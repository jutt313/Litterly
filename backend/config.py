import os
from pathlib import Path
from dotenv import load_dotenv

# Project root
ROOT_DIR = Path(__file__).parent.parent
BACKEND_DIR = Path(__file__).parent

# Load .env from project root
load_dotenv(ROOT_DIR / ".env")


class Settings:
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")

    # Defaults
    DEFAULT_LLM: str = "deepseek"  # deepseek, openai, claude, gemini
    DEFAULT_WORKERS: int = 10
    MAX_WORKERS: int = 20

    # Paths
    UPLOAD_DIR: Path = BACKEND_DIR / "data" / "uploads"
    OUTPUT_DIR: Path = BACKEND_DIR / "data" / "output"
    JOBS_DIR: Path = BACKEND_DIR / "data" / "jobs"
    PROMPTS_DIR: Path = BACKEND_DIR / "prompts"

    # Ensure dirs exist
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)

    def get_available_providers(self) -> list[str]:
        """Return list of providers that have API keys configured."""
        providers = []
        if self.DEEPSEEK_API_KEY:
            providers.append("deepseek")
        if self.OPENAI_API_KEY:
            providers.append("openai")
        if self.ANTHROPIC_API_KEY:
            providers.append("claude")
        if self.GEMINI_API_KEY:
            providers.append("gemini")
        return providers


settings = Settings()
