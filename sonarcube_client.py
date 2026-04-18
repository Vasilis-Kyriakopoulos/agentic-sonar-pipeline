from lib2to3.pgen2 import token
import json
import requests

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
        print(f"Found {data['total']} issues for project '{project_key}'")
        return data["issues"]
    
    def fetch_source_code(self, component_key: str) -> str:
        """Fetch the source code of a file from SonarQube."""
        url = f"{self.url}/api/sources/raw"
        params = {"key": component_key}
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            lines = response.text.splitlines()
            return "".join(lines)
        return ""

    