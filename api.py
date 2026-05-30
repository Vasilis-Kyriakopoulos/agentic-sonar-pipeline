"""
api.py — FastAPI REST API for the Agentic SonarQube Fix Pipeline.

Replaces the interactive CLI with HTTP endpoints.
Pipeline runs execute asynchronously in a background thread pool.
"""

import os
import sys
import logging
import subprocess
import uuid
from datetime import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from sonarcube_client import SonarCubeClient
from agents.coordinator import Coordinator
import database as db

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def configure_clean_logging():
    # Clear root logger handlers and add exactly one StreamHandler
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    
    import sys
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(stdout_handler)
    root.setLevel(logging.INFO)

    # Clear handlers from other loggers and let them propagate to the root logger
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "httpx"]:
        logger = logging.getLogger(logger_name)
        for h in list(logger.handlers):
            logger.removeHandler(h)
        logger.propagate = True

# Apply clean logging immediately
configure_clean_logging()
logging.getLogger("httpx").setLevel(logging.WARNING)

load_dotenv()

MODEL = os.getenv("LLM_MODEL")
MODEL_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
SONAR_TOKEN = os.getenv("SONARQUBE_TOKEN")
SONAR_URL = os.getenv("SONARQUBE_URL")

# Where cloned repos are stored inside the container
REPOS_DIR = os.getenv("REPOS_DIR", os.path.join(os.getcwd(), "repos"))
os.makedirs(REPOS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Agentic SonarQube Fix Pipeline",
    description="REST API for automated SonarQube issue fixing using LLM agents.",
    version="1.0.0",
)

# Thread pool for background pipeline execution
executor = ThreadPoolExecutor(max_workers=2)

# In-memory session store (keyed by session_id)
sessions: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class PipelineRequest(BaseModel):
    """Request body for triggering a pipeline run."""
    repo_url: Optional[str] = Field(None, description="Git URL to clone. Mutually exclusive with repo_path.")
    repo_path: Optional[str] = Field(None, description="Path to an already-cloned repo inside the container.")
    project_key: str = Field(..., description="SonarQube project key.")
    issue_keys: list[str] = Field(
        default=["all"],
        description="List of SonarQube issue keys to fix, or ['all'] for all open issues.",
    )


class PipelineResponse(BaseModel):
    session_id: str
    status: str
    message: str


class ScanRequest(BaseModel):
    """Request body for running a SonarQube scan on a repository."""
    repo_url: Optional[str] = Field(None, description="Git URL to clone.")
    repo_path: Optional[str] = Field(None, description="Path to an already-cloned repo inside the container.")
    project_key: str = Field(..., description="SonarQube project key.")


class ScanResponse(BaseModel):
    status: str
    message: str


class SessionStatus(BaseModel):
    session_id: str
    status: str
    project_key: str
    total_issues: int
    processed: int
    results: list[dict]
    started_at: Optional[str]
    completed_at: Optional[str]


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup():
    # Re-apply clean logging configuration to clear any handlers added by Uvicorn during startup
    configure_clean_logging()

    # Diagnostic logging inspection
    import sys
    for name in ["", "uvicorn", "uvicorn.error", "uvicorn.access"]:
        l = logging.getLogger(name)
        logging.info(f"DEBUG_LOG_LOGGER '{name}': handlers={l.handlers}, propagate={l.propagate}")
    sys.stdout.flush()

    db.init_db()
    logging.info("[API] Database initialized.")
    logging.info(f"[API] Repos directory: {REPOS_DIR}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/issues/{project_key}", tags=["Issues"])
def get_issues(project_key: str):
    """Fetch all open issues from SonarQube for a given project key."""
    try:
        sonar_client = SonarCubeClient(url=SONAR_URL, token=SONAR_TOKEN)
        issues = sonar_client.get_issues(project_key)

        # Persist fetched issues to DB
        session = db.get_session()
        try:
            for issue in issues:
                db.upsert_issue(session, issue, project_key)
        finally:
            session.close()

        return {"project_key": project_key, "total": len(issues), "issues": issues}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scan", response_model=ScanResponse, tags=["Pipeline"])
