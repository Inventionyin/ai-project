from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import dashboard as dashboard_endpoint
from app.core.database import get_db
from app.schemas.dashboard import (
    DashboardCaseGovernanceData,
    DashboardCaseGovernanceDuplicateTitleItem,
    DashboardCaseGovernanceLowValueItem,
    DashboardCaseGovernanceModuleP0DensityItem,
    DashboardTrialOperationExecutionImportData,
    DashboardTrialOperationGovernanceApplyData,
    DashboardTrialOperationGovernanceHistoryData,
    DashboardTrialOperationGovernanceHistoryItem,
    DashboardTrialOperationGovernanceSuggestionBatch,
    DashboardTrialOperationGovernanceSuggestionItem,
)


class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


_USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(dashboard_endpoint.router, prefix="/api")

    async def _override_db():
        yield _DummySession()

    async def _override_user() -> CurrentUser:
        return CurrentUser(id=_USER_ID, tenant_id=_TENANT_ID, roles=frozenset({"ADMIN"}))

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def test_get_case_governance(monkeypatch) -> None:
    async def _fake_governance(db, *, user, project_id):
        assert project_id == _PROJECT_ID
        assert user.id == _USER_ID
        return DashboardCaseGovernanceData(
            totalCases=5899,
            uniqueCaseIds=5899,
            sourceCaseIds=27,
            formalCases=27,
            testPointCases=5872,
            generatedImportIds=5872,
            emptyCaseIds=0,
            emptyTitles=0,
            p0Cases=1651,
            p0Density=27.99,
            typeDistribution={"UI": 5884, "API": 9, "PERF": 6},
            priorityDistribution={"P0": 1651, "P1": 2092, "P2": 2152, "P3": 4},
            moduleDistribution={"活动": 2692, "版本需求": 3180},
            duplicateTitleCandidates=[
                DashboardCaseGovernanceDuplicateTitleItem(title="弹窗UI验证", count=44, modules=["活动", "版本需求"])
            ],
            lowValueCandidates=[
                DashboardCaseGovernanceLowValueItem(
                    id="case-1",
                    testCaseId="TC_LOW_001",
                    title="无反应",
                    feature="活动",
                    priority="P2",
                    type="UI",
                    reasons=["标题过短或语义不完整"],
                )
            ],
            moduleP0Density=[
                DashboardCaseGovernanceModuleP0DensityItem(feature="活动", total=100, p0=40, p0Density=40.0)
            ],
        )

    monkeypatch.setattr(dashboard_endpoint, "get_dashboard_case_governance", _fake_governance)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/dashboard/trial-operation/case-governance")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["totalCases"] == 5899
    assert body["data"]["p0Density"] == 27.99
    assert body["data"]["duplicateTitleCandidates"][0]["title"] == "弹窗UI验证"
    assert body["data"]["lowValueCandidates"][0]["reasons"] == ["标题过短或语义不完整"]


def test_generate_trial_operation_governance_suggestions(monkeypatch) -> None:
    async def _fake_generate(db, *, user, project_id):
        assert project_id == _PROJECT_ID
        assert user.id == _USER_ID
        return DashboardTrialOperationGovernanceSuggestionBatch(
            batchId="batch-1",
            generatedAt=1710000000,
            source="RULE",
            summary={
                "duplicates": 1,
                "lowValue": 1,
                "promotableTestPoints": 1,
                "p0CoverageGaps": 1,
            },
            items=[
                DashboardTrialOperationGovernanceSuggestionItem(
                    id="suggestion-1",
                    category="DUPLICATE_TITLE",
                    title="合并重复标题候选",
                    severity="MEDIUM",
                    targetIds=["case-1", "case-2"],
                    targetCount=2,
                    reason="存在重复标题",
                    recommendation="保留一条主用例，其余标记为重复候选",
                    action="TAG_DUPLICATE",
                    confidence=0.82,
                    canApply=True,
                )
            ],
        )

    monkeypatch.setattr(dashboard_endpoint, "generate_dashboard_trial_operation_governance_suggestions", _fake_generate)

    client = TestClient(_build_app())
    resp = client.post(f"/api/projects/{_PROJECT_ID}/dashboard/trial-operation/governance/suggestions")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["batchId"] == "batch-1"
    assert body["data"]["items"][0]["action"] == "TAG_DUPLICATE"


def test_apply_trial_operation_governance_suggestions(monkeypatch) -> None:
    async def _fake_apply(db, *, user, project_id, payload):
        assert project_id == _PROJECT_ID
        assert payload.batchId == "batch-1"
        assert payload.suggestionIds == ["suggestion-1"]
        return DashboardTrialOperationGovernanceApplyData(
            batchId="batch-1",
            appliedSuggestionIds=["suggestion-1"],
            skippedSuggestionIds=[],
            updatedCases=2,
            summary="已应用 1 条治理建议，更新 2 条用例",
        )

    monkeypatch.setattr(dashboard_endpoint, "apply_dashboard_trial_operation_governance_suggestions", _fake_apply)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/dashboard/trial-operation/governance/apply",
        json={"batchId": "batch-1", "suggestionIds": ["suggestion-1"]},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["updatedCases"] == 2
    assert body["data"]["appliedSuggestionIds"] == ["suggestion-1"]


def test_import_trial_operation_execution_results(monkeypatch) -> None:
    async def _fake_import_execution(db, *, user, project_id, payload):
        assert project_id == _PROJECT_ID
        assert payload.totalLimit == 5
        return DashboardTrialOperationExecutionImportData(
            runId="run-1",
            total=5,
            passed=4,
            failed=1,
            skipped=0,
            summary="已写入执行结果：5 条",
        )

    monkeypatch.setattr(dashboard_endpoint, "import_dashboard_trial_operation_execution_results", _fake_import_execution)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/dashboard/trial-operation/execution-results",
        json={"totalLimit": 5, "failedCaseIds": []},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["runId"] == "run-1"
    assert body["data"]["total"] == 5


def test_get_trial_operation_governance_history(monkeypatch) -> None:
    async def _fake_history(db, *, user, project_id, limit):
        assert project_id == _PROJECT_ID
        assert limit == 5
        return DashboardTrialOperationGovernanceHistoryData(
            generatedBatches=3,
            appliedBatches=2,
            appliedSuggestions=9,
            updatedCases=88,
            latestBatchId="gov-latest",
            items=[
                DashboardTrialOperationGovernanceHistoryItem(
                    batchId="gov-latest",
                    generatedAt=1710001000,
                    source="HYBRID",
                    totalSuggestions=12,
                    appliedSuggestions=4,
                    updatedCases=44,
                    status="PARTIAL_APPLIED",
                    summary="生成 12 条，已应用 4 条",
                )
            ],
        )

    monkeypatch.setattr(dashboard_endpoint, "get_dashboard_trial_operation_governance_history", _fake_history)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/dashboard/trial-operation/governance/history?limit=5")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["generatedBatches"] == 3
    assert body["data"]["items"][0]["status"] == "PARTIAL_APPLIED"
