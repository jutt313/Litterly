from abc import ABC, abstractmethod
from typing import Any
from backend.llm.base import BaseLLM


class BaseAgent(ABC):
    """Abstract base class for all pipeline agents."""

    name: str = "base"

    def __init__(self, llm: BaseLLM | None = None):
        self.llm = llm

    @abstractmethod
    async def run(self, input_data: Any) -> Any:
        """Execute this agent's task.

        Args:
            input_data: Output from the previous agent in the pipeline.

        Returns:
            Processed data to pass to the next agent.
        """
        ...
