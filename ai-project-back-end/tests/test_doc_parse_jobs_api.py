from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import doc_parse_jobs as doc_parse_jobs_endpoint
from app.core.database import get_db


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(doc_parse_jobs_endpoint.router, prefix="/api")

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


def test_create_doc_parse_job(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    doc_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    version_id = uuid.UUID("55555555-5555-5555-5555-555555555555")

    async def _fake_create(db, *, user, project_id, doc_id, doc_version_id):
        from app.schemas.doc_parse_job import DocParseJobDetail
        return DocParseJobDetail(
            id="66666666-6666-6666-6666-666666666666",
            projectId=str(project_id),
            docId=str(doc_id),
            docVersionId=str(doc_version_id),
            status="PENDING",
            attempts=0,
            maxRetries=3,
            createdAt=1700000000,
            updatedAt=1700000000,
        )

    monkeypatch.setattr(doc_parse_jobs_endpoint, "create_doc_parse_job", _fake_create)
    app = _build_app()
    client = TestClient(app)
    resp = client.post(
        f"/api/projects/{project_id}/doc-parse-jobs",
        json={"docId": str(doc_id), "docVersionId": str(version_id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "PENDING"


def test_list_doc_parse_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async def _fake_list(db, *, user, project_id, page, page_size, status=None):
        from app.schemas.doc_parse_job import DocParseJobDetail
        return 0, []

    monkeypatch.setattr(doc_parse_jobs_endpoint, "list_doc_parse_jobs", _fake_list)
    app = _build_app()
    client = TestClient(app)
    resp = client.get(f"/api/projects/{project_id}/doc-parse-jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 0


def test_retry_doc_parse_job(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    job_id = uuid.UUID("66666666-6666-6666-6666-666666666666")

    async def _fake_retry(db, *, user, project_id, job_id):
        from app.schemas.doc_parse_job import DocParseJobDetail
        return DocParseJobDetail(
            id=str(job_id),
            projectId=str(project_id),
            docId="44444444-4444-4444-4444-444444444444",
            docVersionId="55555555-5555-5555-5555-555555555555",
            status="PENDING",
            attempts=0,
            maxRetries=3,
            createdAt=1700000000,
            updatedAt=1700000000,
        )

    monkeypatch.setattr(doc_parse_jobs_endpoint, "retry_doc_parse_job", _fake_retry)
    app = _build_app()
    client = TestClient(app)
    resp = client.post(f"/api/projects/{project_id}/doc-parse-jobs/{job_id}/retry")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "PENDING"
