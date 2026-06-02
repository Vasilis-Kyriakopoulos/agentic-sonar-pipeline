"""
database.py - Persistent storage layer for the Agentic SonarQube Pipeline.

Manages three tables:
  - issues       : SonarQube issues fetched from the server, with status tracking.
  - pipeline_runs: One record per end-to-end pipeline execution for a single issue.
  - token_usage  : LLM API call telemetry (tokens consumed + estimated USD cost).
"""

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text,
    DateTime, ForeignKey, func,
)
from sqlalchemy.orm import DeclarativeBase, relationship, Session, sessionmaker

# ---------------------------------------------------------------------------
# Engine & Session
# ---------------------------------------------------------------------------

DB_PATH = "pipeline.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class IssueRecord(Base):
    """A SonarQube issue, persisted so we can track its status across runs."""
    __tablename__ = "issues"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    key             = Column(String,  unique=True, nullable=False, index=True)
    rule            = Column(String,  nullable=False)
    severity        = Column(String)
    component       = Column(String)
    file_path       = Column(String)
    line            = Column(Integer)
    message         = Column(Text)
    type            = Column(String)
    tags            = Column(Text) 
    project_key     = Column(String)

    # Lifecycle: OPEN → FIXED | FAILED
    status          = Column(String, default="OPEN")

    first_seen_at   = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, default=datetime.utcnow)

    runs = relationship("PipelineRun", back_populates="issue",
                        cascade="all, delete-orphan")


class PipelineRun(Base):
    """One end-to-end pipeline execution for a single issue."""
    __tablename__ = "pipeline_runs"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    issue_key      = Column(String, ForeignKey("issues.key"), nullable=False, index=True)
    session_branch = Column(String)

    # SUCCESS | FAIL | IN_PROGRESS
    verdict        = Column(String, default="IN_PROGRESS")
    attempts       = Column(Integer, default=0)

    # Post-fix verification: None = not verified, True = confirmed fixed, False = still open
    verified       = Column(Integer, nullable=True, default=None)

    started_at     = Column(DateTime, default=datetime.utcnow)
    completed_at   = Column(DateTime)

    issue        = relationship("IssueRecord", back_populates="runs")
    token_usages = relationship("TokenUsage", back_populates="run",
                                cascade="all, delete-orphan")


class TokenUsage(Base):
    """LLM API call telemetry — one row per agent LLM call."""
    __tablename__ = "token_usage"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    run_id              = Column(Integer, ForeignKey("pipeline_runs.id"),
                                 nullable=True, index=True)
    agent_name          = Column(String, nullable=False)
    model_name          = Column(String, nullable=False)
    prompt_tokens       = Column(Integer, default=0)
    completion_tokens   = Column(Integer, default=0)
    total_tokens        = Column(Integer, default=0)
    estimated_cost_usd  = Column(Float,   default=0.0)
    called_at           = Column(DateTime, default=datetime.utcnow)

    run = relationship("PipelineRun", back_populates="token_usages")


# ---------------------------------------------------------------------------
# Pricing table  (USD per 1 000 tokens)
# Extend this dict to support more models.
# ---------------------------------------------------------------------------

# Keys are matched as substrings of the model name (case-insensitive).
_PRICING: list[tuple[str, float, float]] = [
    # (substring,             input $/1k,  output $/1k)
    ("gpt-5-nano",             0.000150,    0.000600),
    ("gpt-4o-mini",           0.000150,    0.000600),
    ("gpt-4o",                0.002500,    0.010000),
    ("gpt-4-turbo",           0.010000,    0.030000),
    ("gpt-4",                 0.030000,    0.060000),
    ("gpt-3.5",               0.000500,    0.001500),
    ("claude-3-5-sonnet",     0.003000,    0.015000),
    ("claude-3-haiku",        0.000250,    0.001250),
    ("claude-3-opus",         0.015000,    0.075000),
    ("llama",                 0.000000,    0.000000),   # local / free
    ("mistral",               0.000000,    0.000000),   # local / free
]


