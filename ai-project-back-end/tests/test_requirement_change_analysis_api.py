from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import requirement_changes as requirement_changes_endpoint
from app.core.database import get_db
from app.schemas.requirement_change import (
    RequirementChangeSetDetail,
    RequirementRegressionSetDetail,
)


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(requirement_changes_endpoint.router, prefix="/api")

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


def _change_set(project_id: uuid.UUID, doc_id: uuid.UUID, change_set_id: uuid.UUID) -> RequirementChangeSetDetail:
    return RequirementChangeSetDetail(
        id=str(change_set_id),
        projectId=str(project_id),
        docId=str(doc_id),
        baselineVersionId="44444444-4444-4444-4444-444444444444",
        targetVersionId="55555555-5555-5555-5555-555555555555",
        summary="检测到新增登录限制规则",
        status="GENERATED",
        items=[],
        createdBy="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        createdAt=1710000000,
        updatedAt=1710000001,
    )


def _regression_set(project_id: uuid.UUID, regression_set_id: uuid.UUID, change_set_id: uuid.UUID) -> RequirementRegressionSetDetail:
    return RequirementRegressionSetDetail(
        id=str(regression_set_id),
        projectId=str(project_id),
        changeSetId=str(change_set_id),
        summary="共需回归 2 条用例",
        status="GENERATED",
        cases=[],
        createdBy="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        createdAt=1710000300,
        updatedAt=1710000301,
    )


def test_change_set_and_regression_set_endpoints(monkeypatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    doc_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    change_set_id = uuid.UUID("66666666-6666-6666-6666-666666666666")
    regression_set_id = uuid.UUID("77777777-7777-7777-7777-777777777777")

    async def _fake_create_change_set(db, *, user, project_id, doc_id, payload):
        return _change_set(project_id, doc_id, change_set_id)

    async def _fake_list_change_sets(db, *, user, project_id, doc_id):
        return [_change_set(project_id, doc_id, change_set_id)]

    async def _fake_get_change_set(db, *, user, project_id, change_set_id):
        return _change_set(project_id, doc_id, change_set_id)

    async def _fake_create_regression_set(db, *, user, project_id, change_set_id):
        return _regression_set(project_id, regression_set_id, change_set_id)

    async def _fake_get_regression_set(db, *, user, project_id, regression_set_id):
        return _regression_set(project_id, regression_set_id, change_set_id)

    monkeypatch.setattr(requirement_changes_endpoint, "create_requirement_change_set", _fake_create_change_set)
    monkeypatch.setattr(requirement_changes_endpoint, "list_requirement_change_sets", _fake_list_change_sets)
    monkeypatch.setattr(requirement_changes_endpoint, "get_requirement_change_set", _fake_get_change_set)
    monkeypatch.setattr(requirement_changes_endpoint, "create_requirement_regression_set", _fake_create_regression_set)
    monkeypatch.setattr(requirement_changes_endpoint, "get_requirement_regression_set", _fake_get_regression_set)

    client = TestClient(_build_app())

    create_resp = client.post(
        f"/api/projects/{project_id}/requirements/docs/{doc_id}/change-sets",
        json={"baselineVersionId": "44444444-4444-4444-4444-444444444444", "targetVersionId": "55555555-5555-5555-5555-555555555555"},
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["data"]["id"] == str(change_set_id)

    list_resp = client.get(f"/api/projects/{project_id}/requirements/docs/{doc_id}/change-sets")
    assert list_resp.status_code == 200
    assert list_resp.json()["data"][0]["summary"] == "检测到新增登录限制规则"

    get_resp = client.get(f"/api/projects/{project_id}/requirements/change-sets/{change_set_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["docId"] == str(doc_id)

    create_reg_resp = client.post(f"/api/projects/{project_id}/requirements/change-sets/{change_set_id}/regression-set")
    assert create_reg_resp.status_code == 200
    assert create_reg_resp.json()["data"]["id"] == str(regression_set_id)

    get_reg_resp = client.get(f"/api/projects/{project_id}/requirements/regression-sets/{regression_set_id}")
    assert get_reg_resp.status_code == 200
    assert get_reg_resp.json()["data"]["changeSetId"] == str(change_set_id)
