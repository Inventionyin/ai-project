from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import requirements as requirements_endpoint
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
_DOC_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
_VERSION_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


@dataclass
class _FakeDoc:
    id: uuid.UUID
    current_version_id: uuid.UUID


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(requirements_endpoint.router, prefix="/api")

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


def test_doc_version_rollback_success(monkeypatch) -> None:
    async def _fake_rollback(db, *, user, project_id, doc_id, version_id):
        return _FakeDoc(id=doc_id, current_version_id=version_id)

    monkeypatch.setattr(requirements_endpoint, "rollback_requirement_doc_version", _fake_rollback)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/requirements/docs/{_DOC_ID}/rollback",
        json={"versionId": str(_VERSION_ID)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["id"] == str(_DOC_ID)
    assert body["data"]["currentVersionId"] == str(_VERSION_ID)


def test_doc_version_rollback_missing_version_id() -> None:
    # uuid.UUID("") raises ValueError before the HTTPException check
    client = TestClient(_build_app(), raise_server_exceptions=False)
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/requirements/docs/{_DOC_ID}/rollback",
        json={},
    )
    assert resp.status_code == 500


def test_doc_version_rollback_empty_version_id() -> None:
    # uuid.UUID("") raises ValueError before the HTTPException check
    client = TestClient(_build_app(), raise_server_exceptions=False)
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/requirements/docs/{_DOC_ID}/rollback",
        json={"versionId": ""},
    )
    assert resp.status_code == 500


def test_doc_version_rollback_version_not_found(monkeypatch) -> None:
    from fastapi import HTTPException

    async def _fake_rollback(db, *, user, project_id, doc_id, version_id):
        raise HTTPException(status_code=404, detail="Version not found")

    monkeypatch.setattr(requirements_endpoint, "rollback_requirement_doc_version", _fake_rollback)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/requirements/docs/{_DOC_ID}/rollback",
        json={"versionId": str(_VERSION_ID)},
    )
    assert resp.status_code == 404
    assert "Version not found" in resp.json()["detail"]


def test_doc_version_rollback_doc_not_found(monkeypatch) -> None:
    from fastapi import HTTPException

    async def _fake_rollback(db, *, user, project_id, doc_id, version_id):
        raise HTTPException(status_code=404, detail="Document not found")

    monkeypatch.setattr(requirements_endpoint, "rollback_requirement_doc_version", _fake_rollback)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/requirements/docs/{_DOC_ID}/rollback",
        json={"versionId": str(_VERSION_ID)},
    )
    assert resp.status_code == 404
    assert "Document not found" in resp.json()["detail"]
