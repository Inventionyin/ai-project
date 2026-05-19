from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import defect_providers as defect_providers_endpoint
from app.core.database import get_db


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


_USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_CONFIG_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")


@dataclass
class _FakeConfig:
    id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    provider: str
    name: str
    base_url: str
    enabled: bool = True
    sync_status: str = "IDLE"
    last_sync_at: object = None
    last_error: str | None = None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(
        defect_providers_endpoint.router,
        prefix="/api/projects/{projectId}/defect-providers",
    )

    async def _override_db():
        yield _DummySession()

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=_USER_ID,
            tenant_id=_TENANT_ID,
            roles=frozenset({"ADMIN"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


async def _fake_get_project(db, *, user, project_id):
    from app.models.project import Project

    return (
        Project(
            id=_PROJECT_ID,
            tenant_id=_TENANT_ID,
            name="Test Project",
            owner_id=_USER_ID,
        ),
        0,
    )


async def _fake_require_project_write(db, *, user, project) -> None:
    return None


def _url(suffix: str = "") -> str:
    base = f"/api/projects/{_PROJECT_ID}/defect-providers"
    return f"{base}/{suffix}".rstrip("/") if suffix else base


def test_list_defect_providers_empty(monkeypatch) -> None:
    async def _fake_list(db, *, user, project_id):
        return []

    monkeypatch.setattr(defect_providers_endpoint, "get_project", _fake_get_project)
    monkeypatch.setattr(defect_providers_endpoint, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(defect_providers_endpoint, "list_defect_providers", _fake_list)

    client = TestClient(_build_app())
    resp = client.get(_url())
    assert resp.status_code == 200
    body = resp.json()
    assert body["requestId"]
    assert body["data"] == []


def test_list_defect_providers_with_data(monkeypatch) -> None:
    async def _fake_list(db, *, user, project_id):
        return [
            _FakeConfig(
                id=_CONFIG_ID,
                project_id=_PROJECT_ID,
                tenant_id=_TENANT_ID,
                provider="JIRA",
                name="Test Jira",
                base_url="https://jira.example.com",
            )
        ]

    monkeypatch.setattr(defect_providers_endpoint, "get_project", _fake_get_project)
    monkeypatch.setattr(defect_providers_endpoint, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(defect_providers_endpoint, "list_defect_providers", _fake_list)

    client = TestClient(_build_app())
    resp = client.get(_url())
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["provider"] == "JIRA"
    assert body["data"][0]["name"] == "Test Jira"


def test_create_defect_provider(monkeypatch) -> None:
    async def _fake_create(db, *, user, project_id, provider, name, base_url, auth_json, config_json):
        return _FakeConfig(
            id=_CONFIG_ID,
            project_id=project_id,
            tenant_id=user.tenant_id,
            provider=provider,
            name=name,
            base_url=base_url,
        )

    monkeypatch.setattr(defect_providers_endpoint, "get_project", _fake_get_project)
    monkeypatch.setattr(defect_providers_endpoint, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(defect_providers_endpoint, "create_defect_provider", _fake_create)

    client = TestClient(_build_app())
    resp = client.post(
        _url(),
        json={
            "provider": "JIRA",
            "name": "Test Jira",
            "baseUrl": "https://jira.example.com",
            "apiToken": "tok123",
            "username": "user",
            "projectKey": "TEST",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["provider"] == "JIRA"
    assert body["data"]["name"] == "Test Jira"
    assert body["data"]["baseUrl"] == "https://jira.example.com"


def test_create_defect_provider_minimal_fields(monkeypatch) -> None:
    async def _fake_create(db, *, user, project_id, provider, name, base_url, auth_json, config_json):
        return _FakeConfig(
            id=_CONFIG_ID,
            project_id=project_id,
            tenant_id=user.tenant_id,
            provider=provider,
            name=name,
            base_url=base_url,
        )

    monkeypatch.setattr(defect_providers_endpoint, "get_project", _fake_get_project)
    monkeypatch.setattr(defect_providers_endpoint, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(defect_providers_endpoint, "create_defect_provider", _fake_create)

    client = TestClient(_build_app())
    resp = client.post(
        _url(),
        json={
            "provider": "GITEA",
            "name": "My Gitea",
            "baseUrl": "https://gitea.example.com",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["provider"] == "GITEA"


def test_delete_defect_provider(monkeypatch) -> None:
    async def _fake_delete(db, *, config_id, tenant_id):
        return None

    monkeypatch.setattr(defect_providers_endpoint, "get_project", _fake_get_project)
    monkeypatch.setattr(defect_providers_endpoint, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(defect_providers_endpoint, "delete_defect_provider", _fake_delete)

    client = TestClient(_build_app())
    resp = client.delete(_url(str(_CONFIG_ID)))
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["ok"] is True


def test_delete_defect_provider_not_found(monkeypatch) -> None:
    async def _fake_delete(db, *, config_id, tenant_id):
        raise ValueError("Not found")

    monkeypatch.setattr(defect_providers_endpoint, "get_project", _fake_get_project)
    monkeypatch.setattr(defect_providers_endpoint, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(defect_providers_endpoint, "delete_defect_provider", _fake_delete)

    client = TestClient(_build_app(), raise_server_exceptions=False)
    resp = client.delete(_url(str(_CONFIG_ID)))
    assert resp.status_code == 404
