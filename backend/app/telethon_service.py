from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import Any
import logging

from telethon import TelegramClient
from telethon import functions
from telethon import types
from telethon.errors import RPCError
from telethon.sessions import StringSession

from app.config import TELEGRAM_API_HASH
from app.config import TELEGRAM_API_ID
from app.config import TELETHON_SESSION


logger = logging.getLogger(__name__)


def normalize_message_date(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def extract_peer_id(peer: Any) -> int | None:
    if isinstance(peer, types.PeerUser):
        return peer.user_id
    if isinstance(peer, types.PeerChannel):
        return peer.channel_id
    if isinstance(peer, types.PeerChat):
        return peer.chat_id
    return None


class TelegramService:
    def __init__(self) -> None:
        self.client = TelegramClient(
            StringSession(TELETHON_SESSION),
            TELEGRAM_API_ID,
            TELEGRAM_API_HASH,
        )

    async def start(self) -> None:
        if not self.client.is_connected():
            await self.client.connect()

    async def close(self) -> None:
        await self.client.disconnect()

    async def resolve_channel(self, username: str) -> dict[str, Any] | None:
        await self.start()
        try:
            entity = await self.client.get_entity(username)
            if entity is None:
                return None

            title = getattr(entity, 'title', None)
            entity_username = getattr(entity, 'username', None) or username
            entity_id = getattr(entity, 'id', None)
            return {
                'id': entity_id,
                'title': title or entity_username,
                'username': entity_username,
            }
        except (RPCError, Exception) as exc:
            logger.warning('Telethon failed for %s: %s', username, exc)
            return None

    async def search_channels(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        await self.start()
        try:
            result = await self.client(
                functions.contacts.SearchRequest(
                    q=query,
                    limit=limit,
                ),
            )
            channels: list[dict[str, Any]] = []
            for chat in result.chats:
                if not isinstance(chat, types.Channel) or chat.megagroup:
                    continue

                description = None
                try:
                    full = await self.client(functions.channels.GetFullChannelRequest(chat))
                    description = getattr(full.full_chat, 'about', None)
                except (RPCError, Exception) as exc:
                    logger.warning(
                        'Telethon failed to fetch channel details for %s: %s',
                        chat.id,
                        exc,
                    )

                channels.append(
                    {
                        'id': chat.id,
                        'title': chat.title or chat.username or str(chat.id),
                        'username': chat.username,
                        'description': description,
                    },
                )
            return channels
        except (RPCError, Exception) as exc:
            logger.warning('Telethon channel search failed for %s: %s', query, exc)
            return []

    async def build_reply_data(
        self,
        message: types.Message,
        reply_cache: dict[tuple[int, int], dict[str, Any]],
        channel_id: int,
    ) -> dict[str, Any] | None:
        reply_id = message.reply_to_msg_id
        if not reply_id:
            return None
        cache_key = (channel_id, reply_id)
        cached = reply_cache.get(cache_key)
        if cached:
            return cached
        reply_data: dict[str, Any] = {
            'message_id': reply_id,
            'user_id': None,
            'text': '',
        }
        try:
            reply_message = await message.get_reply_message()
        except (RPCError, Exception) as exc:
            logger.warning('Telethon failed to fetch reply %s: %s', reply_id, exc)
            reply_message = None
        if reply_message:
            reply_data = {
                'message_id': reply_message.id,
                'user_id': reply_message.sender_id,
                'text': reply_message.message or '',
            }
        reply_cache[cache_key] = reply_data
        return reply_data

    def build_forwarded_data(self, message: types.Message) -> dict[str, Any] | None:
        if not message.fwd_from:
            return None
        fwd = message.fwd_from
        from_user_id = None
        from_channel_id = fwd.channel_id
        if fwd.from_id:
            peer_id = extract_peer_id(fwd.from_id)
            if isinstance(fwd.from_id, types.PeerUser):
                from_user_id = peer_id
            if isinstance(fwd.from_id, types.PeerChannel):
                from_channel_id = peer_id
        from_name = fwd.from_name or fwd.post_author
        return {
            'from_user_id': from_user_id,
            'from_channel_id': from_channel_id,
            'from_name': from_name,
            'from_message_id': fwd.channel_post,
        }

    async def fetch_channel_messages(
        self,
        channels: list[dict[str, Any]],
        *,
        start_date: datetime,
        end_date: datetime,
        max_messages: int | None = None,
    ) -> list[dict[str, Any]]:
        await self.start()
        reply_cache: dict[tuple[int, int], dict[str, Any]] = {}
        collected: list[dict[str, Any]] = []
        try:
            for channel in channels:
                channel_id = int(channel['id'])
                username = channel.get('username')
                lookup = username or channel_id
                entity = await self.client.get_entity(lookup)
                channel_messages: list[dict[str, Any]] = []
                async for message in self.client.iter_messages(entity, offset_date=end_date):
                    message_date = normalize_message_date(message.date)
                    if message_date < start_date:
                        break
                    if message_date > end_date:
                        continue
                    text = message.message or ''
                    if not text:
                        continue
                    reply_data = await self.build_reply_data(message, reply_cache, channel_id)
                    forwarded = self.build_forwarded_data(message)
                    channel_messages.append(
                        {
                            'channel_id': channel_id,
                            'message_id': message.id,
                            'user_id': message.sender_id,
                            'date': message_date,
                            'text': text,
                            'reply_to': reply_data,
                            'forwarded': forwarded,
                        },
                    )
                    if max_messages and len(channel_messages) >= max_messages:
                        break
                collected.extend(channel_messages)
        except (RPCError, Exception) as exc:
            logger.warning('Telethon failed to fetch channel messages: %s', exc)
        return collected
