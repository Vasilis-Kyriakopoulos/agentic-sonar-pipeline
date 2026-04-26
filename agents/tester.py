import os
import json
import subprocess
from typing import List, Dict
from agents.agent import Agent
import sys  

class TesterAgent(Agent):
    name = "Tester Agent"
    color = Agent.YELLOW

    def __init__(self, model_name: str, url: str, token: str, repo_path: str):
        super().__init__(model_name, url, token)
        self.repo_path = repo_path
        self.tool_mapping = {
            "check_testability": self.check_testability,
            "execute_test": self.execute_test
        }       
    
    system_message = (
        "You are an expert Python QA Engineer specializing in writing unit tests. "
        "Your task is to verify that fixes applied to a codebase successfully resolve SonarQube issues.\n\n"
        "OPERATIONAL RULES:\n"
        "1. FOCUS: Write tests only for the specific issue described.\n"
        "2. STEP 1: Always use the 'check_testability' tool first to determine if the issue can be unit tested.\n"
        "3. STEP 2: If testable, use the 'execute_test' tool to submit your pytest code.\n"
        "4. STEP 3: Analyze the test results. If your test fails, correct your test code and call 'execute_test' again.\n"
        "5. OUTPUT: When the test passes successfully, or if you determined the issue was not testable, reply with 'Success: [summary]'.\n"
    )

    check_testability_function = {
            "name": "check_testability",
            "description": "Evaluates whether the SonarQube issue affects runtime behavior and can be verified via a Python unit test.",
            "parameters": {
                "type": "object",
                "properties": {
                    "is_testable": {
                        "type": "boolean",
                        "description": "True if a unit test can verify the fix (e.g., bugs, mutable state, logic errors). False if it is purely stylistic or structural (e.g., TODO comments, naming conventions)."
                    },
                    "reason": {
                        "type": "string",
                        "description": "A brief explanation of why this issue is or is not testable."
                    }
                },
                "required": ["is_testable", "reason"],
                "additionalProperties": False
            }
        
    }

    execute_test_function = {
            "name": "execute_test",
            "description": "Executes the provided pytest code to verify the fix. Only call this after confirming testability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_code": {
                        "type": "string",
                        "description": "The complete Python (pytest) code to run. Must include all necessary imports and target the fixed file."
                    }
                },
                "required": ["test_code"],
                "additionalProperties": False
                }
            
        }

    def check_testability(self, is_testable: bool, reason: str) -> dict:
        """
        Checks if the SonarQube issue is testable.
        """
        self.log(f"Checking testability: {'Testable' if is_testable else 'Not Testable'} - {reason}")
        return {
            "test_passed": is_testable,
            "test_output": reason
        }

    def execute_test(self, test_code: str) -> dict:
        """
        Executes the provided pytest code to verify the fix.
        """
        self.log("Executing test code...")
        
        # Write the test code to a file
        with open(os.path.join(self.repo_path, f"test_sonar.py"), "w") as f:
            f.write(test_code)
        
        # Execute the test code using pytest
        result = subprocess.run([sys.executable, "-m", "pytest", "test_sonar.py"], cwd=self.repo_path, capture_output=True, text=True)
        
        # Clean up
        os.remove(os.path.join(self.repo_path, "test_sonar.py"))
        
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        return {
            "test_passed": result.returncode == 0,
         
            "test_output": output.strip()
        }

    def get_tools(self):
        return [{"type": "function", "function": self.check_testability_function},
                {"type": "function", "function": self.execute_test_function}]
    
    def test(self, issue: dict, source_code: str, fixed_code: str) -> dict:
        """
        Orchestrates the testability check process using the LLM and tool calls.
        Orchestrates the test generation process using the LLM and tool calls.
        """
        self.log("Generating test code...")
        self.test_code_data = None
        
        user_message = f"""
        ORIGINAL SONARQUBE ISSUE:
        - Rule: {issue.get('rule')}
        - Message: {issue.get('message')}
        ORIGINAL SOURCE CODE (Before Fix):
        ---
        {source_code} 
        ---
        PROPOSED FIXED CODE (Currently applied in the repo):
        ---
        {fixed_code}
        ---
        INSTRUCTIONS:
        Please follow your operational rules to verify this fix. The repository has ALREADY been updated with the proposed fixed code.
        """
        
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": user_message}
        ]

        done = False
        while not done:
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
            else:
                done = True
        reply = response.choices[0].message.content
        self.log(f"Tester Agent completed: {reply}")
        return {
            "test_passed": reply is not None and "Success" in reply,
            "test_output": reply
        }