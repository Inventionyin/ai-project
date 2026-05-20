from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import requirements as requirements_endpoint
from app.core.database import get_db
from app.models.requirement import GeneratedCaseDraft, RequirementAnalysis, RequirementCaseLink
from app.services.requirement import normalize_analysis_test_points_payload
from app.services import requirement as requirement_service


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


def test_normalize_analysis_test_points_payload() -> None:
    payload = {
        "testPoints": [
            {
                "title": "登录成功",
                "description": "正常账号密码登录",
                "scenarioType": "positive",
                "priority": "p1",
                "riskLevel": "high",
                "sourcePath": "analysis.testPoints[0]",
            },
            {"title": "", "description": "missing title"},
        ]
    }
    points = normalize_analysis_test_points_payload(payload)
    assert len(points) == 1
    assert points[0]["title"] == "登录成功"
    assert points[0]["scenarioType"] == "POSITIVE"
    assert points[0]["priority"] == "P1"
    assert points[0]["riskLevel"] == "HIGH"


def test_sync_and_list_test_points(monkeypatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    analysis_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async def _fake_sync(db, *, user, project_id, analysis_id):
        return [
            {
                "id": "44444444-4444-4444-4444-444444444444",
                "projectId": str(project_id),
                "analysisId": str(analysis_id),
                "title": "登录成功",
                "description": "正常登录",
                "scenarioType": "POSITIVE",
                "priority": "P1",
                "riskLevel": "MEDIUM",
                "sourcePath": "analysis.testPoints[0]",
                "status": "DRAFT",
                "aiMeta": {},
                "createdBy": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "updatedBy": None,
                "createdAt": 1710000000,
                "updatedAt": 1710000001,
            }
        ]

    async def _fake_list(db, *, user, project_id, analysis_id):
        return await _fake_sync(db, user=user, project_id=project_id, analysis_id=analysis_id)

    monkeypatch.setattr(requirements_endpoint, "sync_requirement_test_points", _fake_sync)
    monkeypatch.setattr(requirements_endpoint, "list_requirement_test_points", _fake_list)

    client = TestClient(_build_app())
    sync_resp = client.post(f"/api/projects/{project_id}/requirements/analyses/{analysis_id}/sync-test-points")
    assert sync_resp.status_code == 200
    assert sync_resp.json()["data"][0]["title"] == "登录成功"

    list_resp = client.get(f"/api/projects/{project_id}/requirements/analyses/{analysis_id}/test-points")
    assert list_resp.status_code == 200
    assert list_resp.json()["data"][0]["status"] == "DRAFT"


def test_update_test_point(monkeypatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    test_point_id = uuid.UUID("55555555-5555-5555-5555-555555555555")

    async def _fake_update(db, *, user, project_id, test_point_id, payload):
        assert payload.status == "ACCEPTED"
        return {
            "id": str(test_point_id),
            "projectId": str(project_id),
            "analysisId": "33333333-3333-3333-3333-333333333333",
            "title": "登录成功",
            "description": "正常登录",
            "scenarioType": "POSITIVE",
            "priority": "P1",
            "riskLevel": "LOW",
            "sourcePath": "analysis.testPoints[0]",
            "status": "ACCEPTED",
            "aiMeta": {},
            "createdBy": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "updatedBy": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "createdAt": 1710000000,
            "updatedAt": 1710000100,
        }

    monkeypatch.setattr(requirements_endpoint, "update_requirement_test_point", _fake_update)
    client = TestClient(_build_app())
    resp = client.put(
        f"/api/projects/{project_id}/requirements/test-points/{test_point_id}",
        json={"status": "ACCEPTED", "riskLevel": "LOW"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "ACCEPTED"


def test_generate_list_and_bulk_approve_case_drafts(monkeypatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    analysis_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    async def _fake_generate(db, *, user, project_id, analysis_id, payload):
        assert payload.mode == "ACCEPTED_ONLY"
        return [
            {
                "id": "66666666-6666-6666-6666-666666666666",
                "projectId": str(project_id),
                "analysisId": str(analysis_id),
                "testPointId": "44444444-4444-4444-4444-444444444444",
                "title": "验证登录成功",
                "type": "API",
                "priority": "P1",
                "preconditions": "已有有效账号",
                "steps": [{"step": "调用登录接口"}],
                "expectedResults": ["返回200且登录成功"],
                "testData": {"username": "u"},
                "status": "PENDING",
                "confidence": 0.91,
                "aiMeta": {},
                "createdBy": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "reviewedBy": None,
                "createdAt": 1710000000,
                "updatedAt": 1710000001,
            }
        ]

    async def _fake_list_drafts(db, *, user, project_id, analysis_id):
        return await _fake_generate(db, user=user, project_id=project_id, analysis_id=analysis_id, payload=type("P", (), {"mode": "ACCEPTED_ONLY"})())

    async def _fake_bulk_approve(db, *, user, project_id, payload):
        assert len(payload.draftIds) == 1
        return {"approvedDraftCount": 1, "createdTestCaseCount": 1, "testCaseIds": ["77777777-7777-7777-7777-777777777777"]}

    monkeypatch.setattr(requirements_endpoint, "generate_case_drafts_from_analysis", _fake_generate)
    monkeypatch.setattr(requirements_endpoint, "list_generated_case_drafts", _fake_list_drafts)
    monkeypatch.setattr(requirements_endpoint, "bulk_approve_case_drafts", _fake_bulk_approve)

    client = TestClient(_build_app())
    gen_resp = client.post(
        f"/api/projects/{project_id}/requirements/analyses/{analysis_id}/generate-case-drafts",
        json={"mode": "ACCEPTED_ONLY", "forceRegenerate": False},
    )
    assert gen_resp.status_code == 200
    assert gen_resp.json()["data"][0]["status"] == "PENDING"

    list_resp = client.get(f"/api/projects/{project_id}/requirements/analyses/{analysis_id}/case-drafts")
    assert list_resp.status_code == 200
    assert list_resp.json()["data"][0]["title"] == "验证登录成功"

    approve_resp = client.post(
        f"/api/projects/{project_id}/requirements/case-drafts/bulk-approve",
        json={"draftIds": ["66666666-6666-6666-6666-666666666666"]},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["data"]["createdTestCaseCount"] == 1


def test_generated_case_draft_is_not_duplicated_for_same_test_point() -> None:
    test_point_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    existing = {test_point_id}

    assert requirement_service._should_create_case_draft(test_point_id, existing) is False
    assert requirement_service._should_create_case_draft(uuid.UUID("55555555-5555-5555-5555-555555555555"), existing) is True


def test_only_pending_case_drafts_are_committable() -> None:
    assert requirement_service._is_committable_case_draft_status("PENDING") is True
    assert requirement_service._is_committable_case_draft_status("COMMITTED") is False
    assert requirement_service._is_committable_case_draft_status("APPROVED") is False
    assert requirement_service._is_committable_case_draft_status("REJECTED") is False


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)


class _FakeListCaseLinksDb:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, _stmt):
        return _FakeScalarResult(self._rows)


class _FakeBulkApproveDb:
    def __init__(self, drafts, analyses):
        self._responses = [drafts, analyses]
        self.added = []

    async def execute(self, _stmt):
        return _FakeScalarResult(self._responses.pop(0))

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid.uuid4()


@pytest.mark.anyio
async def test_bulk_approve_creates_requirement_case_link(monkeypatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    analysis_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    draft_id = uuid.UUID("66666666-6666-6666-6666-666666666666")
    test_point_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    doc_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
    version_id = uuid.UUID("88888888-8888-8888-8888-888888888888")
    draft = GeneratedCaseDraft(
        id=draft_id,
        tenant_id=tenant_id,
        project_id=project_id,
        analysis_id=analysis_id,
        test_point_id=test_point_id,
        title="验证登录成功",
        type="API",
        priority="P1",
        preconditions=None,
        steps_json=[{"step": "调用登录接口"}],
        expected_results_json=["返回200"],
        test_data_json={},
        status="PENDING",
        confidence=0.9,
        ai_meta_json={},
        created_by=user_id,
        reviewed_by=None,
    )
    analysis = RequirementAnalysis(
        id=analysis_id,
        tenant_id=tenant_id,
        project_id=project_id,
        doc_id=doc_id,
        doc_version_id=version_id,
        status="GENERATED",
        analysis_json={},
        summary=None,
        risk_level="MEDIUM",
        coverage_score=None,
        ai_task_id=None,
        created_by=user_id,
        updated_by=None,
    )
    db = _FakeBulkApproveDb([draft], [analysis])
    user = CurrentUser(id=user_id, tenant_id=tenant_id, roles=frozenset({"ADMIN"}))

    async def _fake_get_project(_db, *, user, project_id):
        return object()

    async def _fake_require_write(_db, *, user, project):
        return None

    monkeypatch.setattr(requirement_service, "_get_project", _fake_get_project)
    monkeypatch.setattr(requirement_service, "_require_project_write", _fake_require_write)

    result = await requirement_service.bulk_approve_case_drafts(
        db,
        user=user,
        project_id=project_id,
        payload=requirement_service.BulkApproveCaseDraftsRequest(draftIds=[str(draft_id)]),
    )

    assert result.createdTestCaseCount == 1
    assert result.approvedDraftCount == 1
    assert any(type(x).__name__ == "TestCase" for x in db.added)
    links = [x for x in db.added if isinstance(x, RequirementCaseLink)]
    assert len(links) == 1
    assert links[0].case_draft_id == draft_id
    assert links[0].analysis_id == analysis_id
    assert links[0].doc_id == doc_id
    assert links[0].doc_version_id == version_id
    assert links[0].link_type == "GENERATED_FROM"
    assert draft.status == "COMMITTED"


@pytest.mark.anyio
async def test_bulk_approve_skips_committed_draft_without_duplicate_case_or_link(monkeypatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    analysis_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    draft_id = uuid.UUID("66666666-6666-6666-6666-666666666666")
    draft = GeneratedCaseDraft(
        id=draft_id,
        tenant_id=tenant_id,
        project_id=project_id,
        analysis_id=analysis_id,
        test_point_id=None,
        title="验证登录成功",
        type="API",
        priority="P1",
        preconditions=None,
        steps_json=[{"step": "调用登录接口"}],
        expected_results_json=["返回200"],
        test_data_json={},
        status="COMMITTED",
        confidence=0.9,
        ai_meta_json={},
        created_by=user_id,
        reviewed_by=user_id,
    )
    analysis = RequirementAnalysis(
        id=analysis_id,
        tenant_id=tenant_id,
        project_id=project_id,
        doc_id=uuid.UUID("99999999-9999-9999-9999-999999999999"),
        doc_version_id=uuid.UUID("88888888-8888-8888-8888-888888888888"),
        status="GENERATED",
        analysis_json={},
        summary=None,
        risk_level="MEDIUM",
        coverage_score=None,
        ai_task_id=None,
        created_by=user_id,
        updated_by=None,
    )
    db = _FakeBulkApproveDb([draft], [analysis])
    user = CurrentUser(id=user_id, tenant_id=tenant_id, roles=frozenset({"ADMIN"}))

    async def _fake_get_project(_db, *, user, project_id):
        return object()

    async def _fake_require_write(_db, *, user, project):
        return None

    monkeypatch.setattr(requirement_service, "_get_project", _fake_get_project)
    monkeypatch.setattr(requirement_service, "_require_project_write", _fake_require_write)

    result = await requirement_service.bulk_approve_case_drafts(
        db,
        user=user,
        project_id=project_id,
        payload=requirement_service.BulkApproveCaseDraftsRequest(draftIds=[str(draft_id)]),
    )

    assert result.createdTestCaseCount == 0
    assert result.approvedDraftCount == 0
    assert not any(type(x).__name__ == "TestCase" for x in db.added)
    assert not any(isinstance(x, RequirementCaseLink) for x in db.added)


@pytest.mark.anyio
async def test_list_requirement_case_links_returns_detail_with_testcase_title(monkeypatch) -> None:
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    analysis_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    link = RequirementCaseLink(
        id=uuid.UUID("99999999-9999-9999-9999-999999999999"),
        tenant_id=tenant_id,
        project_id=project_id,
        doc_id=uuid.UUID("77777777-7777-7777-7777-777777777777"),
        doc_version_id=uuid.UUID("88888888-8888-8888-8888-888888888888"),
        analysis_id=analysis_id,
        test_point_id=None,
        case_draft_id=uuid.UUID("66666666-6666-6666-6666-666666666666"),
        testcase_id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        link_type="GENERATED_FROM",
        confidence=0.95,
        created_by=user_id,
    )
    link.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    db = _FakeListCaseLinksDb([(link, "验证登录成功")])
    user = CurrentUser(id=user_id, tenant_id=tenant_id, roles=frozenset({"ADMIN"}))
    checked = {"read": False}

    async def _fake_get_project(_db, *, user, project_id):
        return object()

    async def _fake_require_read(_db, *, user, project):
        checked["read"] = True
        return None

    monkeypatch.setattr(requirement_service, "_get_project", _fake_get_project)
    monkeypatch.setattr(requirement_service, "_require_project_read", _fake_require_read)

    data = await requirement_service.list_requirement_case_links(
        db,
        user=user,
        project_id=project_id,
        analysis_id=analysis_id,
    )

    assert checked["read"] is True
    assert len(data) == 1
    assert data[0].analysisId == str(analysis_id)
    assert data[0].testcaseTitle == "验证登录成功"
    assert data[0].confidence == 0.95
