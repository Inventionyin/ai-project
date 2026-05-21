"""Create or reset the E2E test database.

Usage:
    python scripts/setup_test_db.py              # Create if missing
    python scripts/setup_test_db.py --reset       # Drop and recreate
    python scripts/setup_test_db.py --drop        # Drop only

Reads TEST_DATABASE_URL from env, falls back to the default.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys

import asyncpg
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from pathlib import Path

DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:123456@localhost:5432/ai_test_e2e",
)

_m = re.match(r"postgresql(?:\+\w+)?://([^:]+):([^@]+)@([^/:]+)(?::(\d+))?/(.+)", DB_URL)
if not _m:
    print(f"ERROR: Cannot parse TEST_DATABASE_URL: {DB_URL}")
    sys.exit(1)

PG_USER, PG_PASS, PG_HOST, PG_PORT, PG_DB = _m.groups()
PG_PORT = PG_PORT or "5432"


async def db_exists() -> bool:
    conn = await asyncpg.connect(host=PG_HOST, port=int(PG_PORT), user=PG_USER, password=PG_PASS, database="postgres")
    try:
        return await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", PG_DB) is not None
    finally:
        await conn.close()


async def create_db():
    conn = await asyncpg.connect(host=PG_HOST, port=int(PG_PORT), user=PG_USER, password=PG_PASS, database="postgres")
    try:
        await conn.execute(f'CREATE DATABASE "{PG_DB}"')
        print(f"Created database: {PG_DB}")
    finally:
        await conn.close()


async def drop_db():
    conn = await asyncpg.connect(host=PG_HOST, port=int(PG_PORT), user=PG_USER, password=PG_PASS, database="postgres")
    try:
        await conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1 AND pid <> pg_backend_pid()",
            PG_DB,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{PG_DB}"')
        print(f"Dropped database: {PG_DB}")
    finally:
        await conn.close()


def run_migrations():
    alembic_ini = str(Path(__file__).resolve().parents[1] / "alembic.ini")
    sync_url = DB_URL.replace("+asyncpg", "")
    cfg = AlembicConfig(alembic_ini)
    cfg.set_main_option("sqlalchemy.url", sync_url)
    alembic_command.upgrade(cfg, "head")
    print("Migrations applied: head")


async def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "setup"

    if action == "--drop":
        if await db_exists():
            await drop_db()
        else:
            print(f"Database {PG_DB} does not exist, nothing to drop.")
        return

    if action == "--reset":
        if await db_exists():
            await drop_db()
        await create_db()
        run_migrations()
        return

    # Default: create if missing.
    if await db_exists():
        print(f"Database {PG_DB} already exists. Use --reset to recreate.")
    else:
        await create_db()
        run_migrations()


if __name__ == "__main__":
    asyncio.run(main())
