import datetime
import os
import sys
import subprocess
from typing import List
from agents.agent import Agent

class TesterAgent(Agent):
    name = "Tester Agent"
    color = Agent.YELLOW

    MAX_TOOL_CALLS = 7

    system_message = (
        "You are an expert Python QA Engineer specializing in writing unit tests. "
        "Your task is to verify that fixes applied to a codebase successfully resolve SonarQube issues.\n\n"
        "OPERATIONAL RULES:\n"
        "1. FOCUS: Write tests only for the specific issue described.\n"
        "2. STEP 1: Always use the 'check_testability' tool first to determine if the issue can be unit tested.\n"
        "3. STEP 2: If testable, use the 'execute_test' tool to submit your pytest code.\n"
        "4. STEP 3: Analyze the test results. If your test fails, correct your test code and call 'execute_test' again.\n"
        "5. OUTPUT: When the test passes successfully, or if you determined the issue was not testable, use the 'submit_test_result' tool to provide the final result.\n"
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

    submit_test_result_function = {
        "name": "submit_test_result",
        "description": "Submits the final result of the test generation and execution process.",
        "parameters": {
            "type": "object",
            "properties": {
                "test_passed": {
                    "type": "boolean",
                    "description": "True if the tests passed successfully or if the issue was not testable. False otherwise."
                },
                "summary": {
                    "type": "string",
                    "description": "A summary of the test execution, including the reasoning if it was not testable, or a brief explanation of the tests performed."
                }
            },
            "required": ["test_passed", "summary"],
            "additionalProperties": False
        }
    }

    # Maximum time (seconds) a test is allowed to run before being killed.
    TEST_TIMEOUT_SECONDS = 60

    def __init__(self, model_name: str, url: str, token: str, repo_path: str):
        super().__init__(model_name, url, token)
        self.repo_path = repo_path
        self.tool_mapping = {
            "check_testability": self.check_testability,
            "execute_test": self.execute_test,
            "submit_test_result": self.submit_test_result
        }

    def get_tools(self):
        return [
            {"type": "function", "function": self.check_testability_function},
            {"type": "function", "function": self.execute_test_function},
            {"type": "function", "function": self.submit_test_result_function}
        ]

    # --- Tool Implementations ---

    def check_testability(self, is_testable: bool, reason: str) -> str:
        """Evaluates whether the issue can be meaningfully unit tested."""
        status = "Testable" if is_testable else "Not Testable"
        self.log(f"Testability check: {status} — {reason}")
        return f"{status}: {reason}"

    def execute_test(self, test_code: str) -> str:
        """Writes test code to a temp file and runs pytest directly via subprocess.
        The app already runs inside Docker, so no additional sandboxing is needed."""
        self.log("Executing test code...")
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        test_file = os.path.join(self.repo_path, f"test_sonar_{now}.py")

        try:
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(test_code)

            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-v"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self.TEST_TIMEOUT_SECONDS,
            )
            output = (result.stdout or "") + "\n" + (result.stderr or "")
            passed = result.returncode == 0
            self.log(f"Test {'PASSED' if passed else 'FAILED'} (exit code {result.returncode})")
            return f"{'PASSED' if passed else 'FAILED'}\n\n{output.strip()}"

        except subprocess.TimeoutExpired:
            self.log("⏱️ Test timed out.")
            return "FAILED\n\nERROR: Test execution timed out (exceeded time limit)."

        except Exception as e:
            self.log(f"Test execution error: {e}")
            return f"ERROR: Test execution failed: {str(e)}"

        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def submit_test_result(self, test_passed: bool, summary: str) -> str:
        """Captures the LLM's final test verdict into self.test_result_data."""
        self.test_result_data = {
            "test_passed": test_passed,
            "test_output": summary
        }
        self.log(f"Test result submitted: passed={test_passed}")
        return "Test result submitted successfully"

    def test(self, issue: dict, source_code: str, fixed_code: str) -> dict:
        """
        Runs the Tester agentic loop: the LLM checks testability, writes/runs
        tests, and submits a final verdict via submit_test_result.
        """
        self.log("Starting test generation...")
        self.test_result_data = None

        user_message = f"""
        ORIGINAL SONARQUBE ISSUE:
        - File Path: {issue.get('component')}
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

        CRITICAL IMPORT RULE: When writing your test, you MUST use the correct import path based on the File Path. For example, if the file is 'pokedex/helper.py' (or 'project:pokedex/helper.py'), you should use 'from pokedex.helper import ...'. DO NOT use placeholders like 'your_module'.

        CRITICAL TESTING RULE: If the code interacts with a database, file system, or external service, you MUST use `unittest.mock` (e.g., `MagicMock`, `patch`) to mock the dependencies rather than trying to set up a real database schema or environment.

        PYTHON MOCKING TIP: Remember Python's name mangling for private attributes! If you need to mock a private attribute like `__conn` in a class `ConnectionWrapper`, you MUST set it using its mangled name `_ConnectionWrapper__conn` (e.g., `wrapper._ConnectionWrapper__conn = MagicMock()`) so the original class methods can find it.
        """

        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": user_message}
        ]

        for attempt in range(self.MAX_TOOL_CALLS):
            response = self._tracked_call(
                model=self.model_name,
                messages=messages,
                tools=self.get_tools(),
                tool_choice="auto"
            )
            message = response.choices[0].message

            if not message.tool_calls:
                break

            results = self.handle_tool_call(message)
            messages.append(message)
            messages.extend(results)

            if self.test_result_data is not None:
                break

        if self.test_result_data:
            self.log(f"Tester completed: {self.test_result_data['test_output']}")
            return self.test_result_data
        self.log("Tester did not submit a structured result. Defaulting to failure.")
        return {
            "test_passed": False,
            "test_output": "Tester agent did not produce a structured result within the allowed tool calls."
        }