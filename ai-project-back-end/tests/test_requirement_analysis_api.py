from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import requirements as requirements_endpoint
from app.core.database import get_db
from app.schemas.requirement import RequirementAnalysisDetail
from app.schemas.requirement_change import (
    RequirementAnalysisRevisionDetail,
)


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


def _analysis(project_id: uuid.UUID, doc_id: uuid.UUID, version_id: uuid.UUID, analysis_id: str) -> RequirementAnalysisDetail:
    return RequirementAnalysisDetail(
        id=analysis_id,
        projectId=str(project_id),
        docId=str(doc_id),
        docVersionId=str(version_id),
        status="GENERATED",
        summary="登录模块包含账号密码校验、锁定策略和验证码风险。",
        riskLevel="MEDIUM",
        coverageScore=0.76,
        analysis={
            "featurePoints": [{"title": "账号登录", "description": "用户使用账号密码登录"}],
            "businessRules": [{"title": "密码错误锁定", "description": "连续失败后限制登录"}],
            "testPoints": [{"title": "密码错误提示", "scenarioType": "NEGATIVE", "priority": "P1"}],
            "riskPoints": [{"title": "暴力破解", "riskLevel": "HIGH"}],
            "boundaryCases": [{"title": "密码长度边界"}],
            "coverageSuggestions": [{"title": "补充验证码绕过测试"}],
        },
        aiTaskId=None,
        createdBy="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        updatedBy=None,
        createdAt=1710000000,
        updatedAt=1710000100,
    )


def test_generate_requirement_analysis_calls_service(monkeypatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    doc_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    version_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    analysis_id = "55555555-5555-5555-5555-555555555555"

    async def _fake_generate(db, *, user, project_id, doc_id, version_id, instruction):
        assert user.id == uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        assert str(project_id) == "22222222-2222-2222-2222-222222222222"
        assert str(doc_id) == "33333333-3333-3333-3333-333333333333"
        assert str(version_id) == "44444444-4444-4444-4444-444444444444"
        assert instruction == "重点覆盖异常流程"
        return _analysis(project_id, doc_id, version_id, analysis_id)

    monkeypatch.setattr(requirements_endpoint, "generate_requirement_analysis", _fake_generate)
    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{project_id}/requirements/docs/{doc_id}/versions/{version_id}/analyze",
        json={"instruction": "重点覆盖异常流程"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["id"] == analysis_id
    assert body["data"]["analysis"]["testPoints"][0]["title"] == "密码错误提示"


def test_list_and_update_requirement_analyses(monkeypatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    doc_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    version_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    analysis_id = uuid.UUID("55555555-5555-5555-5555-555555555555")

    async def _fake_list(db, *, user, project_id, doc_id, version_id):
        assert str(doc_id) == "33333333-3333-3333-3333-333333333333"
        return [_analysis(project_id, doc_id, version_id, str(analysis_id))]

    async def _fake_get(db, *, user, project_id, analysis_id):
        return _analysis(project_id, doc_id, version_id, str(analysis_id))

    async def _fake_update(db, *, user, project_id, analysis_id, payload):
        data = _analysis(project_id, doc_id, version_id, str(analysis_id))
        data.status = payload.status or data.status
        data.summary = payload.summary or data.summary
        data.analysis = payload.analysis or data.analysis
        return data

    monkeypatch.setattr(requirements_endpoint, "list_requirement_analyses", _fake_list)
    monkeypatch.setattr(requirements_endpoint, "get_requirement_analysis", _fake_get)
    monkeypatch.setattr(requirements_endpoint, "update_requirement_analysis", _fake_update)
    client = TestClient(_build_app())

    list_resp = client.get(f"/api/projects/{project_id}/requirements/analyses?docId={doc_id}&versionId={version_id}")
    assert list_resp.status_code == 200
    assert list_resp.json()["data"][0]["id"] == str(analysis_id)

    get_resp = client.get(f"/api/projects/{project_id}/requirements/analyses/{analysis_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["coverageScore"] == 0.76

    update_resp = client.put(
        f"/api/projects/{project_id}/requirements/analyses/{analysis_id}",
        json={
            "status": "REVIEWED",
            "summary": "人工复核完成",
            "analysis": {"featurePoints": [], "businessRules": [], "testPoints": [], "riskPoints": [], "boundaryCases": [], "coverageSuggestions": []},
        },
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["status"] == "REVIEWED"


def test_list_and_rollback_analysis_revisions(monkeypatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    analysis_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    revision_id = uuid.UUID("66666666-6666-6666-6666-666666666666")
    doc_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    version_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

    async def _fake_list_revisions(db, *, user, project_id, analysis_id):
        return [
            RequirementAnalysisRevisionDetail(
                id=str(revision_id),
                projectId=str(project_id),
                analysisId=str(analysis_id),
                docId=str(doc_id),
                docVersionId=str(version_id),
                revisionNo=2,
                changeReason="manual_update",
                summary="人工修订了风险点",
                riskLevel="HIGH",
                coverageScore=0.8,
                analysis={"featurePoints": [], "businessRules": [], "testPoints": [], "riskPoints": [], "boundaryCases": [], "coverageSuggestions": []},
                createdBy=str(user.id),
                createdAt=1710000200,
            )
        ]

    async def _fake_rollback(db, *, user, project_id, analysis_id, revision_id):
        data = _analysis(project_id, doc_id, version_id, str(analysis_id))
        data.summary = "已回滚到指定修订"
        data.riskLevel = "HIGH"
        return data

    monkeypatch.setattr(requirements_endpoint, "list_requirement_analysis_revisions", _fake_list_revisions)
    monkeypatch.setattr(requirements_endpoint, "rollback_requirement_analysis_revision", _fake_rollback)
    client = TestClient(_build_app())

    list_resp = client.get(f"/api/projects/{project_id}/requirements/analyses/{analysis_id}/revisions")
    assert list_resp.status_code == 200
    assert list_resp.json()["data"][0]["revisionNo"] == 2

    rollback_resp = client.post(
        f"/api/projects/{project_id}/requirements/analyses/{analysis_id}/rollback",
        json={"revisionId": str(revision_id)},
    )
    assert rollback_resp.status_code == 200
    assert rollback_resp.json()["data"]["summary"] == "已回滚到指定修订"
