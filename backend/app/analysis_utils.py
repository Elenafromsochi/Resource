from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import Any
import json
import logging
import math
import re


logger = logging.getLogger(__name__)


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def truncate_text(text: str, max_tokens: int) -> str:
    if max_tokens <= 0:
        return ''
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip()


def normalize_tag(raw: str) -> str | None:
    value = raw.strip().lower()
    if not value:
        return None
    if not value.startswith('#'):
        value = f'#{value}'
    if any(char.isspace() for char in value):
        return None
    return value


def extract_json_payload(content: str) -> dict[str, Any]:
    payload = content.strip()
    if payload.startswith('```'):
        payload = re.sub(r'^```(?:json)?\s*', '', payload)
        payload = re.sub(r'\s*```$', '', payload)
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', payload, flags=re.DOTALL)
        if not match:
            logger.warning('Unable to extract JSON from DeepSeek response')
            raise
        return json.loads(match.group(0))


def merge_hashtag_counts(
    target: dict[str, int],
    items: list[dict[str, Any]],
) -> None:
    for item in items:
        raw_tag = str(item.get('tag', ''))
        tag = normalize_tag(raw_tag)
        if not tag:
            continue
        count = item.get('count', 0)
        try:
            count_value = int(count)
        except (TypeError, ValueError):
            continue
        if count_value <= 0:
            continue
        target[tag] = target.get(tag, 0) + count_value


def format_message_block(message: dict[str, Any]) -> str:
    date_value = message.get('date')
    if isinstance(date_value, datetime):
        date_value = date_value.isoformat()
    lines = [
        'message:',
        f"channel_id: {message.get('channel_id')}",
        f"message_id: {message.get('message_id')}",
        f"user_id: {message.get('user_id')}",
        f'date: {date_value}',
    ]
    reply = message.get('reply_to')
    if reply:
        lines.extend(
            [
                'reply:',
                f"  message_id: {reply.get('message_id')}",
                f"  user_id: {reply.get('user_id')}",
            ],
        )
        reply_text = reply.get('text')
        if reply_text:
            lines.append(f'  text: {reply_text}')
    forwarded = message.get('forwarded')
    if forwarded:
        lines.extend(
            [
                'forwarded:',
                f"  from_user_id: {forwarded.get('from_user_id')}",
                f"  from_channel_id: {forwarded.get('from_channel_id')}",
                f"  from_name: {forwarded.get('from_name')}",
                f"  from_message_id: {forwarded.get('from_message_id')}",
            ],
        )
    lines.append('text:')
    lines.append(message.get('text') or '')
    return '\n'.join(lines)


def trim_message_texts(message: dict[str, Any], max_tokens: int) -> dict[str, Any]:
    base_message = dict(message)
    reply = base_message.get('reply_to')
    if reply:
        base_message['reply_to'] = dict(reply)

    base_message['text'] = ''
    if base_message.get('reply_to'):
        base_message['reply_to']['text'] = ''

    base_tokens = estimate_tokens(format_message_block(base_message))
    available_tokens = max_tokens - base_tokens
    if available_tokens <= 0:
        if message.get('reply_to'):
            message['reply_to']['text'] = ''
        message['text'] = ''
        return message

    message_text = message.get('text') or ''
    reply_text = ''
    if message.get('reply_to'):
        reply_text = message['reply_to'].get('text') or ''

    message_tokens = estimate_tokens(message_text)
    reply_tokens = estimate_tokens(reply_text)
    total_tokens = message_tokens + reply_tokens
    if total_tokens <= available_tokens:
        return message

    if total_tokens == 0:
        return message

    message_share = max(1, math.floor(available_tokens * (message_tokens / total_tokens)))
    reply_share = max(0, available_tokens - message_share)

    message['text'] = truncate_text(message_text, message_share)
    if message.get('reply_to'):
        message['reply_to']['text'] = truncate_text(reply_text, reply_share)

    block_tokens = estimate_tokens(format_message_block(message))
    if block_tokens <= max_tokens:
        return message

    if message.get('reply_to') and message['reply_to'].get('text'):
        message['reply_to']['text'] = ''
        block_tokens = estimate_tokens(format_message_block(message))
        if block_tokens <= max_tokens:
            return message

    message_tokens = estimate_tokens(message.get('text') or '')
    excess = block_tokens - max_tokens
    if excess > 0 and message_tokens > 0:
        allowed_tokens = max(0, message_tokens - excess)
        message['text'] = truncate_text(message.get('text') or '', allowed_tokens)
    return message


def chunk_blocks(blocks: list[str], *, base_tokens: int, max_tokens: int) -> list[list[str]]:
    chunks: list[list[str]] = []
    current: list[str] = []
    current_tokens = base_tokens
    for block in blocks:
        block_tokens = estimate_tokens(block)
        if current and current_tokens + block_tokens > max_tokens:
            chunks.append(current)
            current = []
            current_tokens = base_tokens
        current.append(block)
        current_tokens += block_tokens
    if current:
        chunks.append(current)
    return chunks
