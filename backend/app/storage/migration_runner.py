from __future__ import annotations

from app.config import MIGRATIONS_DIR
from app.storage.database import Database


async def apply_migrations(db: Database) -> None:
    if not MIGRATIONS_DIR.exists():
        return

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    for migration_path in migration_files:
        sql = migration_path.read_text(encoding="utf-8").strip()
        if not sql:
            continue
        await db.execute_script(sql)
