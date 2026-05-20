from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import security_policy as security_endpoint
from app.core.database import get_db
from app.services.security_policy import mask_sensitive_fields, mask_sensitive_text


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(security_endpoint.router, prefix="/api")

    async def _override_db():
        yield _DummySession()

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            roles=frozenset({"ADMIN"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def test_mask_sensitive_fields() -> None:
    data = {
        "name": "test",
        "password": "secret123",
        "api_key": "ak-123456",
        "nested": {"token": "tok-xyz", "safe": "value"},
    }
    masked = mask_sensitive_fields(data)
    assert masked["name"] == "test"
    assert masked["password"] == "***REDACTED***"
    assert masked["api_key"] == "***REDACTED***"
    assert masked["nested"]["token"] == "***REDACTED***"
    assert masked["nested"]["safe"] == "value"


def test_mask_sensitive_text() -> None:
    text = "Connecting with password=abc123 and token=xyz"
    masked = mask_sensitive_text(text)
    assert "password" not in masked
    assert "token" not in masked
    assert "***REDACTED***" in masked


def test_list_audit_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async def _fake_list(db, *, user, project_id, page=1, page_size=20, module=None, action=None):
        return 0, []

    monkeypatch.setattr(security_endpoint, "list_audit_logs", _fake_list)
    app = _build_app()
    client = TestClient(app)
    resp = client.get(f"/api/projects/{project_id}/security/audit-logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 0
