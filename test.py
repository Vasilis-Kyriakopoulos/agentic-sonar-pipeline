import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from sonarcube_client import SonarCubeClient
from agents.fixer import FixerAgent
from agents.reviewer import ReviewerAgent
from agents.tester import TesterAgent
from agents.evaluator import EvaluatorAgent
from agents.coordinator import Coordinator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
root = logging.getLogger()
root.setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

load_dotenv(override=True)

# --- Configuration ---
#MODEL_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
#MODEL_BASE_URL = "http://127.0.0.1:1234/v1"
#MODEL_BASE_URL = None
#MODEL_BASE_URL = 'https://integrate.api.nvidia.com/v1'
#MODEL = "gemini-3-flash-preview" 
#MODEL = "gemma4" 
MODEL = "gpt-5-nano"
MODEL_BASE_URL="https://api.openai.com/v1"
#MODEL = "deepseek-ai/deepseek-v4-flash"
#MODEL ="gemini-2.5-pro"
#MODEL_BASE_URL = 'https://integrate.api.nvidia.com/v1'
#MODEL = "gemini-3-flash-preview" 


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SONAR_TOKEN = os.getenv("SONARQUBE_TOKEN")
SONAR_URL = os.getenv("SONARQUBE_URL")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

PROJECT_KEY = "vulnerable-python-repo"
REPO_PATH = os.path.join(os.getcwd(), PROJECT_KEY)

def main():
    # 1. Initialize Clients and Agents
    sonar_client = SonarCubeClient(url=SONAR_URL, token=SONAR_TOKEN)
    
    fixer = FixerAgent(
        model_name=MODEL,
        url=MODEL_BASE_URL,
        token=OPENAI_API_KEY,
        repo_path=REPO_PATH
    )

    reviewer = ReviewerAgent(
        model_name=MODEL,
        url=MODEL_BASE_URL,
        token=OPENAI_API_KEY
    )

    tester = TesterAgent(
        model_name=MODEL,
        url=MODEL_BASE_URL,
        token=OPENAI_API_KEY,
        repo_path=REPO_PATH
    )

    evaluator = EvaluatorAgent(
        model_name=MODEL,
        url=MODEL_BASE_URL,
        token=OPENAI_API_KEY,
        repo_path=REPO_PATH
    )

    # 2. Fetch Issues
    logging.info(f"📡 Fetching issues for {PROJECT_KEY}...")
    issues = sonar_client.get_issues(PROJECT_KEY)
    if not issues:
        logging.info("🎉 No issues found!")
        return

    # 3. Setup a single branch for this session
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_branch = f"fix/sonar-session-{timestamp}"
    if not fixer.setup_fix_branch(session_branch):
        logging.info("❌ Failed to setup git branch. Exiting.")
        return

    # 4. Process Issues using Coordinator

    coordinator = Coordinator(sonar_client, fixer, tester, reviewer, evaluator)
    results = coordinator.process_all(issues, REPO_PATH)

    logging.info(f"\n🚀 All issues processed on branch: {session_branch}")

if __name__ == "__main__":
    main()
