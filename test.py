from agents.fixer import FixerAgent
from dotenv import load_dotenv
from sonarcube_client import SonarCubeClient
import os
import logging
root = logging.getLogger()
root.setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
load_dotenv(override=True)
# Gemini API Configuration

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# 2. Use the exact model string without the 'models/' prefix 
# (The OpenAI SDK adds the prefix or handles it internally)
GEMINI_MODEL = "gemini-3-flash-preview"

agent = FixerAgent(
    model_name=GEMINI_MODEL,
    url=GEMINI_BASE_URL, 
    token=os.getenv("GEMINI_API_KEY")
)

sonar_client = SonarCubeClient(url=os.getenv("SONARQUBE_URL"), token=os.getenv("SONARQUBE_TOKEN"))
issues = sonar_client.get_issues(project_key="patient-repo")
components = set(issue["component"] for issue in issues)

for issue in issues:
    component_key = issue["component"]
    source_code = sonar_client.fetch_source_code(component_key)
    agent.fix_code_file(issue,source_code)