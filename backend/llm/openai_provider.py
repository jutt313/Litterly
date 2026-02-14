import json
from openai import AsyncOpenAI
from backend.llm.base import BaseLLM
from backend.config import settings


class OpenAILLM(BaseLLM):
    """OpenAI GPT LLM provider."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=8192,
        )
        return response.choices[0].message.content or ""

    async def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
        json_system = system_prompt + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation, just JSON."
        messages = []
        if json_system:
            messages.append({"role": "system", "content": json_system})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=8192,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content or "{}"
        return json.loads(text)