def _estimate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Return estimated USD cost for a single LLM call."""
    model_lower = model_name.lower()
    for substring, input_price, output_price in _PRICING:
        if substring in model_lower:
            cost = (prompt_tokens / 1000) * input_price \
                 + (completion_tokens / 1000) * output_price
            return round(cost, 8)
    # Unknown model → treat as free but warn
    logging.warning(f"[DB] Unknown model '{model_name}' — cost recorded as $0.00")
    return 0.0


# ---------------------------------------------------------------------------
# DB initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all tables if they do not yet exist."""
    Base.metadata.create_all(engine)
    logging.info("[DB] Database ready → %s", DB_PATH)


def get_session() -> Session:
    """Return a new SQLAlchemy session."""
    return SessionLocal()


# ---------------------------------------------------------------------------
# Issue helpers
# ---------------------------------------------------------------------------

def upsert_issue(session: Session, issue_dict: dict, project_key: str) -> IssueRecord:
    """
    Insert a new IssueRecord or refresh an existing one from a SonarQube
    API response dict.  Returns the (possibly updated) record.
    """
    key = issue_dict.get("key", "")
    record = session.query(IssueRecord).filter_by(key=key).first()

    if record is None:
        record = IssueRecord(key=key)
        session.add(record)

    component = issue_dict.get("component", "")
    record.rule        = issue_dict.get("rule", "")
    record.severity    = issue_dict.get("severity", "")
    record.component   = component
    record.file_path   = component.split(":")[-1] if ":" in component else component
    record.line        = issue_dict.get("line")
    record.message     = issue_dict.get("message", "")
    record.type        = issue_dict.get("type", "")
    record.tags        = json.dumps(issue_dict.get("tags", []))
    record.project_key = project_key
    record.last_updated_at = datetime.utcnow()

    session.commit()
    return record


def update_issue_status(session: Session, issue_key: str, status: str) -> None:
    """
    Update the lifecycle status of an issue.
    Valid values: "OPEN", "FIXED", "FAILED"
    """
    record = session.query(IssueRecord).filter_by(key=issue_key).first()
    if record:
        record.status = status
        record.last_updated_at = datetime.utcnow()
        session.commit()
        logging.info("[DB] Issue %s → %s", issue_key, status)
    else:
        logging.warning("[DB] update_issue_status: issue '%s' not found.", issue_key)


def get_in_progress_issues(session: Session, issue_keys: list[str]) -> list[str]:
    """
    Given a list of issue keys, returns the subset of keys that are currently
    associated with an active pipeline run (where PipelineRun.verdict == 'IN_PROGRESS').
    If 'all' is present in issue_keys, checks all active runs.
    """
    query = session.query(PipelineRun.issue_key).filter(PipelineRun.verdict == "IN_PROGRESS")
    if "all" not in issue_keys:
        query = query.filter(PipelineRun.issue_key.in_(issue_keys))
    return [r.issue_key for r in query.all()]


# ---------------------------------------------------------------------------

# Pipeline run helpers
# ---------------------------------------------------------------------------

def create_run(session: Session, issue_key: str, session_branch: str) -> PipelineRun:
    """Create and persist a new IN_PROGRESS pipeline run. Returns the new record."""
    run = PipelineRun(
        issue_key=issue_key,
        session_branch=session_branch,
        verdict="IN_PROGRESS",
        started_at=datetime.utcnow(),
    )
    session.add(run)
    session.commit()
    logging.info("[DB] Run #%d started for issue %s", run.id, issue_key)
    return run


def complete_run(session: Session, run_id: int, verdict: str, attempts: int) -> None:
    """Mark a pipeline run as complete with its final verdict and attempt count."""
    run = session.query(PipelineRun).filter_by(id=run_id).first()
    if run:
        run.verdict      = verdict
        run.attempts     = attempts
        run.completed_at = datetime.utcnow()
        session.commit()
        logging.info("[DB] Run #%d completed → %s (%d attempt(s))", run_id, verdict, attempts)
    else:
        logging.warning("[DB] complete_run: run_id %d not found.", run_id)


def mark_run_verified(session: Session, run_id: int, verified: bool) -> None:
    """Update the verification status of a pipeline run after a re-scan."""
    run = session.query(PipelineRun).filter_by(id=run_id).first()
    if run:
        run.verified = 1 if verified else 0
        session.commit()
        status_str = "VERIFIED ✅" if verified else "STILL OPEN "
        logging.info("[DB] Run #%d verification → %s", run_id, status_str)
    else:
        logging.warning("[DB] mark_run_verified: run_id %d not found.", run_id)


