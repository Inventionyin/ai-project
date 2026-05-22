from __future__ import annotations

import os
import uuid
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.setup_test_db import DEFAULT_TEST_DATABASE_URL, ensure_database, run_migrations
from helpers import assert_success, unique_phone


os.environ.setdefault("DATABASE_URL", os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL))
os.environ.setdefault("ENV", "e2e")
os.environ.setdefault("JWT_SECRET_KEY", "e2e_secret_change_me_please_32chars_min_123456")
os.environ.setdefault("NOTIFICATION_OUTBOX_CONSUMER_ENABLED", "false")


@pytest.fixture(scope="session", autouse=True)
def e2e_database():
    url = os.environ["DATABASE_URL"]
    asyncio.run(ensure_database(url, reset=True))
    cwd = Path.cwd()
    try:
        run_migrations(url)
        yield
    finally:
        os.chdir(cwd)


@pytest.fixture
def client(e2e_database):
    from app.core.config import get_settings
    from app.core.database import get_engine, get_sessionmaker

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as ac:
        yield ac

    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    get_settings.cache_clear()


@pytest.fixture
def auth_context(client: TestClient) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:10]
    username = f"e2e_{suffix}"
    password = "Test123456"
    register_payload = {
        "phone": unique_phone("139"),
        "username": username,
        "password": password,
        "confirmPassword": password,
        "captcha": "123456",
    }
    register_resp = client.post("/api/auth/register", json=register_payload)
    assert register_resp.status_code == 200
    register_data = assert_success(register_resp.json())

    login_resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert login_resp.status_code == 200
    login_data = assert_success(login_resp.json())

    token = login_data["accessToken"]
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = assert_success(me_resp.json())

    return {
        "username": username,
        "password": password,
        "token": token,
        "userId": register_data["userId"],
        "tenantId": me_data["tenantId"],
    }


@pytest.fixture
def auth_headers(auth_context: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_context['token']}"}
