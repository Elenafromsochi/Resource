from __future__ import annotations

from pathlib import Path

from app.database import Database


def _get_migrations_dir() -> Path:
    return Path(__file__).resolve().parent / "migrations"


async def apply_migrations(db: Database) -> None:
    migrations_dir = _get_migrations_dir()
    if not migrations_dir.exists():
        return

    migration_files = sorted(migrations_dir.glob("*.sql"))
    for migration_path in migration_files:
        sql = migration_path.read_text(encoding="utf-8").strip()
        if not sql:
            continue
        await db.execute_script(sql)
