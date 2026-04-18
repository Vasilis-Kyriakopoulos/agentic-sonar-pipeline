import os
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# --- SonarQube Config ---
SONARQUBE_URL = os.getenv("SONARQUBE_URL", "http://localhost:9000")
SONARQUBE_TOKEN = os.getenv("SONARQUBE_TOKEN")
PROJECT_KEY = "patient-repo"


def fetch_sonarqube_issues(project_key: str) -> list[dict]:
    """Fetch all issues from SonarQube for a given project."""
    url = f"{SONARQUBE_URL}/api/issues/search"
    params = {
        "componentKeys": project_key,
        "ps": 500,  # page size (max 500)
        "statuses": "OPEN,CONFIRMED,REOPENED",
    }
    headers = {"Authorization": f"Bearer {SONARQUBE_TOKEN}"}

    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    print(f"Found {data['total']} issues for project '{project_key}'")
    print(type(data["issues"]),type(data["issues"][0]))
    print(data["issues"][0])
    return data["issues"]


def fetch_source_code(component_key: str) -> str:
    """Fetch the source code of a file from SonarQube."""
    url = f"{SONARQUBE_URL}/api/sources/raw"
    params = {"key": component_key}
    print(params)
    headers = {"Authorization": f"Bearer {SONARQUBE_TOKEN}"}

    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        lines = response.text.splitlines()
        return "".join(lines)
    return ""


def format_issues_for_llm(issues: list[dict], source_codes: dict[str, str]) -> str:
    """Format SonarQube issues + source code into an LLM-friendly prompt."""
    prompt_parts = []

    prompt_parts.append("# SonarQube Code Analysis Issues\n")
    prompt_parts.append(f"**Project:** {PROJECT_KEY}")
    prompt_parts.append(f"**Total Issues:** {len(issues)}\n")

    # Group issues by file
    issues_by_file: dict[str, list[dict]] = {}
    for issue in issues:
        component = issue.get("component", "unknown")
        filename = component.split(":")[-1]  # e.g. "patient-repo:main.py" -> "main.py"
        issues_by_file.setdefault(filename, []).append(issue)

    for filename, file_issues in issues_by_file.items():
        prompt_parts.append(f"\n## File: `{filename}`\n")

        # Add the source code
        component_key = file_issues[0]["component"]
        if component_key in source_codes and source_codes[component_key]:
            prompt_parts.append("### Source Code:")
            prompt_parts.append(f"```python\n{source_codes[component_key]}```\n")

        # Add each issue
        prompt_parts.append("### Issues:")
        for i, issue in enumerate(file_issues, 1):
            prompt_parts.append(f"\n**Issue {i}:**")
            prompt_parts.append(f"- **Rule:** {issue.get('rule', 'N/A')}")
            prompt_parts.append(f"- **Severity:** {issue.get('severity', 'N/A')}")
            prompt_parts.append(f"- **Type:** {issue.get('type', 'N/A')}")
            prompt_parts.append(f"- **Line:** {issue.get('line', 'N/A')}")
            prompt_parts.append(f"- **Message:** {issue.get('message', 'N/A')}")
            prompt_parts.append(f"- **Effort:** {issue.get('effort', 'N/A')}")
            tags = ", ".join(issue.get("tags", []))
            if tags:
                prompt_parts.append(f"- **Tags:** {tags}")

    return "\n".join(prompt_parts)


def ask_llm_to_fix(prompt: str) -> str:
    """Send the issues to an LLM and get fix suggestions."""
    client = OpenAI()  # uses OPENAI_API_KEY from env

    system_message = (
        "You are an expert Python developer and code quality specialist. "
        "You will receive SonarQube analysis issues along with the source code. "
        "For each issue:\n"
        "1. Explain what the issue is and why it matters\n"
        "2. Provide the corrected code\n"
        "3. Explain your fix\n\n"
        "Provide the complete fixed file at the end."
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content


def main():
    # 1. Fetch issues from SonarQube
    print("📡 Fetching issues from SonarQube...")
    issues = fetch_sonarqube_issues(PROJECT_KEY)

    if not issues:
        print("🎉 No issues found! Your code is clean.")
        return

    # 2. Fetch source code for affected files
    print("📄 Fetching source code...")
    components = set(issue["component"] for issue in issues)
    source_codes = {}
    for component in components:
        source_codes[component] = fetch_source_code(component)
        filename = component.split(":")[-1]
        print(f"   - Fetched: {filename}")

    # 3. Format everything for the LLM
    print("📝 Formatting issues for LLM...")
    prompt = format_issues_for_llm(issues, source_codes)
    exit(1)
    # Save the prompt for reference
    with open("sonar_issues_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)
    print("   - Saved prompt to sonar_issues_prompt.txt")

    # 4. Send to LLM
    print("🤖 Sending to LLM for analysis...")
    llm_response = ask_llm_to_fix(prompt)

    # 5. Save the response
    with open("llm_fix_suggestions.md", "w", encoding="utf-8") as f:
        f.write(llm_response)
    print("✅ Fix suggestions saved to llm_fix_suggestions.md")

    # 6. Print summary
    print("\n" + "=" * 60)
    print("LLM RESPONSE:")
    print("=" * 60)
    print(llm_response)


if __name__ == "__main__":
    main()
