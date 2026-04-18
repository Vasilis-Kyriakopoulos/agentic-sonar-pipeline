from agents.fixer import FixerAgent
from dotenv import load_dotenv
from sonarcube_client import SonarCubeClient
import os
import logging
root = logging.getLogger()
root.setLevel(logging.INFO)
load_dotenv(override=True)
agent = FixerAgent(model_name="gpt-5-nano",url = None, token=None)

sonar_client = SonarCubeClient(url=os.getenv("SONARQUBE_URL"), token=os.getenv("SONARQUBE_TOKEN"))
issues = sonar_client.get_issues(project_key="patient-repo")
components = set(issue["component"] for issue in issues)

for issue in issues:
    component_key = issue["component"]
    source_code = sonar_client.fetch_source_code(component_key)
    agent.fix_code_file(issue,source_code)