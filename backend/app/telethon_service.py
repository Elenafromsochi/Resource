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


def chunked(values: list[int], size: int) -> list[list[int]]:
    return [values[i:i + size] for i in range(0, len(values), size)]


def guess_photo_mime(photo_bytes: bytes) -> str:
    if photo_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if photo_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if photo_bytes.startswith(b"GIF87a") or photo_bytes.startswith(b"GIF89a"):
        return "image/gif"
    return "image/jpeg"


def build_display_name(
    *,
    first_name: str | None,
    last_name: str | None,
    username: str | None,
    user_id: int,
) -> str:
    parts = [name for name in [first_name, last_name] if name]
    if parts:
        return " ".join(parts).strip()
    if username:
        return username
    return str(user_id)


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

    async def list_dialog_channels(self, limit: int | None = None) -> list[dict[str, Any]]:
        await self.start()
        channels: dict[int, dict[str, Any]] = {}
        try:
            async for dialog in self.client.iter_dialogs(limit=limit):
                entity = dialog.entity
                if not isinstance(
                    entity,
                    (types.Channel, types.ChannelForbidden, types.Chat, types.ChatForbidden),
                ):
                    continue
                channel_id = getattr(entity, 'id', None)
                if channel_id is None:
                    continue
                username = getattr(entity, 'username', None)
                title = getattr(entity, 'title', None) or username or str(channel_id)
                channels[int(channel_id)] = {
                    'id': int(channel_id),
                    'title': title,
                    'username': username,
                }
        except (RPCError, Exception) as exc:
            logger.warning('Telethon dialog fetch failed: %s', exc)
        return list(channels.values())

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
        from_channel_id = getattr(fwd, 'channel_id', None)
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
        include_replies: bool = True,
        include_forwarded: bool = True,
    ) -> list[dict[str, Any]]:
        await self.start()
        reply_cache: dict[tuple[int, int], dict[str, Any]] | None = (
            {} if include_replies else None
        )
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
                    reply_data = None
                    if include_replies and reply_cache is not None:
                        reply_data = await self.build_reply_data(message, reply_cache, channel_id)
                    forwarded = self.build_forwarded_data(message) if include_forwarded else None
                    payload = {
                        'channel_id': channel_id,
                        'message_id': message.id,
                        'user_id': message.sender_id,
                        'date': message_date,
                        'text': text,
                    }
                    if reply_data:
                        payload['reply_to'] = reply_data
                    if forwarded:
                        payload['forwarded'] = forwarded
                    channel_messages.append(payload)
                    if max_messages and len(channel_messages) >= max_messages:
                        break
                collected.extend(channel_messages)
        except (RPCError, Exception) as exc:
            logger.warning('Telethon failed to fetch channel messages: %s', exc)
        return collected

    async def _resolve_user_entities(
        self,
        user_ids: list[int],
    ) -> list[types.User | types.UserEmpty]:
        await self.start()
        resolved: list[types.User | types.UserEmpty] = []
        if not user_ids:
            return resolved
        unique_ids = list({int(user_id) for user_id in user_ids if user_id})
        for batch in chunked(unique_ids, 100):
            try:
                entities = await self.client.get_entities(batch)
                if not isinstance(entities, list):
                    entities = [entities]
                for entity in entities:
                    if isinstance(entity, (types.User, types.UserEmpty)):
                        resolved.append(entity)
            except (RPCError, Exception) as exc:
                logger.warning('Telethon failed to resolve user batch: %s', exc)
                for user_id in batch:
                    try:
                        entity = await self.client.get_entity(user_id)
                    except (RPCError, Exception) as inner_exc:
                        logger.warning('Telethon failed to resolve user %s: %s', user_id, inner_exc)
                        continue
                    if isinstance(entity, (types.User, types.UserEmpty)):
                        resolved.append(entity)
        return resolved

    async def fetch_user_profiles(
        self,
        user_ids: list[int],
    ) -> list[dict[str, Any]]:
        await self.start()
        entities = await self._resolve_user_entities(user_ids)
        profiles: list[dict[str, Any]] = []
        for entity in entities:
            user_id = getattr(entity, 'id', None)
            if user_id is None:
                continue

            username = getattr(entity, 'username', None)
            first_name = getattr(entity, 'first_name', None)
            last_name = getattr(entity, 'last_name', None)
            display_name = build_display_name(
                first_name=first_name,
                last_name=last_name,
                username=username,
                user_id=int(user_id),
            )

            about = None
            try:
                full = await self.client(functions.users.GetFullUserRequest(entity))
                full_user = getattr(full, 'full_user', None)
                if full_user is not None:
                    about = getattr(full_user, 'about', None)
                if about is None:
                    about = getattr(full, 'about', None)
            except (RPCError, Exception) as exc:
                logger.warning('Telethon failed to fetch user details for %s: %s', user_id, exc)

            photo_bytes = None
            photo_mime = None
            photo = getattr(entity, 'photo', None)
            if photo is not None:
                try:
                    photo_bytes = await self.client.download_profile_photo(
                        entity,
                        file=bytes,
                        download_big=False,
                    )
                except (RPCError, Exception) as exc:
                    logger.warning('Telethon failed to download photo for %s: %s', user_id, exc)
                if photo_bytes:
                    photo_mime = guess_photo_mime(photo_bytes)

            profiles.append(
                {
                    'user_id': int(user_id),
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'display_name': display_name,
                    'about': about,
                    'photo_bytes': photo_bytes,
                    'photo_mime': photo_mime,
                },
            )
        return profiles
