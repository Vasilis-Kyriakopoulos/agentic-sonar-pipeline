import os
import logging
import subprocess
from typing import List
import json

from agents.fixer import FixerAgent
from agents.tester import TesterAgent
from agents.reviewer import ReviewerAgent
from agents.evaluator import EvaluatorAgent

# Coordinator colors (not an Agent, so we define them locally)
_CYAN = '\033[36m'
_BG_BLACK = '\033[40m'
_RESET = '\033[0m'


def _log(message: str) -> None:
    """Coordinator-specific colored log, consistent with agent styling."""
    formatted = f"[Coordinator] {message}"
    logging.info(_BG_BLACK + _CYAN + formatted + _RESET)


class Coordinator:
    def __init__(self, sonar_client, model_name: str, url: str, token: str, repo_path: str, max_retries: int = 2):
        self.sonar_client = sonar_client
        self.repo_path = repo_path
        self.max_retries = max_retries

        # Create agents internally
        self.fixer = FixerAgent(model_name=model_name, url=url, token=token, repo_path=repo_path)
        self.tester = TesterAgent(model_name=model_name, url=url, token=token, repo_path=repo_path)
        self.reviewer = ReviewerAgent(model_name=model_name, url=url, token=token)
        self.evaluator = EvaluatorAgent(model_name=model_name, url=url, token=token, repo_path=repo_path)

    def _restore_file(self, full_path: str) -> None:
        """Restores a file to its last committed state via git."""
        try:
            subprocess.run(["git", "restore", full_path], cwd=self.repo_path, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            _log(f"⚠️ Failed to restore {full_path}: {e}")

    def process_issue(self, issue: dict) -> dict:
        """Orchestrates the fix pipeline for a single issue with retry logic."""
        component_key = issue["component"]
        file_path = component_key.split(":")[-1]
        full_path = os.path.join(self.repo_path, file_path)
        reflection_messages = []

        for attempt in range(self.max_retries + 1):
            _log(f"\n--- [Attempt {attempt + 1}/{self.max_retries + 1}] for Issue {issue.get('rule')} ---")

            source_code = self.sonar_client.fetch_source_code(component_key)

            self.fixer.fix_code_file(issue, source_code, reflection_messages)

            if not self.fixer.fix_applied:
                _log("❌ Fix failed during generation.")
                if attempt == self.max_retries:
                    return {"status": "FAIL", "reason": "Max retries reached during fix generation"}
                continue

            with open(full_path, "r", encoding="utf-8") as f:
                fixed_code = f.read()

            test_result = self.tester.test(issue, source_code, fixed_code)
            if test_result.get("test_passed"):
                _log("✅ Test passed!")
            else:
                _log("❌ Test failed: " + str(test_result.get("test_output", "")))

            review_result = self.reviewer.review(issue, source_code, fixed_code)

            evaluation_result = self.evaluator.evaluate(issue, source_code, fixed_code, test_result, review_result)
            _log(f"Evaluator Verdict: {evaluation_result.get('verdict')} (Score: {evaluation_result.get('overall_score')})")

            verdict = evaluation_result.get("verdict")

            if verdict == "PASS":
                _log("✅ Fix passed evaluator! Committing change...")
                self.fixer.commit_fix(f"Fix SonarQube issue {issue.get('rule')}: {issue.get('message')}")

                self.sonar_client.mark_issue_fixed(
                    issue["key"],
                    evaluation_result.get("reasoning", ""),
                    evaluation_result.get("overall_score", 0)
                )
                return {"status": "SUCCESS", "evaluation": evaluation_result, "attempt": attempt + 1}

            elif verdict == "RETRY":
                _log("⚠️ Evaluator requested retry: " + str(evaluation_result.get("reasoning", "")))
                self._restore_file(full_path)
                reflection_messages.append(evaluation_result.get("reasoning", ""))
                continue

            else:  
                _log("❌ Evaluator marked fix as FAIL. Aborting this issue.")
                self._restore_file(full_path)
                return {"status": "FAIL", "reason": "Evaluator verdict was FAIL"}

        _log("❌ Max retries reached. Issue remains unfixed.")
        self._restore_file(full_path)
        return {"status": "FAIL", "reason": "Max retries reached"}

    def process_all(self, issues: List[dict]) -> List[dict]:
        """Processes all issues and writes a report to report.json."""
        results = []
        for i, issue in enumerate(issues):
            _log(f"\n======================================")
            _log(f"🛠️ Processing Issue {i+1}/{len(issues)}: {issue.get('rule')} at {issue.get('component')}:{issue.get('line')}")
            _log(f"======================================")

            result = self.process_issue(issue)
            results.append({"issue": issue, "result": result})

        # Write report next to the repo, using a resolved path
        report_path = os.path.join(os.path.dirname(self.repo_path), "report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)
        _log(f"\n📊 Report saved to {os.path.abspath(report_path)}")

        return results
