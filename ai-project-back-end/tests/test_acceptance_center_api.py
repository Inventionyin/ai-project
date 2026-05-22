from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import acceptance as acceptance_endpoint
from app.core.database import get_db
from app.schemas.acceptance import (
    AcceptanceCheck,
    AcceptanceExternalSystem,
    AcceptanceReportData,
    AcceptanceSummaryData,
)
from app.schemas.dashboard import DashboardTrialOperationAcceptanceSummary, DashboardTrialOperationData
from app.schemas.integration import (
    NotificationDiagnosticsData,
    NotificationDiagnosticsProviderReadiness,
    NotificationDiagnosticsSummary,
)
from app.schemas.ops import OpsHealthCheck, OpsHealthSummaryData
from app.services.acceptance import _build_checks, _load_devops_external_systems, _render_report_markdown


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
    app.include_router(acceptance_endpoint.router, prefix="/api")

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


def _make_summary() -> AcceptanceSummaryData:
    generated_at = datetime.now(timezone.utc)
    return AcceptanceSummaryData(
        overallStatus="WARN",
        generatedAt=generated_at,
        projectId=str(_PROJECT_ID),
        projectName="X-MAX AI Testing",
        score=72,
        checks=[
            AcceptanceCheck(
                key="realData",
                label="真实数据基线",
                status="READY",
                detail="已导入需求、用例和缺陷数据。",
                metric={"requirementDocs": 33, "testcases": 593, "defects": 256},
                recommendation="继续保持导入批次可追溯。",
            ),
            AcceptanceCheck(
                key="externalSystems",
                label="外部系统联调",
                status="WARN",
                detail="钉钉已配置，Jenkins 未完成真实构建回执。",
                metric={"readyProviders": 1, "totalProviders": 2},
                recommendation="补一次真实 Jenkins 构建和回执校验。",
            ),
        ],
        externalSystems=[
            AcceptanceExternalSystem(
                provider="DINGTALK",
                status="READY",
                configured=True,
                lastVerifiedAt=None,
                missingFields=[],
                detail="Provider is supported and configured.",
                recommendation="触发一次真实通知确认群回执。",
            ),
            AcceptanceExternalSystem(
                provider="JENKINS",
                status="WARN",
                configured=False,
                lastVerifiedAt=None,
                missingFields=["token"],
                detail="缺少 token。",
                recommendation="补齐 Jenkins token 后执行一次真实构建。",
            ),
        ],
        metrics={"requirementDocs": 33, "testcases": 593, "defects": 256},
        nextActions=["补 Jenkins 真实构建回执", "复跑生产验收报告"],
    )


def test_get_acceptance_summary(monkeypatch) -> None:
    async def _fake_summary(db, *, user, project_id):
        assert project_id == _PROJECT_ID
        assert user.id == _USER_ID
        return _make_summary()

    monkeypatch.setattr(acceptance_endpoint, "get_acceptance_summary", _fake_summary)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/acceptance/summary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["overallStatus"] == "WARN"
    assert body["data"]["projectName"] == "X-MAX AI Testing"
    assert body["data"]["score"] == 72
    assert body["data"]["checks"][0]["key"] == "realData"
    assert body["data"]["externalSystems"][1]["provider"] == "JENKINS"
    assert body["data"]["externalSystems"][1]["missingFields"] == ["token"]


def test_get_acceptance_report(monkeypatch) -> None:
    async def _fake_report(db, *, user, project_id):
        assert project_id == _PROJECT_ID
        return AcceptanceReportData(
            title="生产验收中心报告",
            generatedAt=datetime.now(timezone.utc),
            summary=_make_summary(),
            markdown="# 生产验收中心报告\n\n## 结论\n- 总体状态：WARN",
        )

    monkeypatch.setattr(acceptance_endpoint, "get_acceptance_report", _fake_report)

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{_PROJECT_ID}/acceptance/report")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["title"] == "生产验收中心报告"
    assert body["data"]["summary"]["overallStatus"] == "WARN"
    assert "## 结论" in body["data"]["markdown"]


class _ScalarResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows

    def first(self) -> object | None:
        return self._rows[0] if self._rows else None


class _ExecuteResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._rows)


class _DevOpsDb:
    def __init__(self, pipelines: list[object], runs_by_pipeline: dict[uuid.UUID, object | None]) -> None:
        self._pipelines = pipelines
        self._runs_by_pipeline = runs_by_pipeline
        self.run_query_count = 0

    async def execute(self, _stmt):
        if self.run_query_count == 0:
            self.run_query_count += 1
            return _ExecuteResult(self._pipelines)
        pipeline = self._pipelines[self.run_query_count - 1]
        self.run_query_count += 1
        run = self._runs_by_pipeline.get(pipeline.id)
        return _ExecuteResult([run] if run is not None else [])


