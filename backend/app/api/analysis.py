from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi import Depends

from app.analysis_utils import ensure_aware
from app.analysis_utils import extract_json_payload
from app.analysis_utils import format_message_block
from app.analysis_utils import merge_hashtag_counts
from app.api.dependencies import get_deepseek
from app.api.dependencies import get_storage
from app.api.dependencies import get_telegram
from app.config import DEEPSEEK_MAX_OUTPUT_TOKENS
from app.config import DEEPSEEK_TEMPERATURE
from app.deepseek import DeepSeek
from app.exceptions import ExternalServiceError
from app.exceptions import NotFoundError
from app.exceptions import ValidationError
from app.schemas import HashtagAnalysisRequest
from app.schemas import HashtagAnalysisResponse
from app.schemas import HashtagFrequency
from app.storage import Storage
from app.telethon_service import TelegramService


logger = logging.getLogger(__name__)

router = APIRouter(prefix='/analysis', tags=['analysis'])


@router.post('/hashtags', response_model=HashtagAnalysisResponse)
async def analyze_hashtags(
    payload: HashtagAnalysisRequest,
    storage: Storage = Depends(get_storage),
    deepseek: DeepSeek = Depends(get_deepseek),
    telegram: TelegramService = Depends(get_telegram),
):
    start_date = ensure_aware(payload.start_date)
    end_date = ensure_aware(payload.end_date)
    if end_date < start_date:
        raise ValidationError('End date must be after start date')

    prompt = await storage.prompts.get_by_id(payload.prompt_id)
    if not prompt:
        raise NotFoundError('Prompt not found')

    if payload.channel_ids:
        channels = await storage.channels.list_by_ids(payload.channel_ids)
        channel_ids = [channel['id'] for channel in channels]
        missing = [channel_id for channel_id in payload.channel_ids if channel_id not in channel_ids]
        if missing:
            raise NotFoundError(f'Channels not found: {missing}')
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
        )

    messages = await telegram.fetch_channel_messages(
        channels,
        start_date=start_date,
        end_date=end_date,
        max_messages=payload.max_messages_per_channel,
        include_replies=False,
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
        )

    existing_hashtags = await storage.hashtags.list_all()
    counts: dict[str, int] = {}
    blocks = [format_message_block(message) for message in messages]
    try:
        responses = await deepseek.chat_in_chunks(
            system_prompt=prompt['content'],
            hashtags=existing_hashtags,
            message_blocks=blocks,
            max_tokens=DEEPSEEK_MAX_OUTPUT_TOKENS,
            temperature=DEEPSEEK_TEMPERATURE,
        )
    except ExternalServiceError:
        raise
    except Exception as exc:
        logger.warning('DeepSeek analysis failed: %s', exc)
        raise ExternalServiceError('DeepSeek request failed') from exc

    for content in responses:
        try:
            payload_data = extract_json_payload(content)
        except Exception as exc:
            logger.warning('DeepSeek response parsing failed: %s', exc)
            raise ExternalServiceError('DeepSeek response parsing failed') from exc
        if not isinstance(payload_data, dict):
            raise ExternalServiceError('DeepSeek response parsing failed')

        items = payload_data.get('hashtags', [])
        if isinstance(items, list):
            merge_hashtag_counts(counts, items)

    existing_set = set(existing_hashtags)

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
    )
