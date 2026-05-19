from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import organizations as organizations_endpoint
from app.core.database import get_db


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


_USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_ORG_ID = uuid.UUID("77777777-7777-7777-7777-777777777777")


@dataclass
class _FakeOrg:
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str
    settings_json: dict
    created_at: datetime = datetime(2024, 1, 1, tzinfo=timezone.utc)
    updated_at: datetime = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(organizations_endpoint.router, prefix="/api")

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


def test_create_organization(monkeypatch) -> None:
    async def _fake_create(db, *, user, name, description=None, settings=None):
        return _FakeOrg(
            id=_ORG_ID,
            tenant_id=user.tenant_id,
            name=name,
            description=description or "",
            settings_json=settings or {},
        )

    async def _fake_get(db, *, user, org_id):
        return (
            _FakeOrg(
                id=org_id,
                tenant_id=user.tenant_id,
                name="Test Org",
                description="Test",
                settings_json={},
            ),
            0,
        )

    monkeypatch.setattr(organizations_endpoint, "create_organization", _fake_create)
    monkeypatch.setattr(organizations_endpoint, "get_organization", _fake_get)

    client = TestClient(_build_app())
    resp = client.post(
        "/api/organizations",
        json={"name": "Test Org", "description": "Test"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Test Org"
    assert body["data"]["description"] == "Test"


def test_list_organizations_empty(monkeypatch) -> None:
    async def _fake_list(db, *, user, page, page_size, keyword=None):
        return (0, [])

    monkeypatch.setattr(organizations_endpoint, "list_organizations", _fake_list)

    client = TestClient(_build_app())
    resp = client.get("/api/organizations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0


def test_list_organizations_with_data(monkeypatch) -> None:
    async def _fake_list(db, *, user, page, page_size, keyword=None):
        org = _FakeOrg(
            id=_ORG_ID,
            tenant_id=_TENANT_ID,
            name="Test Org",
            description="Desc",
            settings_json={},
        )
        return (1, [(org, 3)])

    monkeypatch.setattr(organizations_endpoint, "list_organizations", _fake_list)

    client = TestClient(_build_app())
    resp = client.get("/api/organizations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["name"] == "Test Org"
    assert body["data"]["items"][0]["projectCount"] == 3


def test_get_organization(monkeypatch) -> None:
    async def _fake_get(db, *, user, org_id):
        return (
            _FakeOrg(
                id=org_id,
                tenant_id=user.tenant_id,
                name="Test Org",
                description="Desc",
                settings_json={"key": "val"},
            ),
            2,
        )

    monkeypatch.setattr(organizations_endpoint, "get_organization", _fake_get)

    client = TestClient(_build_app())
    resp = client.get(f"/api/organizations/{_ORG_ID}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Test Org"
    assert body["data"]["settings"] == {"key": "val"}
    assert body["data"]["projectCount"] == 2


def test_update_organization(monkeypatch) -> None:
    async def _fake_update(db, *, user, org_id, name=None, description=None, settings=None):
        return (
            _FakeOrg(
                id=org_id,
                tenant_id=user.tenant_id,
                name=name or "Updated",
                description=description or "",
                settings_json=settings or {},
            ),
            1,
        )

    monkeypatch.setattr(organizations_endpoint, "update_organization", _fake_update)

    client = TestClient(_build_app())
    resp = client.put(
        f"/api/organizations/{_ORG_ID}",
        json={"name": "Updated"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Updated"


def test_delete_organization(monkeypatch) -> None:
    async def _fake_delete(db, *, user, org_id):
        return None

    monkeypatch.setattr(organizations_endpoint, "delete_organization", _fake_delete)

    client = TestClient(_build_app())
    resp = client.delete(f"/api/organizations/{_ORG_ID}")
    assert resp.status_code == 200
