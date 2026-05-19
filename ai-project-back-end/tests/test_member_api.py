from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import members as members_endpoint
from app.core.database import get_db
from app.models.project import Project


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


_USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(members_endpoint.router, prefix="/api/projects/{projectId}/members")

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
    """Return a dummy project that passes access checks."""
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


def test_list_members_empty(monkeypatch) -> None:
    async def _fake_list_members(db, *, user, project_id, page, page_size):
        return (0, [])

    monkeypatch.setattr(members_endpoint, "get_project", _fake_get_project)
    monkeypatch.setattr(members_endpoint, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(members_endpoint, "list_members", _fake_list_members)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/members")
    assert resp.status_code == 200
    body = resp.json()
    assert body["requestId"]
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0


def test_list_members_with_data(monkeypatch) -> None:
    async def _fake_list_members(db, *, user, project_id, page, page_size):
        return (
            1,
            [
                {
                    "id": str(_MEMBER_ID),
                    "userId": str(_USER_ID),
                    "userName": "Test User",
                    "userEmail": "test@example.com",
                    "role": "ADMIN",
                    "createdAt": 1710000000,
                }
            ],
        )

    monkeypatch.setattr(members_endpoint, "get_project", _fake_get_project)
    monkeypatch.setattr(members_endpoint, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(members_endpoint, "list_members", _fake_list_members)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/members")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["role"] == "ADMIN"


@dataclass
class _FakePM:
    id: uuid.UUID
    user_id: uuid.UUID
    role: object
    created_at: datetime


def test_add_member(monkeypatch) -> None:
    class _Role:
        value = "EDITOR"

    async def _fake_add_member(db, *, user, project_id, user_id, role):
        return _FakePM(
            id=_MEMBER_ID,
            user_id=user_id,
            role=_Role(),
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

    monkeypatch.setattr(members_endpoint, "get_project", _fake_get_project)
    monkeypatch.setattr(members_endpoint, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(members_endpoint, "add_member", _fake_add_member)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/members",
        json={"userId": str(_USER_ID), "role": "EDITOR"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["role"] == "EDITOR"


def test_add_member_duplicate(monkeypatch) -> None:
    async def _fake_add_member(db, *, user, project_id, user_id, role):
        raise ValueError("User is already a member of this project")

    monkeypatch.setattr(members_endpoint, "get_project", _fake_get_project)
    monkeypatch.setattr(members_endpoint, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(members_endpoint, "add_member", _fake_add_member)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/members",
        json={"userId": str(_USER_ID), "role": "EDITOR"},
    )
    assert resp.status_code == 400
    assert "already a member" in resp.json()["detail"]


def test_update_member_role(monkeypatch) -> None:
    class _Role:
        value = "ADMIN"

    async def _fake_update_member_role(db, *, member_id, tenant_id, role):
        return _FakePM(
            id=member_id,
            user_id=_USER_ID,
            role=_Role(),
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

    monkeypatch.setattr(members_endpoint, "get_project", _fake_get_project)
    monkeypatch.setattr(members_endpoint, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(members_endpoint, "update_member_role", _fake_update_member_role)

    client = TestClient(_build_app())
    resp = client.put(
        f"/api/projects/{_PROJECT_ID}/members/{_MEMBER_ID}",
        json={"role": "ADMIN"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["role"] == "ADMIN"


def test_update_member_not_found(monkeypatch) -> None:
    async def _fake_update_member_role(db, *, member_id, tenant_id, role):
        raise ValueError("Member not found")

    monkeypatch.setattr(members_endpoint, "get_project", _fake_get_project)
    monkeypatch.setattr(members_endpoint, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(members_endpoint, "update_member_role", _fake_update_member_role)

    client = TestClient(_build_app())
    resp = client.put(
        f"/api/projects/{_PROJECT_ID}/members/{_MEMBER_ID}",
        json={"role": "ADMIN"},
    )
    assert resp.status_code == 400
    assert "Member not found" in resp.json()["detail"]


def test_remove_member(monkeypatch) -> None:
    async def _fake_remove_member(db, *, member_id, tenant_id):
        return None

    monkeypatch.setattr(members_endpoint, "get_project", _fake_get_project)
    monkeypatch.setattr(members_endpoint, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(members_endpoint, "remove_member", _fake_remove_member)

    client = TestClient(_build_app())
    resp = client.delete(f"/api/projects/{_PROJECT_ID}/members/{_MEMBER_ID}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["ok"] is True


def test_remove_member_not_found(monkeypatch) -> None:
    async def _fake_remove_member(db, *, member_id, tenant_id):
        raise ValueError("Member not found")

    monkeypatch.setattr(members_endpoint, "get_project", _fake_get_project)
    monkeypatch.setattr(members_endpoint, "_require_project_write", _fake_require_project_write)
    monkeypatch.setattr(members_endpoint, "remove_member", _fake_remove_member)

    client = TestClient(_build_app())
    resp = client.delete(f"/api/projects/{_PROJECT_ID}/members/{_MEMBER_ID}")
    assert resp.status_code == 400
    assert "Member not found" in resp.json()["detail"]
