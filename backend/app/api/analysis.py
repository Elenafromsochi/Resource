from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from app.analysis_utils import chunk_blocks
from app.analysis_utils import ensure_aware
from app.analysis_utils import estimate_tokens
from app.analysis_utils import extract_json_payload
from app.analysis_utils import format_message_block
from app.analysis_utils import merge_hashtag_counts
from app.analysis_utils import trim_message_texts
from app.api.dependencies import get_deepseek
from app.api.dependencies import get_storage
from app.deepseek import DeepSeek
from app.schemas import HashtagAnalysisRequest
from app.schemas import HashtagAnalysisResponse
from app.schemas import HashtagFrequency
from app.storage import Storage
from app.telethon_service import fetch_channel_messages


logger = logging.getLogger(__name__)

router = APIRouter(prefix='/analysis', tags=['analysis'])

DEFAULT_MAX_INPUT_TOKENS = 12000
DEFAULT_MAX_OUTPUT_TOKENS = 1000

SYSTEM_PROMPT = (
    'You analyze Telegram channel messages. '
    'Follow the instruction in the user prompt block. '
    'Use existing hashtags as hints but feel free to suggest new ones. '
    'Count hashtags only within the provided messages. '
    'Return JSON only in this shape: '
    '{"hashtags":[{"tag":"#example","count":3}]}'
)


def build_base_prompt(prompt: str, hashtags: list[str]) -> str:
    hashtags_block = '\n'.join(hashtags) if hashtags else ''
    return '\n'.join(
        [
            'PROMPT:',
            prompt,
            '',
            'EXISTING_HASHTAGS:',
            hashtags_block,
            '',
            'MESSAGES:',
        ],
    ).strip()


@router.post('/hashtags', response_model=HashtagAnalysisResponse)
async def analyze_hashtags(
    payload: HashtagAnalysisRequest,
    storage: Storage = Depends(get_storage),
    deepseek: DeepSeek = Depends(get_deepseek),
):
    start_date = ensure_aware(payload.start_date)
    end_date = ensure_aware(payload.end_date)
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='End date must be after start date',
        )

    prompt = await storage.prompts.get_by_id(payload.prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Prompt not found',
        )

    if payload.channel_ids:
        channels = await storage.channels.list_by_ids(payload.channel_ids)
        channel_ids = [channel['id'] for channel in channels]
        missing = [channel_id for channel_id in payload.channel_ids if channel_id not in channel_ids]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Channels not found: {missing}',
            )
    else:
        channels = await storage.channels.list()
        channel_ids = [channel['id'] for channel in channels]

    if not channel_ids:
        return HashtagAnalysisResponse(
            prompt_id=payload.prompt_id,
            start_date=start_date,
            end_date=end_date,
            channels=[],
            total_messages=0,
            hashtags=[],
            added_to_db=[] if payload.save_to_db else None,
        )

    existing_hashtags = await storage.hashtags.list_all()
    base_prompt = build_base_prompt(prompt['content'], existing_hashtags)
    base_tokens = estimate_tokens(base_prompt)
    max_input_tokens = payload.max_input_tokens or DEFAULT_MAX_INPUT_TOKENS
    if base_tokens >= max_input_tokens:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Prompt and hashtags exceed token budget',
        )

    messages = await fetch_channel_messages(
        channel_ids,
        start_date=start_date,
        end_date=end_date,
        max_messages=payload.max_messages_per_channel,
    )
    messages.sort(key=lambda item: item['date'])
    if not messages:
        return HashtagAnalysisResponse(
            prompt_id=payload.prompt_id,
            start_date=start_date,
            end_date=end_date,
            channels=channel_ids,
            total_messages=0,
            hashtags=[],
            added_to_db=[] if payload.save_to_db else None,
        )

    max_block_tokens = max_input_tokens - base_tokens
    trimmed = [trim_message_texts(message, max_block_tokens) for message in messages]
    blocks = [format_message_block(message) for message in trimmed]
    chunks = chunk_blocks(blocks, base_tokens=base_tokens, max_tokens=max_input_tokens)

    counts: dict[str, int] = {}
    for chunk in chunks:
        user_content = base_prompt + '\n\n' + '\n\n'.join(chunk)
        try:
            content = await deepseek.chat(
                [
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_content},
                ],
                max_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
                temperature=0.1,
            )
        except Exception as exc:
            logger.warning('DeepSeek analysis failed: %s', exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail='DeepSeek request failed',
            ) from exc

        try:
            payload_data = extract_json_payload(content)
        except Exception as exc:
            logger.warning('DeepSeek response parsing failed: %s', exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail='DeepSeek response parsing failed',
            ) from exc
        if not isinstance(payload_data, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail='DeepSeek response parsing failed',
            )

        items = payload_data.get('hashtags', [])
        if isinstance(items, list):
            merge_hashtag_counts(counts, items)

    existing_set = set(existing_hashtags)
    added: list[str] = []
    if payload.save_to_db:
        for tag in counts:
            if tag in existing_set:
                continue
            created = await storage.hashtags.create(tag=tag)
            existing_set.add(created['tag'])
            added.append(created['tag'])

    hashtags_sorted = sorted(
        counts.items(),
        key=lambda item: (-item[1], item[0]),
    )
    hashtags = [
        HashtagFrequency(tag=tag, count=count, in_db=tag in existing_set)
        for tag, count in hashtags_sorted
    ]

    return HashtagAnalysisResponse(
        prompt_id=payload.prompt_id,
        start_date=start_date,
        end_date=end_date,
        channels=channel_ids,
        total_messages=len(messages),
        hashtags=hashtags,
        added_to_db=added if payload.save_to_db else None,
    )
