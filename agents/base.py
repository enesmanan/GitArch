from abc import ABC, abstractmethod
from gemini_client import GeminiClient
from tools import ToolExecutor, get_tool_declarations


class BaseAgent(ABC):
    name: str = "base"
    system_prompt: str = ""

    def __init__(self, client: GeminiClient):
        self.client = client

    @abstractmethod
    def run(self, context: dict, **kwargs) -> dict:
        ...

    def _generate(self, user_prompt: str) -> str:
        return self.client.generate(self.system_prompt, user_prompt)


class ToolUsingAgent(BaseAgent):
    def __init__(self, client: GeminiClient, executor: ToolExecutor):
        super().__init__(client)
        self.executor = executor
        self.declarations = get_tool_declarations()

    def _generate_with_tools(self, user_prompt: str) -> str:
        return self.client.generate_with_tools(
            self.system_prompt,
            user_prompt,
            self.declarations,
            self.executor,
        )
