from __future__ import annotations

import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.integration import IssueLink
from app.models.run import Run
from app.schemas.acceptance import AcceptanceExternalSystem, AcceptanceSummaryData
from app.schemas.integration_diagnostics import (
    ExternalIntegrationDiagnosticItem,
    ExternalIntegrationDiagnosticsData,
    ExternalIntegrationDiagnosticsSummary,
    ExternalIntegrationIssueProviderStats,
)
from app.services.acceptance import get_acceptance_summary

_DEVOPS_PROVIDERS = {"JENKINS", "GITHUB", "GITHUB_ACTIONS", "GITLAB", "GITLAB_CI"}


def _category_for_provider(provider: str) -> str:
    normalized = str(provider or "").strip().upper()
    return "devops" if normalized in _DEVOPS_PROVIDERS else "notification"


def _summary_for_checks(checks: list[ExternalIntegrationDiagnosticItem]) -> ExternalIntegrationDiagnosticsSummary:
    blocking = sum(1 for item in checks if item.status == "BLOCKED")
    warnings = sum(1 for item in checks if item.status == "WARN")
    ready = sum(1 for item in checks if item.status == "READY")
    status = "BLOCKED" if blocking else "WARN" if warnings else "READY"
    return ExternalIntegrationDiagnosticsSummary(
        status=status,
        totalChecks=len(checks),
        blocking=blocking,
        warnings=warnings,
        ready=ready,
    )


def _external_system_to_check(item: AcceptanceExternalSystem, index: int) -> ExternalIntegrationDiagnosticItem:
    provider = str(item.provider or "EXTERNAL").strip().upper()
    return ExternalIntegrationDiagnosticItem(
        id=f"external.{provider.lower()}.{index}",
        category=_category_for_provider(provider),  # type: ignore[arg-type]
        provider=provider,
        status=item.status,
        title=f"{provider} 联调状态",
        detail=item.detail,
        recommendation=item.recommendation,
        configured=item.configured,
        missingFields=list(item.missingFields or []),
        lastVerifiedAt=item.lastVerifiedAt,
    )


def _acceptance_check_to_diagnostic(item_key: str, status: str, detail: str, recommendation: str) -> ExternalIntegrationDiagnosticItem:
    category = "ops" if item_key == "opsHealth" else "acceptance"
    provider = "OPS" if item_key == "opsHealth" else "ACCEPTANCE"
    return ExternalIntegrationDiagnosticItem(
        id=f"check.{item_key}",
        category=category,  # type: ignore[arg-type]
        provider=provider,
        status=status,  # type: ignore[arg-type]
        title="运维健康" if item_key == "opsHealth" else "验收检查",
        detail=detail,
        recommendation=recommendation,
    )


async def _load_issue_provider_stats(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> list[ExternalIntegrationIssueProviderStats]:
    count_expr = func.count(IssueLink.id)
    rows = (
        await db.execute(
            select(IssueLink.provider, count_expr)
            .join(Run, Run.id == IssueLink.run_id)
            .where(
                IssueLink.tenant_id == user.tenant_id,
                Run.tenant_id == user.tenant_id,
                Run.project_id == project_id,
            )
            .group_by(IssueLink.provider)
            .order_by(desc(count_expr), IssueLink.provider.asc())
        )
    ).all()
    return [
        ExternalIntegrationIssueProviderStats(provider=str(provider).upper(), total=int(total or 0))
        for provider, total in rows
    ]


def build_external_integration_diagnostics(
    summary: AcceptanceSummaryData,
    issue_links: list[ExternalIntegrationIssueProviderStats],
) -> ExternalIntegrationDiagnosticsData:
    checks = [_external_system_to_check(item, index) for index, item in enumerate(summary.externalSystems, start=1)]
    for check in summary.checks:
        if check.key == "opsHealth":
            checks.append(_acceptance_check_to_diagnostic(check.key, check.status, check.detail, check.recommendation))
    if issue_links:
        checks.append(
            ExternalIntegrationDiagnosticItem(
                id="issues.linked-providers",
                category="issue",
                provider="ISSUE_TRACKING",
                status="READY",
                title="Issue 关联记录",
                detail=f"已关联 {sum(item.total for item in issue_links)} 条外部 Issue。",
                recommendation="保持 Jira/禅道缺陷创建与回链的抽样检查。",
            )
        )
    else:
        checks.append(
            ExternalIntegrationDiagnosticItem(
                id="issues.no-linked-provider",
                category="issue",
                provider="ISSUE_TRACKING",
                status="WARN",
                title="Issue 关联记录为空",
                detail="当前项目还没有 Jira/禅道等外部 Issue 回链记录。",
                recommendation="至少创建一次真实外部 Issue，并确认平台能展示回链。",
            )
        )
    return ExternalIntegrationDiagnosticsData(
        projectId=summary.projectId,
        projectName=summary.projectName,
        generatedAt=summary.generatedAt,
        summary=_summary_for_checks(checks),
        checks=checks,
        issueLinks=issue_links,
        nextActions=list(summary.nextActions),
    )


async def get_external_integration_diagnostics(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> ExternalIntegrationDiagnosticsData:
    summary = await get_acceptance_summary(db, user=user, project_id=project_id)
    issue_links = await _load_issue_provider_stats(db, user=user, project_id=project_id)
    return build_external_integration_diagnostics(summary, issue_links)