def test_load_devops_external_systems_queries_latest_run_per_pipeline() -> None:
    import asyncio

    async def _run() -> None:
        pipeline_a = SimpleNamespace(
            id=uuid.uuid4(),
            provider="jenkins",
            enabled=True,
            config_json={"baseUrl": "https://jenkins.example.com", "jobName": "acceptance", "token": "masked"},
            repo_full_name=None,
            workflow_file=None,
            updated_at=datetime.now(timezone.utc),
        )
        pipeline_b = SimpleNamespace(
            id=uuid.uuid4(),
            provider="github_actions",
            enabled=True,
            config_json={},
            repo_full_name="org/repo",
            workflow_file="ci.yml",
            updated_at=datetime.now(timezone.utc),
        )
        db = _DevOpsDb(
            [pipeline_a, pipeline_b],
            {
                pipeline_a.id: SimpleNamespace(pipeline_id=pipeline_a.id, status="SUCCESS", updated_at=datetime.now(timezone.utc)),
                pipeline_b.id: SimpleNamespace(pipeline_id=pipeline_b.id, status="FAILED", updated_at=datetime.now(timezone.utc)),
            },
        )
        user = CurrentUser(id=_USER_ID, tenant_id=_TENANT_ID, roles=frozenset({"ADMIN"}))

        systems = await _load_devops_external_systems(db, user=user, project_id=_PROJECT_ID)

        assert db.run_query_count == 3
        by_provider = {item.provider: item for item in systems}
        assert by_provider["JENKINS"].status == "READY"
        assert by_provider["GITHUB_ACTIONS"].status == "WARN"
        assert by_provider["GITHUB_ACTIONS"].configured is True

    asyncio.run(_run())


def test_build_checks_maps_real_contract_status_and_metrics() -> None:
    trial = DashboardTrialOperationData(
        metrics={"requirementDocs": 1, "testcases": 12, "defects": 0},
        acceptanceSummary=DashboardTrialOperationAcceptanceSummary(
            conclusion="建议通过",
            score=92,
            level="PASS",
            highlights=[],
            risks=[],
            nextActions=[],
        ),
    )
    diagnostics = NotificationDiagnosticsData(
        summary=NotificationDiagnosticsSummary(status="WARN", total=1, blocking=0, warnings=1, ready=0, failedDeliveries=0),
        providerReadiness=[
            NotificationDiagnosticsProviderReadiness(
                provider="DINGTALK",
                ready=True,
                reason="Provider is supported and configured.",
                notificationCount=1,
                configured=True,
                missingFields=[],
                diagnostics={},
            )
        ],
    )
    ops = OpsHealthSummaryData(
        overallStatus="WARN",
        generatedAt=datetime.now(timezone.utc),
        checks=[
            OpsHealthCheck(
                key="workers",
                label="Workers",
                status="WARN",
                detail="no worker heartbeat",
                metric={"totalCount": 0},
                recommendation="Bring workers online.",
            )
        ],
    )
    external_systems = [
        AcceptanceExternalSystem(
            provider="DINGTALK",
            status="READY",
            configured=True,
            missingFields=[],
            detail="ok",
            recommendation="保持真实外部通知 smoke。",
        )
    ]

    checks = _build_checks(trial=trial, diagnostics=diagnostics, ops=ops, external_systems=external_systems)
    by_key = {item.key: item for item in checks}

    assert by_key["realData"].status == "READY"
    assert by_key["externalSystems"].metric["readyProviders"] == 1
    assert by_key["externalSystems"].metric["warnings"] == 1
    assert by_key["opsHealth"].status == "WARN"


def test_render_report_markdown_explains_blocked_real_data_as_phase_acceptance() -> None:
    generated_at = datetime.now(timezone.utc)
    summary = AcceptanceSummaryData(
        overallStatus="BLOCKED",
        generatedAt=generated_at,
        projectId=str(_PROJECT_ID),
        projectName="真实业务数据验收",
        score=54,
        checks=[
            AcceptanceCheck(
                key="realData",
                label="真实数据基线",
                status="BLOCKED",
                detail="建议暂缓",
                metric={
                    "requirementDocs": 31,
                    "testcases": 5899,
                    "defects": 460,
                    "riskHints": 460,
                    "executedCaseRuns": 27,
                },
                recommendation="补齐需求文档、测试用例或关闭阻塞缺陷后再进入生产验收。",
            ),
            AcceptanceCheck(
                key="externalSystems",
                label="外部系统联调",
                status="READY",
                detail="通知诊断：READY，外部系统 2 项。",
                metric={"readyProviders": 2},
                recommendation="保持外部系统回执的定期 smoke。",
            ),
            AcceptanceCheck(
                key="opsHealth",
                label="运维可观测性",
                status="READY",
                detail="运维健康聚合状态：READY",
                metric={"workers": {"totalCount": 1}},
                recommendation="保持健康检查和告警阈值巡检。",
            ),
        ],
        externalSystems=[],
        metrics={
            "requirementDocs": 31,
            "testcases": 5899,
            "defects": 460,
            "riskHints": 460,
            "executedCaseRuns": 27,
        },
        nextActions=["导出本页 Markdown 作为阶段验收附件。"],
    )

    markdown = _render_report_markdown(summary)

    assert "## 阶段验收结论" in markdown
    assert "阶段验收暂缓" in markdown
    assert "外部系统联调与运维健康已就绪" in markdown
    assert "有条件放行前置条件" in markdown
    assert "缺陷：460" in markdown
