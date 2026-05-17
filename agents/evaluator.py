import os
from agents.agent import Agent
from models import EvalResult

class EvaluatorAgent(Agent):
    name = "Evaluator Agent"
    color = Agent.RED
    
    system_message = (
        "You are a Staff Software Engineer acting as the final Evaluator in an automated code repair pipeline. "
        "Your task is to holistically assess a proposed fix for a SonarQube issue, taking into account the code changes, "
        "test results, and review feedback.\n\n"
        "SCORING RULES:\n"
        "1. Score the fix on three dimensions from 1 to 10:\n"
        "   - correctness_score: Does it actually solve the SonarQube issue without breaking tests?\n"
        "   - safety_score: Does the fix introduce any new security vulnerabilities or unintended side effects?\n"
        "   - readability_score: Is the code clean, well-named, and compliant with PEP-8?\n"
        "2. Based on your scores, determine a final verdict:\n"
        "   - 'PASS': The fix is excellent and ready to merge (average score >= 7).\n"
        "   - 'RETRY': The fix is flawed but fixable. Another attempt should be made (average score 4-6).\n"
        "   - 'FAIL': The fix is completely wrong or introduces severe issues (average score < 4).\n"
        "3. Provide clear reasoning explaining your verdict.\n"
    )

    def __init__(self, model_name: str, url: str = None, token: str = None, repo_path: str = None) -> None:
        super().__init__(model_name, url, token)
        self.repo_path = repo_path or os.getcwd()

    def evaluate(self, issue: dict, source_code: str, fixed_code: str, test_result: dict, review_result: dict) -> dict:
        self.log(f"Evaluating fix for issue {issue.get('rule')}")

        user_message = f"""
        ORIGINAL SONARQUBE ISSUE:
        - Rule: {issue.get('rule')}
        - Message: {issue.get('message')}

        ORIGINAL SOURCE CODE:
        ---
        {source_code}
        ---

        PROPOSED FIXED CODE:
        ---
        {fixed_code}
        ---

        TEST RESULTS:
        - Passed: {test_result.get('test_passed')}
        - Output: {test_result.get('test_output')}

        REVIEWER FEEDBACK:
        - Acceptable: {review_result.get('is_acceptable')}
        - Suggestions: {review_result.get('suggestions')}
        - Readability Score: {review_result.get('readability_score')}
        - Maintainability Score: {review_result.get('maintainability_score')}

        Please evaluate this fix according to your scoring rules.
        """

        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": user_message}
        ]

        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=messages,
                response_format=EvalResult
            )

            result: EvalResult = response.choices[0].message.parsed

            # --- Token telemetry ---
            usage = getattr(response, "usage", None)
            if usage and self.db_session is not None:
                from database import log_token_usage
                log_token_usage(
                    session=self.db_session,
                    agent_name=self.name,
                    model_name=self.model_name,
                    prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                    completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                    run_id=self.run_id,
                )

            self.log(f"Verdict: {result.verdict} (Score: {result.overall_score}) - {result.reasoning}")
            return result.model_dump()

        except Exception as e:
            self.log(f"Structured output failed: {e}. Returning RETRY fallback.")
            return {
                "verdict": "RETRY",
                "reasoning": f"Evaluator structured output failed: {str(e)}",
                "correctness_score": 0,
                "safety_score": 0,
                "readability_score": 0,
                "overall_score": 0.0
            }