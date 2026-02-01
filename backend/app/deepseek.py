from __future__ import annotations

from typing import Optional

import httpx

from app.config import settings


async def generate_summary(text: str) -> Optional[str]:
    if not settings.deepseek_api_key:
        return None

    payload = {
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'system', 'content': 'You are a concise assistant.'},
            {
                'role': 'user',
                'content': f'Summarize in one short sentence: {text}',
            },
        ],
        'temperature': 0.3,
    }

    headers = {'Authorization': f'Bearer {settings.deepseek_api_key}'}

    async with httpx.AsyncClient(
        base_url=settings.deepseek_base_url, timeout=15
    ) as client:
        response = await client.post(
            '/chat/completions',
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    try:
        return data['choices'][0]['message']['content'].strip()
    except (KeyError, IndexError, AttributeError):
        return None
