from backend.llm.base import BaseLLM
from backend.llm.deepseek_provider import DeepSeekLLM
from backend.llm.openai_provider import OpenAILLM
from backend.llm.claude_provider import ClaudeLLM
from backend.llm.gemini_provider import GeminiLLM


def get_llm(provider: str = "deepseek") -> BaseLLM:
    """Factory function to get the right LLM provider."""
    providers = {
        "deepseek": DeepSeekLLM,
        "openai": OpenAILLM,
        "claude": ClaudeLLM,
        "gemini": GeminiLLM,
    }

    if provider not in providers:
        available = list(providers.keys())
        raise ValueError(f"Unknown LLM provider '{provider}'. Available: {available}")

    return providers[provider]()
