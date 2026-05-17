import logging
import json
from typing import Optional
from openai import OpenAI
from sqlalchemy.orm import Session

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

    def __init__(
        self,
        model_name: str,
        url: str = None,
        token: str = None,
        db_session: Optional[Session] = None,
        run_id: Optional[int] = None,
    ) -> None:
        """
        Initializes the agent with common LLM configuration.

        Args:
            db_session: An open SQLAlchemy session for token-usage telemetry.
                        If None, token usage is logged to the console only.
            run_id:     The current PipelineRun.id to associate token usage with.
        """
        self.model_name = model_name
        self.client = OpenAI(api_key=token, base_url=url)
        self.db_session = db_session
        self.run_id = run_id
        self.log(f"Initialized with model: {self.model_name}")

    def log(self, message):
        """
        Log identifying the agent with its assigned color.
        """
        color_code = self.BG_BLACK + self.color
        formatted_message = f"[{self.name}] {message}"
        logging.info(color_code + formatted_message + self.RESET)

    def set_run_context(self, db_session: Session, run_id: int) -> None:
        """Attach or update the DB session and run_id mid-pipeline."""
        self.db_session = db_session
        self.run_id = run_id

    def _tracked_call(self, **kwargs):
        """
        Wrapper around client.chat.completions.create() that automatically
        logs prompt_tokens, completion_tokens, and estimated USD cost to the DB.
        Pass the same kwargs you would pass to the OpenAI client.
        """
        response = self.client.chat.completions.create(**kwargs)

        # --- Token telemetry ---
        usage = getattr(response, "usage", None)
        if usage:
            prompt_tokens     = getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens = getattr(usage, "completion_tokens", 0) or 0

            if self.db_session is not None:
                from database import log_token_usage
                log_token_usage(
                    session=self.db_session,
                    agent_name=self.name,
                    model_name=self.model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    run_id=self.run_id,
                )
            else:
                self.log(
                    f"Token usage (no DB): prompt={prompt_tokens}, "
                    f"completion={completion_tokens}"
                )

        return response

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
