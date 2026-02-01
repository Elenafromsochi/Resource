from __future__ import annotations

import json
from typing import Any

import httpx


class OpenAIService:
    def __init__(
        self,
        api_key: str | None,
        gpt_model: str,
        whisper_model: str,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.gpt_model = gpt_model
        self.whisper_model = whisper_model
        self._client = httpx.AsyncClient(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    async def close(self) -> None:
        await self._client.aclose()

    async def transcribe_voice(self, audio_bytes: bytes, filename: str) -> str | None:
        if not self.api_key:
            return None
        files = {"file": (filename, audio_bytes)}
        data = {"model": self.whisper_model}
        response = await self._client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers=self._headers(),
            data=data,
            files=files,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("text")

    async def parse_resource_fields(
        self, text: str, has_photo: bool = False, link: str | None = None
    ) -> dict[str, Any]:
        if not self.api_key:
            return {}
        system = (
            "Ты ассистент для кооператива. Извлеки структуру карточки ресурса. "
            "Верни только JSON."
        )
        user = {
            "text": text,
            "has_photo": has_photo,
            "link": link,
        }
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    "Извлеки поля: category, condition, estimated_value, "
                    "exchange_type (gift|barter|money), resource_type "
                    "(item|service|experience). "
                    f"Данные: {json.dumps(user, ensure_ascii=False)}"
                ),
            },
        ]
        response = await self._client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=self._headers(),
            json={
                "model": self.gpt_model,
                "messages": messages,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}

