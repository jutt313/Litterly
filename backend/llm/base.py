from abc import ABC, abstractmethod


class BaseLLM(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate a text response from the LLM.

        Args:
            prompt: The user prompt / main content.
            system_prompt: Optional system-level instructions.

        Returns:
            The LLM's text response.
        """
        ...

    @abstractmethod
    async def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
        """Generate a JSON response from the LLM.

        Args:
            prompt: The user prompt / main content.
            system_prompt: Optional system-level instructions.

        Returns:
            Parsed JSON dict from the LLM's response.
        """
        ...
