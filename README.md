# Agentic SonarQube Fix Pipeline

A multi-agent system that fetches SonarQube issues and automatically fixes them through a coordinated workflow of specialized LLM agents.

## Architecture

```
                         ┌──────────────┐
                         │  SonarQube   │
                         │    API       │
                         └──────┬───────┘
                                │ issues + source code
                         ┌──────▼───────┐
                         │  User Issue  │
                         │  Selection   │
                         └──────┬───────┘
                                │
                    ┌───────────▼───────────┐
                    │     Coordinator       │
                    │  (retry loop, max 2x) │
                    └───────────┬───────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                  ▼
     ┌────────────┐   ┌────────────────┐   ┌──────────────┐
     │   Fixer    │   │    Tester      │   │   Reviewer   │
     │  Agent     │──▶│    Agent       │   │   Agent      │
     │ (tool call)│   │ (pytest exec)  │   │(Pydantic out)│
     └────────────┘   └────────┬───────┘   └──────┬───────┘
                               │                   │
                        ┌──────▼───────────────────▼──┐
                        │       Evaluator Agent        │
                        │  PASS → commit + resolve     │
                        │  RETRY → restore + feedback  │
                        │  FAIL → abort                │
                        └──────────────────────────────┘
```

## Agents

| Agent | Role | Output |
|-------|------|--------|
| **Fixer** | Applies surgical code fixes via tool calling (`apply_surgical_fix`) | Patched file in-place |
| **Tester** | Checks testability, generates pytest tests, executes them | Pass/fail with stdout |
| **Reviewer** | Evaluates code quality (readability, maintainability, PEP8) | Structured `ReviewResult` |
| **Evaluator** | Scores the fix (correctness, safety, readability) and decides PASS/RETRY/FAIL | Structured `EvalResult` |
| **Coordinator** | Orchestrates the pipeline with retry logic and reflection | `report.json` + DB records |

## Prerequisites

- **Python 3.12+**
- **SonarQube** instance (Community Edition or higher) running and accessible
- **Git** installed
- An **OpenAI-compatible LLM API** (OpenAI, Ollama, OpenRouter, LM Studio, etc.)

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd agentic-sonar-pipeline
```

### 2. Configure environment variables

Copy or edit the `.env` file:

```env
# LLM Configuration — works with any OpenAI-compatible API
LLM_MODEL=gpt-4o                            # or "llama3", "mistral", etc.
LLM_BASE_URL=https://api.openai.com/v1      # or http://localhost:11434/v1 for Ollama
LLM_API_KEY=sk-...                           # or "ollama" for local models

# SonarQube
SONARQUBE_URL=http://localhost:9000
SONARQUBE_TOKEN=squ_...
```

**Provider examples:**

| Provider | `LLM_BASE_URL` | `LLM_API_KEY` | `LLM_MODEL` |
|----------|----------------|---------------|-------------|
| OpenAI | `https://api.openai.com/v1` | `sk-...` | `gpt-4o` |
| Ollama | `http://localhost:11434/v1` | `ollama` | `llama3` |
| OpenRouter | `https://openrouter.ai/api/v1` | `sk-or-...` | `openai/gpt-4o` |

### 3. Install dependencies

```bash
pip install -r requirements.docker.txt
```

Or with the full dev environment (includes torch, transformers, etc.):

```bash
pip install -e .
```

## Usage

### Web UI (Streamlit)

The easiest way to use the pipeline. Start the FastAPI backend and Streamlit UI:

```bash
# Terminal 1 — API backend
uvicorn api:app --host 0.0.0.0 --port 8000

# Terminal 2 — Streamlit UI
streamlit run ui.py
```

Open `http://localhost:8501` in your browser. The dashboard has 4 pages:

| Page | What it does |
|------|-------------|
| **🏠 Dashboard** | Overview with metrics, cost breakdown, recent runs |
| **🚀 Run Pipeline** | Configure repo → preview issues → launch pipeline → live progress |
| **📋 Issues** | Browse and inspect SonarQube issues for any project |
| **📊 Analytics** | Token usage, costs, success rates, cost by agent |

### CLI Mode

```bash
python main.py
```

The interactive CLI will:
1. Ask for a Git repo URL or local path
2. Ask for the SonarQube project key
3. Fetch and display all open issues
4. Let you select which issues to fix (or "all")
5. Run the multi-agent pipeline
6. Print a summary with scores and commit fixes to a new branch

### Docker Mode (Full Stack)

Launch the entire stack (FastAPI + Streamlit UI + SonarQube) with one command:

```bash
docker-compose up --build
```

This starts:
- **Streamlit UI** on `http://localhost:8501`
- **FastAPI API** on `http://localhost:8000`
- **SonarQube** on `http://localhost:9000`

### REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/issues/{project_key}` | Fetch all open issues from SonarQube |
| `POST` | `/pipeline/run` | Trigger an async pipeline run |
| `GET` | `/pipeline/status/{session_id}` | Check pipeline progress |
| `GET` | `/runs` | List recent pipeline runs from DB |
| `GET` | `/analytics` | Token usage, costs, success rates |

**Example — trigger a pipeline:**

```bash
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/user/repo.git",
    "project_key": "my-project",
    "issue_keys": ["all"]
  }'
```

## Database

The pipeline uses SQLite (`pipeline.db`) with three tables:

- **`issues`** — SonarQube issues with lifecycle tracking (`OPEN → FIXED | FAILED`)
- **`pipeline_runs`** — One record per pipeline execution per issue
- **`token_usage`** — LLM API call telemetry (tokens consumed + estimated USD cost)

## Project Structure

```
agentic-sonar-pipeline/
├── ui.py                   # Streamlit web dashboard
├── main.py                 # CLI entry point
├── api.py                  # FastAPI REST API
├── sonarcube_client.py     # SonarQube API client (with pagination)
├── models.py               # Pydantic/dataclass models
├── database.py             # SQLAlchemy ORM + analytics
├── agents/
│   ├── agent.py            # Base agent with tracked LLM calls
│   ├── coordinator.py      # Pipeline orchestration + retry logic
│   ├── fixer.py            # Surgical code fix via tool calling
│   ├── tester.py           # Test generation + pytest execution
│   ├── reviewer.py         # Code review (structured output)
│   └── evaluator.py        # Final scoring + PASS/RETRY/FAIL verdict
├── Dockerfile              # Container for FastAPI + Streamlit
├── docker-compose.yml      # Full stack (app + SonarQube)
├── start.sh                # Startup script (runs both services)
├── requirements.docker.txt # Lean dependencies for Docker
├── pyproject.toml          # Full dev dependencies
└── .env                    # Environment configuration
```