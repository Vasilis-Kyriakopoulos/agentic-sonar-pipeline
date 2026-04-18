import re
from typing import List, Dict
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from agents.agent import Agent
import json
import os

class FixerAgent(Agent):
    name = "Fixer Agent"
    color = Agent.BLUE
    # Define rules 
    system_message = (
         "You are a Senior Software Engineer specializing in Python code quality and security. "
         "Your task is to resolve issues identified by SonarQube.\n\n"
         "OPERATIONAL RULES:\n"
         "1. FOCUS: Only address the specific issue described. Do not perform unrelated refactoring.\n"
         "2. PRECISION: Pay close attention to the 'line' number and the 'message' provided.\n"
         "3. INDENTATION: Ensure the Python indentation in your 'fixed_code' is perfectly consistent with the original file.\n"
         "4. TOOL USE: You MUST submit your fix by calling the 'apply_code_fix' tool.\n"
         "5. OUTPUT: Inform when finished with message: 'Fix applied successfully'"
         "6. FILE PATH:The folder of the file is 'patient-repo' is in the same directory as this file. The file path is provided in the issue details. Use it directly in the 'apply_code_fix' tool.\n"
        )

    def __init__(self, model_name: str, url: str = None, token: str = None) -> None:
        """
        Initializes the Fixer Agent with the necessary LLM configuration.

        The Fixer Agent is responsible for receiving SonarQube issues and generating 
        code fixes using an OpenAI-compatible API.

        Args:
            model_name (str): The name of the LLM model to use (e.g., 'gpt-4o', 'llama3').
            url (str): The base URL for the OpenAI-compatible API (OpenAI, Ollama, etc.).
            token (str): The API key or token required for authentication.

        Note:
            Sets up the internal OpenAI client and logs the agent's readiness state.
        """
        self.log("Initializing Fixer Agent")
        self.client = OpenAI(api_key=token, base_url=url)
        self.model_name = model_name
        self.log("Fixer Agent is ready")

    fix_function = {
            "name": "apply_code_fix",
            "description": "Applies a specific fix to a file to resolve a SonarQube issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "new_content": {"type": "string", "description": "The complete updated content of the file."}
                },
                "required": ["file_path", "fixed_code"]
            }     
    }

    def get_tools(self):
        """
        Return the json for the tools to be used
        """
        return [
            {"type": "function", "function": self.fix_function}
        ]

    def handle_tool_call(self, message):
        """
        Actually call the tools associated with this message
        """
        mapping = {
            "apply_code_fix": self.apply_code_fix,
        }
        results = []
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            tool = mapping.get(tool_name)
            result = tool(**arguments) if tool else ""
            results.append({"role": "tool", "content": result, "tool_call_id": tool_call.id})
        return results

    @staticmethod
    def apply_code_fix(file_path: str, new_content: str):
        """
        Physically overwrites the file with the fixed version.
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w+", encoding="utf-8") as f:
                f.write(new_content)
            return "File change Success"
        except Exception as e:
            print(f"Error writing to file {file_path}: {e}")
            return "File change Failure"


    def fix_code_file(self, issue: dict, source_code: str) -> str:
        """
        Orchestrates the code fix process by interacting with the LLM and executing tool calls.

        This method sends the SonarQube issue metadata and the source code context to the LLM. 
        It enters a loop to handle 'tool_calls', allowing the agent to use the 'apply_code_fix' 
        tool to propose changes. 

        The process follows these steps:
        1. Formulates a detailed prompt with rule ID, line number, and original code.
        2. Executes the LLM call with access to the 'apply_code_fix' tool.
        3. If the LLM requests a tool call, the method executes the physical file change via 
           'handle_tool_call' and appends the result to the conversation history.
        4. Continues until the LLM provides a final confirmation or summary.

        Args:
            issue (dict): The dictionary containing SonarQube issue metadata (key, rule, line, message).
            source_code (str): The full content of the file requiring a fix.

        Returns:
            str: The final explanation or status message from the Fixer Agent.
        """
        self.log("Fixer Agent is changing the code!!!")
        user_message = f"""
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
                2. Apply the fix suggested by the SonarQube message.
                3. Ensure the overall logic of the program remains unchanged.
                4. Use the 'apply_code_fix' tool to return the updated file content.
                """
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": user_message}
        ]
        done = False
        while not done:
            response = self.client.chat.completions.create(
                model=self.model_name, messages=messages, tools=self.get_tools()
            )
            if response.choices[0].finish_reason == "tool_calls":
                message = response.choices[0].message
                results = self.handle_tool_call(message)
                messages.append(message)
                messages.extend(results)
            else:
                done = True
        reply = response.choices[0].message.content
        self.log(f"Fixer Agent completed with: {reply}")
        return reply
            
        
