import os
import sys
import logging
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from sonarcube_client import SonarCubeClient
from agents.coordinator import Coordinator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
root = logging.getLogger()
root.setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

load_dotenv(override=True)

MODEL = os.getenv("LLM_MODEL")
MODEL_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")

SONAR_TOKEN = os.getenv("SONARQUBE_TOKEN")
SONAR_URL = os.getenv("SONARQUBE_URL")


def clone_repo(repo_url: str, target_dir: str) -> bool:
    """Clones a git repository. Returns True on success."""
    if os.path.exists(target_dir):
        logging.info(f"Directory '{target_dir}' already exists. Using existing repo.")
        return True

    logging.info(f"Cloning {repo_url}...")
    try:
        subprocess.run(
            ["git", "clone", repo_url, target_dir],
            check=True, capture_output=True, text=True
        )
        logging.info(f"Cloned to {target_dir}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Clone failed: {e.stderr}")
        return False


def get_repo_path() -> str:
    """Prompts the user for a repo URL or local path and returns a local directory path."""
    print("\n" + "=" * 50)
    print("Agentic SonarQube Fix Pipeline")
    print("=" * 50)

    repo_input = input("Enter a Git repo URL or local path: ").strip()

    if not repo_input:
        print("No input provided. Exiting.")
        sys.exit(1)

    # If it looks like a URL, clone it
    if repo_input.startswith("http") or repo_input.startswith("git@"):
        # Extract repo name from URL for the local directory
        repo_name = repo_input.rstrip("/").split("/")[-1].replace(".git", "")
        target_dir = os.path.join(os.getcwd(), repo_name)

        if not clone_repo(repo_input, target_dir):
            sys.exit(1)
        return target_dir

    # Otherwise treat as a local path
    repo_path = os.path.abspath(repo_input)
    if not os.path.isdir(repo_path):
        print(f"Directory not found: {repo_path}")
        sys.exit(1)
    return repo_path


def get_project_key(repo_path: str) -> str:
    """Prompts the user for a SonarQube project key, defaulting to the repo folder name."""
    default_key = os.path.basename(repo_path)
    project_key = input(f"\n🔑 Enter SonarQube project key [{default_key}]: ").strip()
    return project_key or default_key


def display_issues(issues: list) -> None:
    """Prints a formatted table of fetched issues."""
    print(f"\n{'#':<4} {'Rule':<20} {'Severity':<10} {'File':<35} {'Line':<6} Message")
    print("-" * 110)
    for i, issue in enumerate(issues):
        file_path = issue.get("component", "").split(":")[-1]
        print(
            f"{i+1:<4} "
            f"{issue.get('rule', ''):<20} "
            f"{issue.get('severity', ''):<10} "
            f"{file_path:<35} "
            f"{issue.get('line', ''):<6} "
            f"{issue.get('message', '')[:50]}"
        )


def select_issues(issues: list) -> list:
    """Lets the user pick which issues to fix."""
    display_issues(issues)
    print(f"Found {len(issues)} issue(s).")
    selection = input("Which issues to fix? (enter numbers like '1,3,5' or 'all') [all]: ").strip().lower()

    if not selection or selection == "all":
        return issues

    try:
        indices = [int(x.strip()) - 1 for x in selection.split(",")]
        selected = [issues[i] for i in indices if 0 <= i < len(issues)]
        if not selected:
            print("No valid issues selected.")
            sys.exit(1)
        print(f"\nSelected {len(selected)} issue(s).")
        return selected
    except (ValueError, IndexError):
        print("Invalid input. Please enter numbers separated by commas.")
        sys.exit(1)


def main():
    # 1. Get the repository
    repo_path = get_repo_path()

    # 2. Get the SonarQube project key
    project_key = get_project_key(repo_path)

    # 3. Initialize clients
    sonar_client = SonarCubeClient(url=SONAR_URL, token=SONAR_TOKEN)

    # 4. Fetch issues
    logging.info(f"\n📡 Fetching issues for '{project_key}'...")
    issues = sonar_client.get_issues(project_key)
    if not issues:
        logging.info("No issues found! Your code is clean.")
        return

    # 5. User selects which issues to fix
    selected_issues = select_issues(issues)

    # 6. Initialize Coordinator (creates all agents internally)
    coordinator = Coordinator(
        sonar_client=sonar_client,
        model_name=MODEL,
        url=MODEL_BASE_URL,
        token=LLM_API_KEY,
        repo_path=repo_path
    )

    # 7. Setup a single branch for this session
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_branch = f"fix/sonar-session-{timestamp}"
    if not coordinator.fixer.setup_fix_branch(session_branch):
        logging.info("❌ Failed to setup git branch. Exiting.")
        return

    # 8. Process selected issues
    results = coordinator.process_all(selected_issues)

    # 9. Print summary
    print_summary(results, session_branch)


def print_summary(results: list, branch: str) -> None:
    """Prints a formatted summary of the pipeline run."""
    print("\n" + "=" * 60)
    print("Pipeline Results Summary")
    print("=" * 60)

    success = sum(1 for r in results if r["result"]["status"] == "SUCCESS")
    failed = len(results) - success

    for r in results:
        issue = r["issue"]
        result = r["result"]
        status_icon = "✅" if result["status"] == "SUCCESS" else "❌"
        score = result.get("evaluation", {}).get("overall_score", "-")
        attempts = result.get("attempt", "-")
        file_path = issue.get("component", "").split(":")[-1]
        print(f"  {status_icon} {issue['rule']:<20} {file_path:<30} Score: {score}  Attempts: {attempts}")

    print(f"\n  Fixed: {success}, Failed: {failed}, Total: {len(results)}")
    print(f"Branch: {branch}")
    print("=" * 60)


if __name__ == "__main__":
    main()
