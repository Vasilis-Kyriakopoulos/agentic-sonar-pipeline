import os
import logging
import subprocess
from typing import List, Dict
import json

class Coordinator:
    def __init__(self, sonar_client, fixer, tester, reviewer, evaluator, max_retries: int = 2):
        self.sonar_client = sonar_client
        self.fixer = fixer
        self.tester = tester
        self.reviewer = reviewer
        self.evaluator = evaluator
        self.max_retries = max_retries

    def process_issue(self, issue: dict, repo_path: str) -> dict:
        """
        Orchestrates the fix pipeline for a single issue.
        """
        component_key = issue["component"]
        file_path = component_key.split(":")[-1]
        full_path = os.path.join(repo_path, file_path)
        reflection_messages = []
        for attempt in range(self.max_retries + 1):
            logging.info(f"\n--- [Attempt {attempt + 1}/{self.max_retries + 1}] for Issue {issue['rule']} ---")
            
            # Fetch fresh source code from SonarQube for context
            source_code = self.sonar_client.fetch_source_code(component_key)

            # 1. Fix the code
            fix_reply = self.fixer.fix_code_file(issue, source_code,reflection_messages)
            if fix_reply.startswith("Fix failed within max tries"):
                logging.info("❌ Fix failed during generation.")
                if attempt == self.max_retries:
                    return {"status": "FAIL", "reason": "Max retries reached during fix generation"}
                continue
            
            # Read the newly fixed code from disk
            with open(full_path, "r", encoding="utf-8") as f:
                fixed_code = f.read()

            # 2. Test the code
            test_result = self.tester.test(issue, source_code, fixed_code)
            if test_result.get("test_passed"):
                logging.info("✅ Test passed!")
            else:
                logging.info("❌ Test failed: " + str(test_result.get("test_output", "")))
            
            # 3. Review the code
            review_result = self.reviewer.review(issue, source_code, fixed_code)
            
            # 4. Evaluate the overall fix
            evaluation_result = self.evaluator.evaluate(issue, source_code, fixed_code, test_result, review_result)
            logging.info(f"Evaluator Result: {evaluation_result}")
            
            verdict = evaluation_result.get("verdict")
            if verdict == "PASS":
                logging.info("✅ Fix passed evaluator! Committing change...")
                self.fixer.commit_fix(f"Fix SonarQube issue {issue['rule']}: {issue['message']}")
                
                # Mark in SonarQube
                overall_score = evaluation_result.get("overall_score", 0)
                reasoning = evaluation_result.get("reasoning", "")
                self.sonar_client.mark_issue_fixed(issue["key"], reasoning, overall_score)
                return {"status": "SUCCESS", "evaluation": evaluation_result,"attempt":attempt+1}
                
            elif verdict == "RETRY":
                logging.info("⚠️ Evaluator requested a retry. Suggestions: " + str(evaluation_result.get("reasoning", "")))
                # Restore the file to its original state before trying again
                subprocess.run(["git", "restore", full_path], cwd=repo_path, check=True)
                reflection_messages.append(evaluation_result.get("reasoning", ""))
                continue
            else: # FAIL
                logging.info("❌ Evaluator marked fix as FAIL. Aborting this issue.")
                subprocess.run(["git", "restore", full_path], cwd=repo_path, check=True)
                return {"status": "FAIL", "reason": "Evaluator verdict was FAIL"}

        logging.info("❌ Max retries reached. Issue remains unfixed.")
        # Restore file just in case
        subprocess.run(["git", "restore", full_path], cwd=repo_path, check=True)
        return {"status": "FAIL", "reason": "Max retries reached"}

    def process_all(self, issues: List[dict], repo_path: str) -> List[dict]:
        results = []
        for i, issue in enumerate(issues):
            logging.info(f"\n======================================")
            logging.info(f"🛠️ Processing Issue {i+1}/{len(issues)}: {issue['rule']} at {issue['component']}:{issue.get('line')}")
            logging.info(f"======================================")
            res = self.process_issue(issue, repo_path)
            results.append({"issue": issue, "result": res})
        
        # Write report
        with open("report.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)
        return results
