from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import dashboard as dashboard_endpoint
from app.core.database import get_db
from app.schemas.dashboard import (
    DashboardTrialOperationData,
    DashboardTrialOperationReportData,
    DashboardTrialOperationReportSnapshotData,
)
from app.services.dashboard import _build_trial_operation_acceptance_summary


@dataclass
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
        return CurrentUser(
            id=_USER_ID,
            tenant_id=_TENANT_ID,
            roles=frozenset({"ADMIN"}),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return app


def _make_trial_dashboard() -> DashboardTrialOperationData:
    return DashboardTrialOperationData(
        metrics={
            "requirementDocs": 33,
            "testcases": 593,
            "defects": 256,
            "defectClusters": 223,
            "riskHints": 256,
        },
        testcasePriorityDistribution={"P0": 234, "P1": 192, "P2": 167},
        testcaseStatusDistribution={"REVIEWED": 593},
        testcaseTypeDistribution={"UI": 593},
        testcaseFeatureDistribution={"基本功能": 193, "AI角色聊天_初态与续推重生": 77},
        defectSeverityDistribution={"P0": 12, "P1": 68, "P2": 176},
        defectStatusDistribution={"OPEN": 256},
        topDefectClusters=[
            {
                "clusterKey": "chat-reset",
                "count": 9,
                "sampleTitles": ["聊天重置异常"],
                "rootCauseHint": "疑似同类缺陷，建议结合最近改动排查",
                "confidence": 0.75,
            }
        ],
        topRiskHints=[
            {
                "defectId": str(uuid.UUID("33333333-3333-3333-3333-333333333333")),
                "title": "P0 登录失败",
                "status": "OPEN",
                "severity": "P0",
                "updatedAt": 1710000000,
                "riskScore": 8.2,
                "hint": "P0 缺陷处于未关闭状态，建议优先回归",
            }
        ],
        sampleTestcases=["聊天重置与弹窗", "角色收藏"],
        acceptanceSummary={
            "conclusion": "建议谨慎通过",
            "score": 66,
            "level": "WARNING",
            "highlights": ["已纳入 593 条测试用例", "已汇总 256 条缺陷记录", "覆盖 33 份需求文档"],
            "risks": ["仍有 12 个 P0 缺陷未关闭", "当前风险提示总量 256 条"],
            "nextActions": ["优先关闭 P0 缺陷并补充回归", "按风险提示清单推进修复验收"],
        },
    )


def test_get_trial_operation_dashboard(monkeypatch) -> None:
    async def _fake_get(db, *, user, project_id):
        assert project_id == _PROJECT_ID
        return _make_trial_dashboard()

    monkeypatch.setattr(dashboard_endpoint, "get_dashboard_trial_operation", _fake_get)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/dashboard/trial-operation")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["metrics"]["requirementDocs"] == 33
    assert body["data"]["metrics"]["testcases"] == 593
    assert body["data"]["testcasePriorityDistribution"]["P0"] == 234
    assert body["data"]["topDefectClusters"][0]["clusterKey"] == "chat-reset"
    assert body["data"]["acceptanceSummary"]["level"] == "WARNING"
    assert body["data"]["acceptanceSummary"]["score"] == 66
    assert len(body["data"]["acceptanceSummary"]["highlights"]) >= 3


def _make_trial_dashboard_report() -> DashboardTrialOperationReportData:
    return DashboardTrialOperationReportData(
        title="WeiTesting 真实数据试运行验收报告",
        generatedAt=1710001234,
        markdown="# WeiTesting 真实数据试运行验收报告\n\n## 结论\n建议谨慎通过",
        summary={
            "conclusion": "建议谨慎通过",
            "score": 66,
            "level": "WARNING",
            "highlights": ["已纳入 593 条测试用例", "已汇总 256 条缺陷记录", "覆盖 33 份需求文档"],
            "risks": ["仍有 12 个 P0 缺陷未关闭", "当前风险提示总量 256 条"],
            "nextActions": ["优先关闭 P0 缺陷并补充回归", "按风险提示清单推进修复验收"],
        },
    )


def test_get_trial_operation_dashboard_report(monkeypatch) -> None:
    async def _fake_get(db, *, user, project_id):
        assert project_id == _PROJECT_ID
        return _make_trial_dashboard_report()

    monkeypatch.setattr(dashboard_endpoint, "get_dashboard_trial_operation_report", _fake_get)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/dashboard/trial-operation/report")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["title"] == "WeiTesting 真实数据试运行验收报告"
    assert body["data"]["generatedAt"] == 1710001234
    assert "## 结论" in body["data"]["markdown"]
    assert body["data"]["summary"]["level"] == "WARNING"
    assert body["data"]["summary"]["score"] == 66


def _make_trial_dashboard_report_snapshot() -> DashboardTrialOperationReportSnapshotData:
    return DashboardTrialOperationReportSnapshotData(
        id=str(uuid.UUID("44444444-4444-4444-4444-444444444444")),
        projectId=str(_PROJECT_ID),
        title="WeiTesting 真实数据试运行验收报告",
        generatedAt=1710001234,
        markdown="# WeiTesting 真实数据试运行验收报告\n\n## 结论\n建议谨慎通过",
        summary={
            "conclusion": "建议谨慎通过",
            "score": 66,
            "level": "WARNING",
            "highlights": ["已纳入 593 条测试用例", "已汇总 256 条缺陷记录", "覆盖 33 份需求文档"],
            "risks": ["仍有 12 个 P0 缺陷未关闭", "当前风险提示总量 256 条"],
            "nextActions": ["优先关闭 P0 缺陷并补充回归", "按风险提示清单推进修复验收"],
        },
        score=66,
        level="WARNING",
        acceptanceScore=66,
        acceptanceLevel="WARNING",
        createdBy=str(_USER_ID),
        createdAt=1710001300,
    )


def test_create_trial_operation_dashboard_report_snapshot(monkeypatch) -> None:
    async def _fake_create(db, *, user, project_id, payload=None):
        assert project_id == _PROJECT_ID
        assert user.id == _USER_ID
        assert payload is not None
        assert payload.title == "手动验收报告"
        assert payload.summary.score == 88
        return _make_trial_dashboard_report_snapshot()

    monkeypatch.setattr(dashboard_endpoint, "create_dashboard_trial_operation_report_snapshot", _fake_create)

    client = TestClient(_build_app())
    resp = client.post(
        f"/api/projects/{_PROJECT_ID}/dashboard/trial-operation/report/snapshots",
        json={
            "title": "手动验收报告",
            "generatedAt": 1710005678,
            "markdown": "# 手动验收报告",
            "summary": {
                "conclusion": "建议通过",
                "score": 88,
                "level": "PASS",
                "highlights": ["数据完整"],
                "risks": [],
                "nextActions": ["持续跟踪"],
            },
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["id"] == "44444444-4444-4444-4444-444444444444"
    assert body["data"]["title"] == "WeiTesting 真实数据试运行验收报告"
    assert body["data"]["score"] == 66
    assert body["data"]["level"] == "WARNING"
    assert body["data"]["acceptanceScore"] == 66
    assert body["data"]["acceptanceLevel"] == "WARNING"


def test_list_trial_operation_dashboard_report_snapshots(monkeypatch) -> None:
    async def _fake_list(db, *, user, project_id, page, page_size):
        assert project_id == _PROJECT_ID
        assert page == 1
        assert page_size == 6
        return 1, [_make_trial_dashboard_report_snapshot()]

    monkeypatch.setattr(dashboard_endpoint, "list_dashboard_trial_operation_report_snapshots", _fake_list)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/dashboard/trial-operation/report/snapshots?page=1&pageSize=6")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["page"] == 1
    assert body["data"]["pageSize"] == 6
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["id"] == "44444444-4444-4444-4444-444444444444"
    assert body["data"]["items"][0]["score"] == 66
    assert body["data"]["items"][0]["level"] == "WARNING"
    assert body["data"]["items"][0]["markdown"].startswith("# WeiTesting")


def test_get_trial_operation_dashboard_report_snapshot(monkeypatch) -> None:
    expected_snapshot_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

    async def _fake_get(db, *, user, project_id, snapshot_id):
        assert project_id == _PROJECT_ID
        assert snapshot_id == expected_snapshot_id
        return _make_trial_dashboard_report_snapshot()

    monkeypatch.setattr(dashboard_endpoint, "get_dashboard_trial_operation_report_snapshot", _fake_get)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/dashboard/trial-operation/report/snapshots/{expected_snapshot_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["id"] == str(expected_snapshot_id)
    assert "## 结论" in body["data"]["markdown"]
    assert body["data"]["summary"]["score"] == 66


def test_build_trial_operation_acceptance_summary_pass() -> None:
    summary = _build_trial_operation_acceptance_summary(
        metrics={
            "requirementDocs": 10,
            "testcases": 120,
            "defects": 8,
            "defectClusters": 2,
            "riskHints": 3,
        },
        defect_severity_distribution={"P0": 0, "P1": 3, "P2": 5},
    )

    assert summary.level == "PASS"
    assert 80 <= summary.score <= 100
    assert summary.risks == []


def test_build_trial_operation_acceptance_summary_insufficient() -> None:
    summary = _build_trial_operation_acceptance_summary(
        metrics={
            "requirementDocs": 0,
            "testcases": 0,
            "defects": 0,
            "defectClusters": 0,
            "riskHints": 0,
        },
        defect_severity_distribution={},
    )

    assert summary.level == "INSUFFICIENT"
    assert 0 <= summary.score <= 49
