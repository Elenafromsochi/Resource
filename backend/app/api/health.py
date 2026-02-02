from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends

from app.api.dependencies import get_storage
from app.storage.mongo import ping_mongo
from app.storage import Storage

router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck(storage: Storage = Depends(get_storage)):
    db_ok = True
    try:
        await storage.db.execute("SELECT 1")
    except Exception:  # pragma: no cover - best effort
        db_ok = False

    mongo_ok = await ping_mongo()
    return {"postgres": db_ok, "mongo": mongo_ok}
