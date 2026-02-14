import json
import re
from anthropic import AsyncAnthropic
from backend.llm.base import BaseLLM
from backend.config import settings


class ClaudeLLM(BaseLLM):
    """Anthropic Claude LLM provider."""

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-5-20250929"

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=system_prompt if system_prompt else "",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
        json_system = system_prompt + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation, just JSON."

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=json_system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text

        # Try to extract JSON if wrapped in markdown
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            text = json_match.group(1)

        return json.loads(text.strip())
