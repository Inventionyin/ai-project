"""E2E test fixtures: isolated test database with real migrations.

Usage:
    TEST_DATABASE_URL=postgresql+asyncpg://postgres:123456@localhost:5432/ai_test_e2e \
        pytest tests/e2e -v

The conftest creates the test DB (if missing), runs alembic migrations,
provides an async client with real auth, and drops the DB after the session.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncGenerator

import asyncpg
import pytest
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Override DATABASE_URL before any app imports so the engine picks it up.
# ---------------------------------------------------------------------------
_E2E_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:123456@localhost:5432/ai_test_e2e",
)

# Derive the sync URL for CREATE/DROP DATABASE (asyncpg cannot run these).
_E2E_DB_URL_SYNC = _E2E_DB_URL.replace("+asyncpg", "")

# Parse connection parts for raw asyncpg admin connection.
import re as _re
_m = _re.match(r"postgresql(?:\+\w+)?://([^:]+):([^@]+)@([^/:]+)(?::(\d+))?/(.+)", _E2E_DB_URL)
if _m:
    _PG_USER, _PG_PASS, _PG_HOST, _PG_PORT, _PG_DB = (
        _m.group(1), _m.group(2), _m.group(3), _m.group(4) or "5432", _m.group(5)
    )
else:
    raise RuntimeError(f"Cannot parse TEST_DATABASE_URL: {_E2E_DB_URL}")


def _sync_admin_url() -> str:
    return f"postgresql://{_PG_USER}:{_PG_PASS}@{_PG_HOST}:{_PG_PORT}/postgres"


# ---------------------------------------------------------------------------
# Session-scoped: create / drop the test database once per pytest session.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def _ensure_test_db():
    """Create the E2E test database if it does not exist, drop it after."""
    loop = asyncio.new_event_loop()

    async def _create():
        conn = await asyncpg.connect(
            host=_PG_HOST, port=int(_PG_PORT), user=_PG_USER, password=_PG_PASS, database="postgres"
        )
        try:
            exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", _PG_DB)
            if not exists:
                await conn.execute(f'CREATE DATABASE "{_PG_DB}"')
        finally:
            await conn.close()

    async def _drop():
        conn = await asyncpg.connect(
            host=_PG_HOST, port=int(_PG_PORT), user=_PG_USER, password=_PG_PASS, database="postgres"
        )
        try:
            # Terminate existing connections.
            await conn.execute(
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = $1 AND pid <> pg_backend_pid()", _PG_DB
            )
            await conn.execute(f'DROP DATABASE IF EXISTS "{_PG_DB}"')
        finally:
            await conn.close()

    loop.run_until_complete(_create())

    # Set the env var so the app reads it.
    os.environ["DATABASE_URL"] = _E2E_DB_URL

    # Run alembic migrations.
    alembic_ini = str(
        __import__("pathlib").Path(__file__).resolve().parents[2] / "alembic.ini"
    )
    cfg = AlembicConfig(alembic_ini)
    cfg.set_main_option("sqlalchemy.url", _E2E_DB_URL_SYNC)
    alembic_command.upgrade(cfg, "head")

    yield _E2E_DB_URL

    loop.run_until_complete(_drop())
    loop.close()


# ---------------------------------------------------------------------------
# Function-scoped: fresh async session per test.
# ---------------------------------------------------------------------------
@pytest.fixture()
def _engine(_ensure_test_db):
    """Create a fresh engine per session (reuses the same DB)."""
    from app.core.database import get_engine, get_sessionmaker

    # Clear lru_cache so engine picks up the overridden DATABASE_URL.
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()

    engine = get_engine()
    yield engine


@pytest.fixture()
async def db_session(_engine) -> AsyncGenerator[AsyncSession, None]:
    """Yield a session wrapped in a rollback — tests never persist."""
    from app.core.database import get_sessionmaker

    sm = get_sessionmaker()
    async with sm() as session:
        yield session
        await session.rollback()


@pytest.fixture()
async def client(_ensure_test_db) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client pointing at the real app with real DB."""
    from app.main import create_app

    # Clear settings cache so it picks up the new DATABASE_URL.
    from app.core.config import get_settings
    get_settings.cache_clear()

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Auth helpers.
# ---------------------------------------------------------------------------
@pytest.fixture()
async def auth_token(client: AsyncClient) -> str:
    """Register a user and return a valid access token."""
    phone = f"138{uuid.uuid4().hex[:8]}"
    username = f"e2e_{uuid.uuid4().hex[:8]}"
    password = "Test123456"

    # Register.
    resp = await client.post("/api/auth/register", json={
        "phone": phone,
        "username": username,
        "password": password,
        "confirmPassword": password,
        "captcha": "123456",
    })
    assert resp.status_code == 200, f"Register failed: {resp.text}"
    body = resp.json()
    assert body.get("code") == 0, f"Register error: {body}"

    # Login.
    resp = await client.post("/api/auth/login", json={
        "username": username,
        "password": password,
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    body = resp.json()
    assert body.get("code") == 0, f"Login error: {body}"
    return body["data"]["accessToken"]


@pytest.fixture()
def auth_headers(auth_token: str) -> dict[str, str]:
    """Authorization header with a valid token."""
    return {"Authorization": f"Bearer {auth_token}"}
