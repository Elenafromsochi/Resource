from __future__ import annotations

from app.storage.database import Database
from app.storage.repositories.channels import ChannelsRepository
from app.storage.repositories.hashtags import HashtagsRepository


class Storage:
    def __init__(self, db: Database):
        self.db = db
        self.channels = ChannelsRepository(db)
        self.hashtags = HashtagsRepository(db)

    @classmethod
    async def create(cls, dsn: str) -> "Storage":
        db = await Database.connect(dsn)
        return cls(db)

    async def close(self) -> None:
        await self.db.close()
