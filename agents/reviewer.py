import os
from agents.agent import Agent
from models import ReviewResult

class ReviewerAgent(Agent):
    name = "Reviewer Agent"
    color = Agent.GREEN
    
    system_message = (
        "You are an elite Python Code Reviewer. Your job is to evaluate code changes "
        "made by other developers to fix SonarQube issues.\n"
        "CRITICAL RULE: You MUST ONLY evaluate the specific changes made to fix the issue. "
        "DO NOT evaluate or penalize the rest of the file for pre-existing issues.\n"
        "If the fix itself is correct and acceptable, you must set 'is_acceptable' to True, "
        "even if the surrounding original code has other flaws.\n\n"
        "SCORING RULES:\n"
        "- readability_score (1-10): How easy is the changed code to read?\n"
        "- maintainability_score (1-10): PEP8 compliance and Pythonic patterns of the changed code.\n"
        "- suggestions: A list of specific improvement suggestions. Empty list if the code is perfect.\n"
        "- is_acceptable: True if the fix meets professional standards, False otherwise.\n"
    )

    def __init__(self, model_name: str, url: str = None, token: str = None) -> None:
        super().__init__(model_name, url, token)

    def review(self, issue: dict, source_code: str, fixed_code: str) -> dict:
        """
        Reviews the proposed fix using Pydantic structured output.
        """
        self.log("Starting code review...")
        
        user_message = f"""
        ORIGINAL SONARQUBE ISSUE:
        - Rule: {issue.get('rule')}
        - Message: {issue.get('message')}

        ORIGINAL SOURCE CODE (Before Fix):
        ---
        {source_code} 
        ---

        PROPOSED FIXED CODE (After Fix):
        ---
        {fixed_code}
        ---

        INSTRUCTIONS:
        Compare the original code to the proposed fixed code. 
        1. Did the specific fix successfully resolve the SonarQube issue?
        2. Did the fix accidentally alter or delete unrelated logic?
        3. Evaluate ONLY the new/modified code lines based on readability and maintainability. Ignore pre-existing issues in the file.
        """
        
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": user_message}
        ]

        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=messages,
                response_format=ReviewResult
            )

            result: ReviewResult = response.choices[0].message.parsed

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

            self.log(f"Review: acceptable={result.is_acceptable}, readability={result.readability_score}, maintainability={result.maintainability_score}")
            return result.model_dump()

        except Exception as e:
            self.log(f"Structured output failed: {e}. Returning fallback review.")
            return {
                "readability_score": 5,
                "maintainability_score": 5,
                "suggestions": [f"Review failed: {str(e)}"],
                "is_acceptable": True
            }
