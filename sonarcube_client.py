import json
import requests
import logging

class SonarCubeClient():
    def __init__(self, url: str, token: str) -> None:
        self.url = url
        self.token = token

    def get_issues(self, project_key: str) -> list[dict]:
        """Fetch all issues from SonarQube for a given project (with pagination)."""
        url = f"{self.url}/api/issues/search"
        page_size = 500
        page = 1
        all_issues = []

        while True:
            params = {
                "componentKeys": project_key,
                "ps": page_size,
                "p": page,
                "statuses": "OPEN,CONFIRMED,REOPENED",
            }
            response = requests.get(url, params=params, auth=(self.token, ""))
            response.raise_for_status()
            data = response.json()

            issues = data.get("issues", [])
            all_issues.extend(issues)
            total = data.get("total", 0)

            logging.info(f"Fetched page {page} ({len(all_issues)}/{total} issues) for project '{project_key}'")

            if len(all_issues) >= total or not issues:
                break
            page += 1

        logging.info(f"Found {len(all_issues)} total issues for project '{project_key}'")
        return all_issues
    
    def fetch_source_code(self, component_key: str) -> str:
        """Fetch the source code of a file from SonarQube."""
        url = f"{self.url}/api/sources/raw"
        params = {"key": component_key}
        response = requests.get(url, params=params, auth=(self.token, ""))
        if response.status_code == 200:
            lines = response.content.decode("utf-8").splitlines()
            return "\n".join(lines)
        return ""

    def mark_issue_fixed(self, issue_key: str, comment: str, overall_score: float) -> None:
        """Mark an issue as fixed in SonarQube by adding a comment and transitioning."""
        
        # 1. Add a comment with the Evaluator's reasoning and score
        comment_url = f"{self.url}/api/issues/add_comment"
        text = f"Agentic Fix applied (Score: {overall_score}/10).\n\nEvaluator Reasoning:\n{comment}"
        comment_data = {
            "issue": issue_key,
            "text": text
        }
        try:
            # We use 'data' instead of 'params' for POST bodies in requests
            res = requests.post(comment_url, data=comment_data, auth=(self.token, ""))
            res.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to add comment to issue {issue_key}: {e}")
            
        # 2. Try to transition the issue to 'resolve'
        transition_url = f"{self.url}/api/issues/do_transition"
        transition_data = {
            "issue": issue_key,
            "transition": "resolve"
        }
        try:
            res = requests.post(transition_url, data=transition_data, auth=(self.token, ""))
            res.raise_for_status()
            logging.info(f"Marked issue '{issue_key}' as resolved")
        except requests.exceptions.RequestException as e:
            logging.warning(f"Could not transition issue '{issue_key}' to 'resolve' (it may require a different state or permissions). Added comment instead.")

    def run_scan(self, repo_path: str, project_key: str) -> None:
        """Run sonar-scanner CLI on the given repository path."""
        import subprocess
        
        logging.info(f"Starting SonarQube scan for project '{project_key}' at '{repo_path}'...")
        
        # We point to the sonarqube service inside the docker-compose network (http://sonarqube:9000)
        # or the URL passed to the client (self.url)
        cmd = [
            "sonar-scanner",
            f"-Dsonar.projectKey={project_key}",
            f"-Dsonar.sources=.",
            f"-Dsonar.host.url={self.url}",
            f"-Dsonar.token={self.token}",
            "-Dsonar.scm.disabled=true",
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            logging.info("SonarQube scan completed successfully!")
            logging.debug(result.stdout)
        except subprocess.CalledProcessError as e:
            logging.error(f"SonarQube scan failed: {e.stderr}\nOutput: {e.stdout}")
            raise Exception(f"SonarQube scan failed: {e.stderr}")

    