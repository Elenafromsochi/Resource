from __future__ import annotations

import logging

from openai import AsyncOpenAI
from openai import OpenAIError

from app.config import DEEPSEEK_API_KEY
from app.config import DEEPSEEK_BASE_URL
from app.config import DEEPSEEK_MODEL
from app.config import DEEPSEEK_TIMEOUT_SECONDS
from app.exceptions import ExternalServiceError


logger = logging.getLogger(__name__)


class DeepSeek:
    def __init__(self, api_key: str = DEEPSEEK_API_KEY) -> None:
        self.api_key = api_key
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=DEEPSEEK_BASE_URL,
            timeout=DEEPSEEK_TIMEOUT_SECONDS,
        )

    async def close(self) -> None:
        await self.client.close()

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
        model: str = DEEPSEEK_MODEL,
    ) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except OpenAIError as exc:
            logger.warning('DeepSeek request failed: %s', exc)
            raise ExternalServiceError('DeepSeek request failed') from exc
        if not response.choices:
            raise ExternalServiceError('DeepSeek response parsing failed')
        content = response.choices[0].message.content
        if not content:
            raise ExternalServiceError('DeepSeek response parsing failed')
        return content
