import os
from agents.agent import Agent

class EvaluatorAgent(Agent):
    name = "Evaluator Agent"
    color = Agent.RED
    
    system_message = (
        "You are a Staff Software Engineer acting as the final Evaluator in an automated code repair pipeline. "
        "Your task is to holistically assess a proposed fix for a SonarQube issue, taking into account the code changes, "
        "test results, and review feedback.\n\n"
        "OPERATIONAL RULES:\n"
        "1. INPUTS: You will receive the original issue, the proposed fix, the test execution results, and the review feedback.\n"
        "2. SCORING: You must score the fix on three dimensions from 1 to 10:\n"
        "   - Correctness: Does it actually solve the SonarQube issue without breaking tests?\n"
        "   - Safety: Does the fix introduce any new security vulnerabilities or unintended side effects?\n"
        "   - Readability: Is the code clean, well-named, and compliant with PEP-8?\n"
        "3. VERDICT: Based on your scores, determine a final verdict:\n"
        "   - 'PASS': The fix is excellent and ready to merge (overall score >= 7).\n"
        "   - 'RETRY': The fix is flawed but fixable. Another attempt should be made (overall score 4-6).\n"
        "   - 'FAIL': The fix is completely wrong or introduces severe issues, and we should abort (overall score < 4).\n"
        "4. OUTPUT: You MUST use the 'evaluate_fix' tool to provide your scores, reasoning, and final verdict.\n"
    )

    def __init__(self, model_name: str, url: str = None, token: str = None, repo_path: str = None) -> None:
        super().__init__(model_name, url, token)
        self.repo_path = repo_path or os.getcwd()
        self.tool_mapping = {
            "evaluate_fix": self.evaluate_fix
        }

    def get_tools(self):
        return [{"type": "function", "function": self.evaluate_fix_function}]

    def evaluate_fix(self, correctness_score: int, safety_score: int, readability_score: int, verdict: str, reasoning: str) -> str:
        self.evaluation_result = {
            "correctness_score": correctness_score,
            "safety_score": safety_score,
            "readability_score": readability_score,
            "verdict": verdict,
            "reasoning": reasoning,
            "overall_score": (correctness_score + safety_score + readability_score) / 3.0
        }
        return "Evaluation submitted successfully"
    
    evaluate_fix_function = {
        "name": "evaluate_fix",
        "description": "Evaluates a proposed fix for a SonarQube issue.",
        "parameters": {
            "type": "object",
            "properties": {
                "correctness_score": {
                    "type": "integer",
                    "description": "The correctness score of the fix on a scale of 1 to 10."
                },
                "safety_score": {
                    "type": "integer",
                    "description": "The safety score of the fix on a scale of 1 to 10."
                },
                "readability_score": {
                    "type": "integer",
                    "description": "The readability score of the fix on a scale of 1 to 10."
                },
                "verdict": {
                    "type": "string",
                    "description": "The final verdict on the fix: 'PASS', 'RETRY', or 'FAIL'."
                },
                "reasoning": {
                    "type": "string",
                    "description": "A brief explanation of why the fix received the given scores."
                }
            },
            "required": ["correctness_score", "safety_score", "readability_score", "verdict", "reasoning"],
            "additionalProperties": False
        }
    }

    def evaluate(self, issue: dict, source_code: str, fixed_code: str, test_result: dict, review_result: dict) -> dict:
        self.log(f"Evaluating fix for issue {issue.get('rule')}")
        self.evaluation_result = None

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

        Please evaluate this fix according to your operational rules and submit your verdict.
        """

        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": user_message}
        ]

        done = False
        max_tries = 3
        current_tries = 0
        while not done and current_tries < max_tries:
            response = self.client.chat.completions.create(
                model=self.model_name, 
                messages=messages, 
                tools=self.get_tools(),
                tool_choice="auto"
            )
            message = response.choices[0].message
            if message.tool_calls:
                results = self.handle_tool_call(message)
                messages.append(message)
                messages.extend(results)
                
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "evaluate_fix":
                        done = True
                        break
            else:
                done = True
            current_tries += 1

        if self.evaluation_result:
            self.log(f"Evaluator Verdict: {self.evaluation_result['verdict']} - {self.evaluation_result['reasoning']}")
            return self.evaluation_result

        reply = response.choices[0].message.content if response.choices[0].message.content else "No reply content"
        self.log(f"Evaluator Agent completed with fallback reply: {reply}")
        return {
            "verdict": "RETRY",
            "reasoning": "Evaluator failed to output properly via tool call. Fallback reply: " + reply,
            "correctness_score": 0,
            "safety_score": 0,
            "readability_score": 0,
            "overall_score": 0.0
        }