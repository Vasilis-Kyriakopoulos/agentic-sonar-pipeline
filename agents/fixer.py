import os
import subprocess
from typing import List
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
    )

    MAX_TOOL_CALLS = 5

    def __init__(self, model_name: str, url: str = None, token: str = None, repo_path: str = None) -> None:
        super().__init__(model_name, url, token)
        self.repo_path = repo_path or os.getcwd()
        self.tool_mapping = {
            "apply_surgical_fix": self.apply_surgical_fix
        }

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
            "required": ["file_path", "old_code", "new_code"],
            "additionalProperties": False
        }
    }

    def get_tools(self):
        return [{"type": "function", "function": self.surgical_fix_function}]

    def apply_surgical_fix(self, file_path: str, old_code: str, new_code: str, explanation: str = "") -> str:
        """Applies a surgical fix by replacing old_code with new_code in the target file."""
        clean_path = file_path.split(":")[-1] if ":" in file_path else file_path
        full_path = clean_path if os.path.isabs(clean_path) else os.path.join(self.repo_path, clean_path)

        try:
            if not os.path.exists(full_path):
                return f"Failure: File {full_path} does not exist."

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            matched_old_code = self._find_match(old_code, content, clean_path)
            if matched_old_code is None:
                return f"Failure: 'old_code' block not found in {clean_path}. Ensure exact match including indentation."

            new_content = content.replace(matched_old_code, new_code, 1)
            with open(full_path, "w", encoding="utf-8", newline='') as f:
                f.write(new_content)
            
            self.fix_applied = True
            return f"Success: Fix applied to {clean_path}. {explanation}"

        except Exception as e:
            return f"Error: {str(e)}"

    def _find_match(self, old_code: str, content: str, file_name: str) -> str | None:
        """Attempts to find old_code in content with progressive fallbacks. Returns the matched string or None."""
        # Exact match
        if old_code in content:
            return old_code
        
        # Fallback 1: Strip leading/trailing newlines only
        stripped_newlines = old_code.strip('\r\n')
        if stripped_newlines in content:
            self.log(f"Used newline-stripped fallback for match in {file_name}")
            return stripped_newlines
        
        # Fallback 2: Strip all outer whitespace (only if unique)
        stripped_all = old_code.strip()
        if stripped_all in content:
            if content.count(stripped_all) == 1:
                self.log(f"Used fully-stripped fallback for match in {file_name}")
                return stripped_all
            else:
                self.log(f"Stripped match is ambiguous ({content.count(stripped_all)} occurrences) in {file_name}")
                return None
        
        return None

    def setup_fix_branch(self, branch_name: str) -> bool:
        """Prepares the repository for a new set of fixes."""
        self.log(f"Setting up branch: {branch_name}")
        try:
            subprocess.run(["git", "restore", "."], cwd=self.repo_path, capture_output=True, check=True)
            subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=self.repo_path, check=True, capture_output=True)
            subprocess.run(["git", "checkout", "main"], cwd=self.repo_path, capture_output=True, check=True)
            
            result = subprocess.run(["git", "checkout", "-b", branch_name], cwd=self.repo_path, capture_output=True)
            if result.returncode != 0:
                subprocess.run(["git", "checkout", branch_name], cwd=self.repo_path, check=True, capture_output=True)
            
            subprocess.run(["git", "restore", "."], cwd=self.repo_path, capture_output=True, check=True)
            return True
        except Exception as e:
            self.log(f"Git setup failed: {e}")
            return False

    def commit_fix(self, message: str) -> bool:
        """Commits the current changes to the branch."""
        try:
            subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)
            subprocess.run(["git", "commit", "-m", message], cwd=self.repo_path, check=True)
            self.log(f"Committed: {message}")
            return True
        except Exception as e:
            self.log(f"Commit failed: {e}")
            return False

    def fix_code_file(self, issue: dict, source_code: str, reflection_messages: List[str]) -> str:
        """
        Runs the Fixer agentic loop: sends the issue to the LLM and lets it
        call apply_surgical_fix until the fix is applied or retries are exhausted.
        """
        self.log(f"Fixing issue {issue['rule']} at line {issue.get('line')}")
        self.fix_applied = False

        user_content = f"""
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
            """

        if reflection_messages:
            user_content += f"\n PREVIOUS FEEDBACK (use this to improve your fix):\n"
            for i, msg in enumerate(reflection_messages, 1):
                user_content += f"- Attempt {i}: {msg}\n"

        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": user_content}
        ]

        for attempt in range(self.MAX_TOOL_CALLS):
            response = self.client.chat.completions.create(
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

            if self.fix_applied:
                self.log("Fix applied successfully.")
                return message.content or "Fix applied successfully"

        if not self.fix_applied:
            self.log(f"Failed to apply fix within {self.MAX_TOOL_CALLS} tool calls.")
            return "Fix failed within max tries"

        reply = response.choices[0].message.content or "Fix applied"
        self.log(f"Fixer Agent completed: {reply}")
        return reply
