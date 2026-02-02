from __future__ import annotations

from typing import Any
import logging

import httpx

from app.config import DEEPSEEK_API_KEY


logger = logging.getLogger(__name__)


class DeepSeek:
    def __init__(self, api_key: str = DEEPSEEK_API_KEY) -> None:
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url='https://api.deepseek.com/v1',
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            timeout=httpx.Timeout(30.0),
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.2,
        model: str = 'deepseek-chat',
    ) -> str:
        payload: dict[str, Any] = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        response = await self.client.post('/chat/completions', json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning('DeepSeek request failed: %s', exc)
            raise
        data = response.json()
        return data['choices'][0]['message']['content']
