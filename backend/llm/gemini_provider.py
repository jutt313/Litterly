import json
import re
import google.generativeai as genai
from backend.llm.base import BaseLLM
from backend.config import settings


class GeminiLLM(BaseLLM):
    """Google Gemini LLM provider."""

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = self.model.generate_content(full_prompt)
        return response.text

    async def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
        json_system = system_prompt + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation, just JSON."
        full_prompt = f"{json_system}\n\n{prompt}"

        response = self.model.generate_content(full_prompt)
        text = response.text

        # Try to extract JSON if wrapped in markdown
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            text = json_match.group(1)

        return json.loads(text.strip())
