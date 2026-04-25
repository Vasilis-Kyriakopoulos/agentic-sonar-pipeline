import os
import json
import subprocess
from typing import List, Dict
from agents.agent import Agent

class FixerAgent(Agent):
    name = "Fixer Agent"
    color = Agent.BLUE
    
    system_message = (
         "You are a Senior Software Engineer specializing in Python code quality and security. "
         "Your task is to resolve issues identified by SonarQube.\n\n"
         "OPERATIONAL RULES:\n"
         "1. FOCUS: Only address the specific issue described. Do not perform unrelated refactoring.\n"
         "2. PRECISION: Pay close attention to the 'line' number and the 'message' provided.\n"
         "3. SURGICAL EDITS: You MUST use the 'apply_surgical_fix' tool to replace only the necessary block of code. Avoid overwriting the entire file.\n"
         "4. OUTPUT: Inform when finished with message: 'Fix applied successfully'\n"
    )

    def __init__(self, model_name: str, url: str = None, token: str = None, repo_path: str = None) -> None:
        super().__init__(model_name, url, token)
        self.repo_path = repo_path or os.getcwd()
        self.tool_mapping = {
            "apply_surgical_fix": self.apply_surgical_fix
        }
        self.log(f"Fixer Agent ready at: {self.repo_path}")

    surgical_fix_function = {
        "name": "apply_surgical_fix",
        "description": "Applies a surgical fix to a specific file by replacing a block of code.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path of the file being fixed relative to the repo root."
                },
                "old_code": {
                    "type": "string",
                    "description": "The exact block of code to be replaced, including leading indentation and trailing newlines."
                },
                "new_code": {
                    "type": "string",
                    "description": "The new block of code to insert."
                },
                "explanation": {
                    "type": "string",
                    "description": "A brief explanation of why this fix resolves the issue."
                }
            },
            "required": ["file_path", "old_code", "new_code", "explanation"],
            "additionalProperties": False
        }
    }

    def get_tools(self):
        return [{"type": "function", "function": self.surgical_fix_function}]

    def apply_surgical_fix(self, file_path: str, old_code: str, new_code: str, explanation: str) -> str:
        # Prepend repo_path if not already absolute
        clean_path = file_path
        print("file_path", file_path)
        print("old_code", old_code)
        print("new_code", new_code)
        print("explanation", explanation)
        if ":" in clean_path:
            clean_path = clean_path.split(":")[-1]
        
        full_path = clean_path if os.path.isabs(clean_path) else os.path.join(self.repo_path, clean_path)

        try:
            if not os.path.exists(full_path):
                return f"Failure: File {full_path} does not exist."

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if old_code not in content:
                self.log(f"Failure: 'old_code' block not found in {clean_path}. Ensure exact match including indentation and newlines.")
                return f"Failure: 'old_code' block not found in {clean_path}. Ensure exact match including indentation and newlines."
            
            new_content = content.replace(old_code, new_code, 1)
            with open(full_path, "w", encoding="utf-8", newline='') as f:
                f.write(new_content)
            
            return f"Success: Fix applied. {explanation}"
        except Exception as e:
            return f"Error: {str(e)}"

    def setup_fix_branch(self, branch_name: str):
        """Prepares the repository for a new set of fixes."""
        self.log(f"Setting up branch: {branch_name}")
        try:

            # Check if in git repo
            subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=self.repo_path, check=True, capture_output=True)
            # Ensure we are on a clean state (optional but safer)
            subprocess.run(["git", "checkout", "main"], cwd=self.repo_path, capture_output=True,check=True)
            # Create/Switch to the branch
            result = subprocess.run(["git", "checkout", "-b", branch_name], cwd=self.repo_path, capture_output=True)
            if result.returncode != 0:
                 subprocess.run(["git", "checkout", branch_name], cwd=self.repo_path, check=True, capture_output=True)
            subprocess.run(["git", "restore", "."], cwd=self.repo_path, capture_output=True,check=True)
            return True
        except Exception as e:
            self.log(f"Git setup failed: {e}")
            return False

    def commit_fix(self, message: str):
        """Commits the current changes to the branch."""
        try:
            subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)
            subprocess.run(["git", "commit", "-m", message], cwd=self.repo_path, check=True)
            self.log(f"Committed: {message}")
            return True
        except Exception as e:
            self.log(f"Commit failed: {e}")
            return False

    def fix_code_file(self, issue: dict, source_code: str) -> str:
        """Applies a fix to the current branch."""
        self.log(f"Fixing issue {issue['rule']} at line {issue.get('line')}")
        
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": f"""
                I need you to fix a SonarQube issue in the file: '{issue['component']}'
                ISSUE DETAILS:
                - Rule ID: {issue['rule']}
                - Type: {issue['type']}
                - Line Number: {issue['line']}
                - SonarQube Message: {issue['message']}

                ORIGINAL SOURCE CODE:
                ---
                {source_code}
                ---
                INSTRUCTIONS:
                1. Analyze the code at line {issue['line']}.
                2. Identify the exact block of code (including indentation) that needs to be changed.
                3. Use 'apply_surgical_fix' to replace ONLY that block. 
                """}
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
                
                if any("Success" in str(r['content']) for r in results):
                    messages.append({"role": "user", "content": "The fix was applied successfully. Please provide a final summary."})
            else:
                done = True
            current_tries += 1
        if current_tries == max_tries:
            self.log(f"Fixer Agent failed to fix the issue within {max_tries} tries.")
            return "Fix failed within max tries"
        reply = response.choices[0].message.content
        self.log(f"Fixer Agent completed: {reply}")
        return reply
