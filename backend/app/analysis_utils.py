from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import Any
import json
import logging
import re


logger = logging.getLogger(__name__)


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


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


def collect_participant_last_seen(
    messages: list[dict[str, Any]],
) -> dict[int, datetime]:
    last_seen: dict[int, datetime] = {}

    def update_seen(user_id: Any, message_date: Any) -> None:
        if not user_id or not isinstance(message_date, datetime):
            return
        user_id_int = int(user_id)
        current = last_seen.get(user_id_int)
        if current is None or message_date > current:
            last_seen[user_id_int] = message_date

    for message in messages:
        message_date = message.get('date')
        update_seen(message.get('user_id'), message_date)

        reply = message.get('reply_to') or {}
        update_seen(reply.get('user_id'), message_date)

        forwarded = message.get('forwarded') or {}
        update_seen(forwarded.get('from_user_id'), message_date)

    return last_seen
