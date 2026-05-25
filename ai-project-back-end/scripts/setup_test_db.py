from __future__ import annotations

import argparse
import asyncio
import os
from urllib.parse import urlsplit, urlunsplit

import asyncpg
from alembic import command
from alembic.config import Config


DEFAULT_TEST_DATABASE_URL = "postgresql+asyncpg://postgres:123456@localhost:5432/ai_test_platform_e2e"


def _database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL") or DEFAULT_TEST_DATABASE_URL


def _split_url(url: str) -> tuple[str, str]:
    parsed = urlsplit(url.replace("postgresql+asyncpg://", "postgresql://", 1))
    db_name = parsed.path.lstrip("/")
    if not db_name:
        raise RuntimeError("TEST_DATABASE_URL must include a database name")
    if "test" not in db_name.lower() and "e2e" not in db_name.lower():
        raise RuntimeError(f"Refusing to manage non-test database: {db_name}")
    admin_url = urlunsplit((parsed.scheme, parsed.netloc, "/postgres", parsed.query, parsed.fragment))
    return admin_url, db_name


async def _database_exists(conn: asyncpg.Connection, db_name: str) -> bool:
    value = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
    return value == 1


async def _terminate_connections(conn: asyncpg.Connection, db_name: str) -> None:
    await conn.execute(
        """
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = $1 AND pid <> pg_backend_pid()
        """,
        db_name,
    )


async def ensure_database(url: str, *, reset: bool = False, drop: bool = False) -> None:
    admin_url, db_name = _split_url(url)
    conn = await asyncpg.connect(admin_url)
    try:
        exists = await _database_exists(conn, db_name)
        if drop or reset:
            if exists:
                await _terminate_connections(conn, db_name)
                await conn.execute(f'DROP DATABASE "{db_name}"')
                exists = False
        if drop:
            return
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()


def run_migrations(url: str) -> None:
    os.environ["DATABASE_URL"] = url
    config = Config("alembic.ini")
    command.upgrade(config, "head")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create, reset, migrate, or drop the WeiTesting E2E database.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate the test database before migrating.")
    parser.add_argument("--drop", action="store_true", help="Drop the test database and exit.")
    args = parser.parse_args()

    url = _database_url()
    asyncio.run(ensure_database(url, reset=args.reset, drop=args.drop))
    if not args.drop:
        run_migrations(url)


if __name__ == "__main__":
    main()
