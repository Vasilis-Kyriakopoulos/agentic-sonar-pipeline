import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from sonarcube_client import SonarCubeClient
from agents.fixer import FixerAgent
from agents.reviewer import ReviewerAgent
from agents.tester import TesterAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
root = logging.getLogger()
root.setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

load_dotenv(override=True)

# --- Configuration ---
MODEL_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MODEL_BASE_URL = "http://127.0.0.1:1234/v1"
MODEL = "gemini-3-flash-preview" 
MODEL = "gemma4" 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SONAR_TOKEN = os.getenv("SONARQUBE_TOKEN")
SONAR_URL = os.getenv("SONARQUBE_URL")

PROJECT_KEY = "vulnerable-python-repo"
REPO_PATH = os.path.join(os.getcwd(), PROJECT_KEY)

def main():
    # 1. Initialize Clients and Agents
    sonar_client = SonarCubeClient(url=SONAR_URL, token=SONAR_TOKEN)
    
    fixer = FixerAgent(
        model_name=MODEL,
        url=MODEL_BASE_URL,
        token=GEMINI_API_KEY,
        repo_path=REPO_PATH
    )

    reviewer = ReviewerAgent(
        model_name=MODEL,
        url=MODEL_BASE_URL,
        token=GEMINI_API_KEY
    )

    tester = TesterAgent(
        model_name=MODEL,
        url=MODEL_BASE_URL,
        token=GEMINI_API_KEY,
        repo_path=REPO_PATH
    )

    # 2. Fetch Issues
    print(f"📡 Fetching issues for {PROJECT_KEY}...")
    issues = sonar_client.get_issues(PROJECT_KEY)
    if not issues:
        print("🎉 No issues found!")
        return

    # 3. Setup a single branch for this session
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_branch = f"fix/sonar-session-{timestamp}"
    if not fixer.setup_fix_branch(session_branch):
        print("❌ Failed to setup git branch. Exiting.")
        return

    # 4. Process Issues
    for i, issue in enumerate(issues[:10]): # Processing first 10 for safety
        component_key = issue["component"]
        source_code = sonar_client.fetch_source_code(component_key)
        
        print(f"\n--- [Issue {i+1}/{len(issues)}] ---")
        print(f"🛠️ Rule: {issue['rule']} at {component_key}:{issue.get('line')}")
        
        # A. Fix the code
        fix_reply = fixer.fix_code_file(issue, source_code)
        if fix_reply.startswith("Fix failed within max tries"):
            print("❌ Fix failed:", fix_reply)
            continue
        
        # B. Get the updated code for review
        file_path = component_key.split(":")[-1]
        full_path = os.path.join(REPO_PATH, file_path)
        
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                fixed_code = f.read()
            
            test_result = tester.test(issue, source_code, fixed_code)
            
            if test_result.get("test_passed"):
                print("✅ Test passed!")
            else:
                print("❌ Test failed:", test_result.get("test_output"))
                continue
            
            # C. Review the fix
            review_result = reviewer.review(issue, source_code, fixed_code)
            
            if review_result.get("is_acceptable"):
                print("✅ Review passed! Committing change...")
                fixer.commit_fix(f"Fix SonarQube issue {issue['rule']}: {issue['message']}")
            else:
                print("⚠️ Review failed. Suggestions:", review_result.get("suggestions"))
                # In a more advanced version, we could loop back to fixer here
                
        except Exception as e:
            print(f"❌ Error during review/commit: {e}")

    print(f"\n🚀 All issues processed on branch: {session_branch}")

if __name__ == "__main__":
    main()
