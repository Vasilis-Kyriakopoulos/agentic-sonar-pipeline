import logging
import json
from openai import OpenAI

class Agent:
    """
    An abstract superclass for Agents.
    Provides shared logging, OpenAI client initialization, and tool handling logic.
    """

    # Foreground colors
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Background color
    BG_BLACK = '\033[40m'
    
    # Reset code
    RESET = '\033[0m'

    name: str = "Base Agent"
    color: str = '\033[37m'

    def __init__(self, model_name: str, url: str = None, token: str = None) -> None:
        """
        Initializes the agent with common LLM configuration.
        """
        self.model_name = model_name
        self.client = OpenAI(api_key=token, base_url=url)
        self.log(f"Initialized with model: {self.model_name}")

    def log(self, message):
        """
        Log identifying the agent with its assigned color.
        """
        color_code = self.BG_BLACK + self.color
        formatted_message = f"[{self.name}] {message}"
        logging.info(color_code + formatted_message + self.RESET)

    def get_tools(self) -> list:
        """
        Override this to return a list of OpenAI tool definitions.
        """
        return []

    def handle_tool_call(self, message) -> list[dict]:
        """
        Generic tool caller. Maps tool names to class methods.
        Subclasses should define a 'tool_mapping' attribute.
        """
        if not hasattr(self, 'tool_mapping'):
            self.log("Error: 'tool_mapping' not defined in subclass.")
            return []

        results = []
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            tool_func = self.tool_mapping.get(tool_name)
            
            if tool_func:
                self.log(f"Executing tool: {tool_name}")
                result = tool_func(**arguments)
            else:
                self.log(f"Error: Tool '{tool_name}' not found in mapping.")
                result = f"Error: Tool '{tool_name}' not found."
            
            results.append({
                "role": "tool",
                "content": str(result),
                "tool_call_id": tool_call.id
            })
        return results
