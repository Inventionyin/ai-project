from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import integration_diagnostics as integration_diagnostics_endpoint
from app.core.database import get_db
from app.schemas.integration_diagnostics import (
    ExternalIntegrationDiagnosticItem,
    ExternalIntegrationDiagnosticsData,
    ExternalIntegrationDiagnosticsSummary,
    ExternalIntegrationIssueProviderStats,
)


@dataclass
class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(integration_diagnostics_endpoint.router, prefix="/api")

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


def test_external_integration_diagnostics_endpoint_returns_overview(monkeypatch) -> None:
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async def _fake_diagnostics(db, *, user, project_id):
        return ExternalIntegrationDiagnosticsData(
            summary=ExternalIntegrationDiagnosticsSummary(
                status="WARN",
                totalChecks=3,
                blocking=0,
                warnings=1,
                ready=2,
            ),
            checks=[
                ExternalIntegrationDiagnosticItem(
                    id="notifications.dingtalk",
                    category="notification",
                    provider="DINGTALK",
                    status="READY",
                    title="钉钉通知已配置",
                    detail="通知通道已就绪",
                    recommendation="可执行一次真实回执验证",
                ),
                ExternalIntegrationDiagnosticItem(
                    id="devops.jenkins",
                    category="devops",
                    provider="jenkins",
                    status="WARN",
                    title="Jenkins 流水线缺少 job_name",
                    detail="流水线 trigger 配置不完整",
                    recommendation="补齐 config.job_name|workflowFile",
                    missingFields=["config.job_name|workflowFile"],
                ),
            ],
            issueLinks=[
                ExternalIntegrationIssueProviderStats(provider="JIRA", total=2),
            ],
            nextActions=["补齐 Jenkins 触发配置后再跑真实流水线 smoke"],
        )

    monkeypatch.setattr(
        integration_diagnostics_endpoint,
        "get_external_integration_diagnostics",
        _fake_diagnostics,
    )

    client = TestClient(_build_app())
    resp = client.get(f"/api/projects/{project_id}/integrations/diagnostics")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["summary"]["status"] == "WARN"
    assert body["data"]["checks"][1]["provider"] == "jenkins"
    assert body["data"]["issueLinks"][0]["provider"] == "JIRA"
