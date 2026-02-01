from __future__ import annotations

from typing import Optional

import httpx

from app.config import DEEPSEEK_API_KEY
from app.config import DEEPSEEK_BASE_URL


async def generate_summary(text: str) -> Optional[str]:
    if not DEEPSEEK_API_KEY:
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

    headers = {'Authorization': f'Bearer {DEEPSEEK_API_KEY}'}

    async with httpx.AsyncClient(
        base_url=DEEPSEEK_BASE_URL, timeout=15
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
