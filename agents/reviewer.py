import os
import json
from typing import List, Dict
from agents.agent import Agent

class ReviewerAgent(Agent):
    name = "Reviewer Agent"
    color = Agent.GREEN
    
    system_message = (
        "You are an elite Python Code Reviewer. Your job is to evaluate code changes "
        "made by other developers to fix SonarQube issues.\n"
        "Evaluate based on naming conventions, complexity, PEP8, and Pythonic patterns.\n"
        "You MUST use the 'submit_review' tool to provide your final scores."
    )

    def __init__(self, model_name: str, url: str = None, token: str = None) -> None:
        super().__init__(model_name, url, token)
        # Defining the mapping for the Agent base class to use
        self.tool_mapping = {
            "submit_review": self.submit_review
        }

    submit_review_function = {
        "name": "submit_review",
        "description": "Submits the code review scores and suggestions.",
        "parameters": {
            "type": "object",
            "properties": {
                "readability_score": {
                    "type": "integer",
                    "description": "Score from 1 to 10 evaluating how easy the code is to read."
                },
                "maintainability_score": {
                    "type": "integer",
                    "description": "Score from 1 to 10 evaluating PEP8 compliance and Pythonic patterns."
                },
                "suggestions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "A list of specific suggestions for improvement. Empty if the code is perfect."
                },
                "is_acceptable": {
                    "type": "boolean",
                    "description": "True if the code meets professional standards, False otherwise."
                }
            },
            "required": ["readability_score", "maintainability_score", "suggestions", "is_acceptable"],
            "additionalProperties": False
        }   
    }

    def get_tools(self):
        return [{"type": "function", "function": self.submit_review_function}]

    def submit_review(self, readability_score: int, maintainability_score: int, suggestions: list, is_acceptable: bool):
        """
        Tool implementation for submitting a review.
        """
        self.review_data = {
            "readability_score": readability_score,
            "maintainability_score": maintainability_score,
            "suggestions": suggestions,
            "is_acceptable": is_acceptable
        }
        self.log(f"Review Processed: {self.review_data}")
        return "Review submitted successfully"

    def review(self, issue: dict, source_code: str, fixed_code: str) -> dict:
        """
        Orchestrates the review process using the LLM and tool calls.
        """
        self.log("Starting code review...")
        self.review_data = None
        
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
        1. Did the fix successfully resolve the SonarQube issue?
        2. Did the fix accidentally alter or delete unrelated logic?
        3. Evaluate the new code based on readability and maintainability.
        
        Submit your evaluation using the 'submit_review' tool.
        """
        
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": user_message}
        ]
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=self.get_tools(),
            tool_choice="required"
        )
        
        message = response.choices[0].message
        if message.tool_calls:
            # Use the base class tool handler
            self.handle_tool_call(message)
            return self.review_data
        
        return {"error": "No review tool was called by the LLM"}
