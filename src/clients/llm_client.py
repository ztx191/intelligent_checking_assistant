import os
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv("../.env")

class ModelSettings(BaseModel):
    base_url: str = os.getenv("API_HUB_ENDPOINT")
    api_key: str = os.getenv("API_HUB_TOKEN")
    model: str = os.getenv("API_HUB_DEFAULT_AI_MODEL_ID")

    temperature: float = 0.1
    streaming: bool = False
    max_tokens: int = 5000


class LLMService:
    def __init__(self, settings: ModelSettings = None):
        self.settings = settings if settings else ModelSettings()
        self.client = OpenAI(
            api_key=self.settings.api_key,
            base_url=self.settings.base_url + "/v1"
        )

    def chat(self, system: str, query: str) -> str:
        """
        非流式
        :param system:
        :param query:
        :return:
        """
        message = [
            {"role": "system", "content": system},
            {"role": "user", "content": query}
        ]

        response = self.client.chat.completions.create(
            model=self.settings.model,
            messages=message,
            temperature=self.settings.temperature,
            stream=self.settings.streaming,
            max_tokens=self.settings.max_tokens
        )
        return response.choices[0].message.content