def get_latest_successful_runs(session: Session, issue_keys: list[str]) -> list[PipelineRun]:
    """
    For each issue key, return the most recent pipeline run with verdict='SUCCESS'.
    Used by the verification step to update the right runs.
    """
    from sqlalchemy import desc
    runs = []
    for key in issue_keys:
        run = (
            session.query(PipelineRun)
            .filter_by(issue_key=key, verdict="SUCCESS")
            .order_by(desc(PipelineRun.id))
            .first()
        )
        if run:
            runs.append(run)
    return runs


# ---------------------------------------------------------------------------
# Token usage helpers
# ---------------------------------------------------------------------------

def log_token_usage(
    session: Session,
    agent_name: str,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    run_id: Optional[int] = None,
) -> TokenUsage:
    """
    Persist LLM token usage for one API call.
    Automatically calculates the estimated USD cost.
    Returns the saved TokenUsage record.
    """
    total = prompt_tokens + completion_tokens
    cost  = _estimate_cost(model_name, prompt_tokens, completion_tokens)

    record = TokenUsage(
        run_id=run_id,
        agent_name=agent_name,
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total,
        estimated_cost_usd=cost,
        called_at=datetime.utcnow(),
    )
    session.add(record)
    session.commit()

    logging.info(
        "[DB] Token usage — %s | prompt=%d, completion=%d, cost=$%.6f",
        agent_name, prompt_tokens, completion_tokens, cost,
    )
    return record


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def get_analytics(session: Session) -> dict:
    """
    Query the DB and return a summary dict suitable for printing a final report.

    Returns:
        {
            "total_issues":     int,
            "fixed":            int,
            "failed":           int,
            "open":             int,
            "success_rate_pct": float,
            "total_runs":       int,
            "avg_attempts":     float,
            "total_tokens":     int,
            "total_cost_usd":   float,
            "cost_by_agent":    dict[str, float],
        }
    """
    # Issue counts by status
    status_counts: dict[str, int] = {}
    for status, count in session.query(IssueRecord.status, func.count(IssueRecord.id)) \
                                 .group_by(IssueRecord.status).all():
        status_counts[status] = count

    total_issues = sum(status_counts.values())
    fixed  = status_counts.get("FIXED",  0)
    failed = status_counts.get("FAILED", 0)
    open_  = status_counts.get("OPEN",   0)
    success_rate = round((fixed / total_issues * 100) if total_issues else 0.0, 1)

    # Pipeline run stats
    total_runs   = session.query(func.count(PipelineRun.id)).scalar() or 0
    avg_attempts = session.query(func.avg(PipelineRun.attempts)).scalar() or 0.0
    avg_attempts = round(float(avg_attempts), 2)

    # Token & cost totals
    total_tokens = session.query(func.sum(TokenUsage.total_tokens)).scalar() or 0
    total_cost   = session.query(func.sum(TokenUsage.estimated_cost_usd)).scalar() or 0.0
    total_cost   = round(float(total_cost), 6)

    # Cost broken down by agent
    cost_by_agent: dict[str, float] = {}
    for agent_name, cost in session.query(
        TokenUsage.agent_name,
        func.sum(TokenUsage.estimated_cost_usd)
    ).group_by(TokenUsage.agent_name).all():
        cost_by_agent[agent_name] = round(float(cost), 6)

    # Verification stats
    verified_count = session.query(func.count(PipelineRun.id)).filter(
        PipelineRun.verdict == "SUCCESS", PipelineRun.verified == 1
    ).scalar() or 0
    unverified_count = session.query(func.count(PipelineRun.id)).filter(
        PipelineRun.verdict == "SUCCESS", PipelineRun.verified == 0
    ).scalar() or 0
    pending_verification = session.query(func.count(PipelineRun.id)).filter(
        PipelineRun.verdict == "SUCCESS", PipelineRun.verified.is_(None)
    ).scalar() or 0

    return {
        "total_issues":          total_issues,
        "fixed":                 fixed,
        "failed":                failed,
        "open":                  open_,
        "success_rate_pct":      success_rate,
        "total_runs":            total_runs,
        "avg_attempts":          avg_attempts,
        "total_tokens":          total_tokens,
        "total_cost_usd":        total_cost,
        "cost_by_agent":         cost_by_agent,
        "verified":              verified_count,
        "verification_failed":   unverified_count,
        "pending_verification":  pending_verification,
    }
