from __future__ import annotations

import io
import uuid
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import requirements as requirements_endpoint
from app.core.database import get_db
from app.schemas.requirement import RequirementDocDetail, RequirementDocVersionDetail, normalize_doc_source_type, normalize_doc_status


def test_requirement_doc_normalizers_accept_frontend_aliases() -> None:
    assert normalize_doc_status("active") == "PUBLISHED"
    assert normalize_doc_status("deprecated") == "ARCHIVED"
    assert normalize_doc_status("reviewing") == "REVIEWING"
    assert normalize_doc_status("unknown") == "DRAFT"
    assert normalize_doc_source_type("prd") == "PRD"
    assert normalize_doc_source_type("prototype") == "PROTOTYPE"
    assert normalize_doc_source_type("md") == "MARKDOWN"
    assert normalize_doc_source_type("weird") == "OTHER"


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(requirements_endpoint.router, prefix="/api")

    async def _override_db():
        yield _DummySession()

    async def _override_user() -> CurrentUser:
        return CurrentUser(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            roles=frozenset({"ADMIN"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def test_list_docs(monkeypatch) -> None:
    async def _fake_list(db, *, user, project_id, page, page_size, status, q):
        assert str(project_id) == "22222222-2222-2222-2222-222222222222"
        assert page == 2
        assert page_size == 5
        assert status == "DRAFT"
        assert q == "login"
        return (
            1,
            [
                RequirementDocDetail(
                    id="33333333-3333-3333-3333-333333333333",
                    projectId=str(project_id),
                    title="Login PRD",
                    sourceType="DOCX",
                    ownerId=None,
                    status="DRAFT",
                    tags=["auth"],
                    createdBy=str(user.id),
                    createdAt=1710000000,
                    updatedAt=1710000100,
                )
            ],
        )

    monkeypatch.setattr(requirements_endpoint, "list_requirement_docs", _fake_list)
    client = TestClient(_build_app())
    resp = client.get("/api/projects/22222222-2222-2222-2222-222222222222/requirements/docs?page=2&pageSize=5&status=DRAFT&q=login")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["title"] == "Login PRD"


def test_create_get_update_delete_doc(monkeypatch) -> None:
    doc_id = "44444444-4444-4444-4444-444444444444"

    async def _fake_create(db, *, user, project_id, payload):
        return RequirementDocDetail(
            id=doc_id,
            projectId=str(project_id),
            title=payload.title,
            sourceType=payload.sourceType,
            ownerId=payload.ownerId,
            status=payload.status,
            tags=payload.tags,
            createdBy=str(user.id),
            createdAt=1710000000,
            updatedAt=1710000001,
        )

    async def _fake_get(db, *, user, project_id, doc_id):
        return RequirementDocDetail(
            id=str(doc_id),
            projectId=str(project_id),
            title="A",
            sourceType="PDF",
            ownerId=None,
            status="PUBLISHED",
            tags=[],
            createdBy=str(user.id),
            createdAt=1710000000,
            updatedAt=1710000001,
        )

    async def _fake_update(db, *, user, project_id, doc_id, payload):
        return RequirementDocDetail(
            id=str(doc_id),
            projectId=str(project_id),
            title=payload.title or "A",
            sourceType=payload.sourceType or "PDF",
            ownerId=payload.ownerId,
            status=payload.status or "DRAFT",
            tags=payload.tags if payload.tags is not None else [],
            createdBy=str(user.id),
            createdAt=1710000000,
            updatedAt=1710000200,
        )

    async def _fake_delete(db, *, user, project_id, doc_id):
        return None

    monkeypatch.setattr(requirements_endpoint, "create_requirement_doc", _fake_create)
    monkeypatch.setattr(requirements_endpoint, "get_requirement_doc", _fake_get)
    monkeypatch.setattr(requirements_endpoint, "update_requirement_doc", _fake_update)
    monkeypatch.setattr(requirements_endpoint, "delete_requirement_doc", _fake_delete)
    client = TestClient(_build_app())

    create_resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/requirements/docs",
        json={"title": "PRD", "sourceType": "DOCX", "status": "DRAFT", "tags": ["x"]},
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["data"]["id"] == doc_id

    get_resp = client.get(f"/api/projects/22222222-2222-2222-2222-222222222222/requirements/docs/{doc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["status"] == "PUBLISHED"

    update_resp = client.put(
        f"/api/projects/22222222-2222-2222-2222-222222222222/requirements/docs/{doc_id}",
        json={"title": "PRD v2", "status": "REVIEW"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["title"] == "PRD v2"

    delete_resp = client.delete(f"/api/projects/22222222-2222-2222-2222-222222222222/requirements/docs/{doc_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["data"] == {}


def test_versions_endpoints(monkeypatch) -> None:
    version_id = "55555555-5555-5555-5555-555555555555"

    async def _fake_list_versions(db, *, user, project_id, doc_id):
        return [
            RequirementDocVersionDetail(
                id=version_id,
                docId=str(doc_id),
                projectId=str(project_id),
                version=1,
                fileName="a.docx",
                fileType="DOCX",
                storageUrl="/var/a.docx",
                contentHash="abc",
                parsedTextUrl=None,
                parsedTextPreview=None,
                changeSummary=None,
                effectiveScope=None,
                publishedAt=None,
                createdBy=str(user.id),
                createdAt=1710000000,
                updatedAt=1710000001,
            )
        ]

    async def _fake_create_version(db, *, user, project_id, doc_id, upload_file, change_summary, effective_scope):
        assert upload_file.filename == "a.docx"
        assert change_summary == "delta"
        assert effective_scope == "core"
        return RequirementDocVersionDetail(
            id=version_id,
            docId=str(doc_id),
            projectId=str(project_id),
            version=2,
            fileName=upload_file.filename,
            fileType="DOCX",
            storageUrl="/var/a.docx",
            contentHash="abc",
            parsedTextUrl=None,
            parsedTextPreview=None,
            changeSummary=change_summary,
            effectiveScope=effective_scope,
            publishedAt=None,
            createdBy=str(user.id),
            createdAt=1710000000,
            updatedAt=1710000001,
        )

    async def _fake_parse(db, *, user, project_id, doc_id, version_id):
        return {"status": "ok"}

    async def _fake_get_parsed_text(db, *, user, project_id, doc_id, version_id):
        return {"text": "hello"}

    monkeypatch.setattr(requirements_endpoint, "list_requirement_doc_versions", _fake_list_versions)
    monkeypatch.setattr(requirements_endpoint, "create_requirement_doc_version", _fake_create_version)
    monkeypatch.setattr(requirements_endpoint, "parse_requirement_doc_version", _fake_parse)
    monkeypatch.setattr(requirements_endpoint, "get_requirement_doc_version_parsed_text", _fake_get_parsed_text)
    client = TestClient(_build_app())

    list_resp = client.get(
        "/api/projects/22222222-2222-2222-2222-222222222222/requirements/docs/44444444-4444-4444-4444-444444444444/versions"
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["data"][0]["id"] == version_id

    create_resp = client.post(
        "/api/projects/22222222-2222-2222-2222-222222222222/requirements/docs/44444444-4444-4444-4444-444444444444/versions",
        files={"file": ("a.docx", io.BytesIO(b"abc"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"changeSummary": "delta", "effectiveScope": "core"},
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["data"]["version"] == 2

    parse_resp = client.post(
        f"/api/projects/22222222-2222-2222-2222-222222222222/requirements/docs/44444444-4444-4444-4444-444444444444/versions/{version_id}/parse"
    )
    assert parse_resp.status_code == 200
    assert parse_resp.json()["data"]["status"] == "ok"

    text_resp = client.get(
        f"/api/projects/22222222-2222-2222-2222-222222222222/requirements/docs/44444444-4444-4444-4444-444444444444/versions/{version_id}/parsed-text"
    )
    assert text_resp.status_code == 200
    assert text_resp.json()["data"]["text"] == "hello"
