import json
import requests
import logging

class SonarCubeClient():
    def __init__(self, url: str, token: str) -> None:
        self.url = url
        self.token = token

    def get_issues(self, project_key: str) -> list[dict]:
        """Fetch all issues from SonarQube for a given project."""
        url = f"{self.url}/api/issues/search"
        params = {
            "componentKeys": project_key,
            "ps": 500,  # page size (max 500)
            "statuses": "OPEN,CONFIRMED,REOPENED",
        }
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Found {data['total']} issues for project '{project_key}'")
        return data["issues"]
    
    def fetch_source_code(self, component_key: str) -> str:
        """Fetch the source code of a file from SonarQube."""
        url = f"{self.url}/api/sources/raw"
        params = {"key": component_key}
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            lines = response.content.decode("utf-8").splitlines()
            return "\n".join(lines)
        return ""

    def mark_issue_fixed(self, issue_key: str, comment: str, overall_score: float) -> None:
        """Mark an issue as fixed in SonarQube by adding a comment and transitioning."""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # 1. Add a comment with the Evaluator's reasoning and score
        comment_url = f"{self.url}/api/issues/add_comment"
        text = f"Agentic Fix applied (Score: {overall_score}/10).\n\nEvaluator Reasoning:\n{comment}"
        comment_data = {
            "issue": issue_key,
            "text": text
        }
        try:
            # We use 'data' instead of 'params' for POST bodies in requests
            res = requests.post(comment_url, data=comment_data, headers=headers)
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
            res = requests.post(transition_url, data=transition_data, headers=headers)
            res.raise_for_status()
            logging.info(f"Marked issue '{issue_key}' as resolved")
        except requests.exceptions.RequestException as e:
            logging.warning(f"Could not transition issue '{issue_key}' to 'resolve' (it may require a different state or permissions). Added comment instead.")

    