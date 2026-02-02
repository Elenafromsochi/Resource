from __future__ import annotations

from app.database import Database
from app.repositories.channels import ChannelsRepository


class Storage:
    def __init__(self, db: Database):
        self.db = db
        self.channels = ChannelsRepository(db)

    @classmethod
    async def create(cls, dsn: str) -> "Storage":
        db = await Database.connect(dsn)
        return cls(db)

    async def close(self) -> None:
        await self.db.close()
