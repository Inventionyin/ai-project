from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
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


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(requirements_endpoint.router, prefix="/api")

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


def test_list_requirement_case_links_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    analysis_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async def _fake_list_links(db, *, user, project_id, analysis_id):
        return [
            {
                "id": "99999999-9999-9999-9999-999999999999",
                "projectId": str(project_id),
                "docId": "77777777-7777-7777-7777-777777777777",
                "docVersionId": "88888888-8888-8888-8888-888888888888",
                "analysisId": str(analysis_id),
                "testPointId": None,
                "caseDraftId": "66666666-6666-6666-6666-666666666666",
                "testcaseId": "55555555-5555-5555-5555-555555555555",
                "testcaseTitle": "验证登录成功",
                "linkType": "GENERATED_FROM",
                "confidence": 0.92,
                "createdBy": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "createdAt": 1710000000,
            }
        ]

    monkeypatch.setattr(requirements_endpoint, "list_requirement_case_links", _fake_list_links)
    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{project_id}/requirements/analyses/{analysis_id}/case-links")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["analysisId"] == str(analysis_id)
    assert data[0]["testcaseTitle"] == "验证登录成功"
