from __future__ import annotations

from app.storage.database import Database
from app.storage.repositories.channels import ChannelsRepository
from app.storage.repositories.hashtags import HashtagsRepository
from app.storage.repositories.participants import ParticipantsRepository
from app.storage.repositories.prompts import PromptsRepository


class Storage:
    def __init__(self, db: Database):
        self.db = db
        self.channels = ChannelsRepository(db)
        self.hashtags = HashtagsRepository(db)
        self.participants = ParticipantsRepository(db)
        self.prompts = PromptsRepository(db)

    @classmethod
    async def create(cls, dsn: str) -> "Storage":
        db = await Database.connect(dsn)
        return cls(db)

    async def close(self) -> None:
        await self.db.close()