def scan_project(request: ScanRequest):
    """Clone repository (if needed) and run a SonarQube scan."""
    # --- Resolve repository path ---
    if request.repo_url:
        repo_name = request.repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        repo_path = os.path.join(REPOS_DIR, repo_name)
        if not os.path.isdir(repo_path):
            try:
                subprocess.run(
                    ["git", "clone", request.repo_url, repo_path],
                    check=True, capture_output=True, text=True,
                )
            except subprocess.CalledProcessError as e:
                raise HTTPException(status_code=400, detail=f"Git clone failed: {e.stderr}")
    elif request.repo_path:
        repo_path = request.repo_path
        if not os.path.isdir(repo_path):
            raise HTTPException(status_code=400, detail=f"Directory not found: {repo_path}")
    else:
        raise HTTPException(status_code=400, detail="Provide either repo_url or repo_path.")

    # --- Run SonarQube scan ---
    try:
        sonar_client = SonarCubeClient(url=SONAR_URL, token=SONAR_TOKEN)
        sonar_client.run_scan(repo_path, request.project_key)
        return ScanResponse(
            status="SUCCESS",
            message=f"SonarQube scan completed successfully for '{request.project_key}'!",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SonarQube scan failed: {str(e)}")


@app.post("/pipeline/run", response_model=PipelineResponse, tags=["Pipeline"])
def run_pipeline(request: PipelineRequest):
    """Trigger an asynchronous pipeline run for the given project and issues."""

    # --- Resolve repository path ---
    if request.repo_url:
        repo_name = request.repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        repo_path = os.path.join(REPOS_DIR, repo_name)
        if not os.path.isdir(repo_path):
            try:
                subprocess.run(
                    ["git", "clone", request.repo_url, repo_path],
                    check=True, capture_output=True, text=True,
                )
            except subprocess.CalledProcessError as e:
                raise HTTPException(status_code=400, detail=f"Git clone failed: {e.stderr}")
    elif request.repo_path:
        repo_path = request.repo_path
        if not os.path.isdir(repo_path):
            raise HTTPException(status_code=400, detail=f"Directory not found: {repo_path}")
    else:
        raise HTTPException(status_code=400, detail="Provide either repo_url or repo_path.")

    # --- Create session ---
    session_id = f"session-{uuid.uuid4().hex[:8]}"

    sessions[session_id] = {
        "session_id": session_id,
        "status": "IN_PROGRESS",
        "project_key": request.project_key,
        "repo_path": repo_path,
        "total_issues": 0,
        "processed": 0,
        "results": [],
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
    }

    # --- Launch pipeline in background thread ---
    executor.submit(
        _run_pipeline_background,
        session_id,
        repo_path,
        request.project_key,
        request.issue_keys,
    )

    return PipelineResponse(
        session_id=session_id,
        status="IN_PROGRESS",
        message=f"Pipeline started. Poll /pipeline/status/{session_id} for progress.",
    )


@app.get("/pipeline/status/{session_id}", response_model=SessionStatus, tags=["Pipeline"])
def get_pipeline_status(session_id: str):
    """Check the status of an in-progress or completed pipeline run."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return SessionStatus(**sessions[session_id])


@app.get("/runs", tags=["Database"])
def list_runs(limit: int = 20):
    """List recent pipeline runs from the database."""
    session = db.get_session()
    try:
        runs = session.query(db.PipelineRun).order_by(db.PipelineRun.id.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "issue_key": r.issue_key,
                "session_branch": r.session_branch,
                "verdict": r.verdict,
                "attempts": r.attempts,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ]
    finally:
        session.close()


@app.get("/analytics", tags=["Database"])
def get_analytics():
    """Return pipeline analytics (token usage, costs, success rate)."""
    session = db.get_session()
    try:
        return db.get_analytics(session)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Background pipeline runner
# ---------------------------------------------------------------------------

def _run_pipeline_background(
    session_id: str,
    repo_path: str,
    project_key: str,
    issue_keys: list[str],
):
    """Runs the full pipeline in a background thread. Updates the in-memory session store."""
    db_session = db.get_session()

    try:
        sonar_client = SonarCubeClient(url=SONAR_URL, token=SONAR_TOKEN)

        # Fetch issues
        all_issues = sonar_client.get_issues(project_key)
        for issue in all_issues:
            db.upsert_issue(db_session, issue, project_key)

        # Filter issues
        if issue_keys == ["all"]:
            selected_issues = all_issues
        else:
            selected_issues = [i for i in all_issues if i["key"] in issue_keys]

        if not selected_issues:
            sessions[session_id]["status"] = "COMPLETED"
            sessions[session_id]["completed_at"] = datetime.utcnow().isoformat()
            return

        sessions[session_id]["total_issues"] = len(selected_issues)

        # Tests run directly inside the container — no additional sandboxing needed
        coordinator = Coordinator(
            sonar_client=sonar_client,
            model_name=MODEL,
            url=MODEL_BASE_URL,
            token=LLM_API_KEY,
            repo_path=repo_path,
            db_session=db_session,
        )

        # Setup branch
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        branch = f"fix/sonar-session-{timestamp}"
        coordinator.fixer.setup_fix_branch(branch)

        # Process issues one by one, updating session state
        results = []
        for i, issue in enumerate(selected_issues):
            result = coordinator.process_issue(issue)
            results.append({"issue": issue, "result": result})
            sessions[session_id]["processed"] = i + 1
            sessions[session_id]["results"] = results

        sessions[session_id]["status"] = "COMPLETED"
        sessions[session_id]["completed_at"] = datetime.utcnow().isoformat()

    except Exception as e:
        logging.error(f"[API] Pipeline failed for session {session_id}: {e}")
        sessions[session_id]["status"] = "FAILED"
        sessions[session_id]["completed_at"] = datetime.utcnow().isoformat()
        sessions[session_id]["results"].append({"error": str(e)})

    finally:
        db_session.close()
