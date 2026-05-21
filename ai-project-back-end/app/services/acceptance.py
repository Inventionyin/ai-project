from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.devops_pipeline import DevOpsPipeline, DevOpsRun
from app.schemas.acceptance import (
    AcceptanceCheck,
    AcceptanceExternalSystem,
    AcceptanceReportData,
    AcceptanceStatus,
    AcceptanceSummaryData,
)
from app.schemas.dashboard import DashboardTrialOperationData
from app.schemas.integration import NotificationDiagnosticsData
from app.schemas.ops import OpsHealthSummaryData
from app.services.dashboard import _get_project, _require_project_read, get_dashboard_trial_operation
from app.services.integration_config import get_notification_diagnostics
from app.services.ops_health import build_ops_health_summary


def _status_rank(status: str) -> int:
    return {"READY": 0, "WARN": 1, "BLOCKED": 2}.get(str(status or "").upper(), 2)


def _worst_status(statuses: list[str]) -> AcceptanceStatus:
    if not statuses:
        return "BLOCKED"
    status = max((str(item).upper() for item in statuses), key=_status_rank)
    if status in {"READY", "WARN", "BLOCKED"}:
        return status  # type: ignore[return-value]
    return "BLOCKED"


def _trial_status(level: str) -> AcceptanceStatus:
    normalized = str(level or "").upper()
    if normalized == "PASS":
        return "READY"
    if normalized in {"WARNING", "INSUFFICIENT"}:
        return "WARN"
    return "BLOCKED"


def _score_penalty(status: str) -> int:
    if status == "BLOCKED":
        return 18
    if status == "WARN":
        return 8
    return 0


def _provider_status(configured: bool, ready: bool, missing_fields: list[str]) -> AcceptanceStatus:
    if ready:
        return "READY"
    if configured and not missing_fields:
        return "WARN"
    return "BLOCKED"


async def _load_devops_external_systems(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> list[AcceptanceExternalSystem]:
    pipelines = (
        await db.execute(
            select(DevOpsPipeline)
            .where(
                DevOpsPipeline.tenant_id == user.tenant_id,
                DevOpsPipeline.project_id == project_id,
            )
            .order_by(desc(DevOpsPipeline.updated_at), desc(DevOpsPipeline.id))
        )
    ).scalars().all()
    if not pipelines:
        return [
            AcceptanceExternalSystem(
                provider="JENKINS",
                status="WARN",
                configured=False,
                missingFields=["pipeline"],
                detail="尚未配置 Jenkins/GitHub Actions 等流水线。",
                recommendation="配置至少一条 DevOps pipeline，并执行一次真实构建回执。",
            )
        ]

    systems: list[AcceptanceExternalSystem] = []
    for pipeline in pipelines[:8]:
        provider = str(pipeline.provider or "DEVOPS").strip().upper()
        config = dict(pipeline.config_json or {})
        missing_fields: list[str] = []
        if provider in {"JENKINS", "JENKINS_PIPELINE"}:
            if not (config.get("baseUrl") or config.get("url")):
                missing_fields.append("baseUrl")
            if not (config.get("jobName") or config.get("job")):
                missing_fields.append("jobName")
            if not (config.get("token") or config.get("apiToken")):
                missing_fields.append("token")
        elif provider in {"GITHUB", "GITHUB_ACTIONS"}:
            if not pipeline.repo_full_name:
                missing_fields.append("repository")
            if not pipeline.workflow_file:
                missing_fields.append("workflowFile")

        latest_run = await _load_latest_devops_run(db, user=user, project_id=project_id, pipeline_id=pipeline.id)
        run_status = str(getattr(latest_run, "status", "") or "").upper()
        has_successful_callback = run_status in {"SUCCESS", "PASSED", "COMPLETED"}
        configured = bool(pipeline.enabled) and not missing_fields
        status = "READY" if configured and has_successful_callback else ("WARN" if configured else "BLOCKED")
        detail = "已配置并存在成功构建回执。" if status == "READY" else "流水线已配置，尚需真实构建回执。" if configured else "流水线配置不完整。"
        systems.append(
            AcceptanceExternalSystem(
                provider=provider,
                status=status,
                configured=configured,
                lastVerifiedAt=getattr(latest_run, "updated_at", None) if latest_run else None,
                missingFields=missing_fields,
                detail=detail,
                recommendation="保持构建回执与部署环境一致。" if status == "READY" else "补齐配置后触发一次真实构建并确认回执。",
            )
        )
    return systems


async def _load_latest_devops_run(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    pipeline_id: uuid.UUID,
) -> DevOpsRun | None:
    return (
        await db.execute(
            select(DevOpsRun)
            .where(
                DevOpsRun.tenant_id == user.tenant_id,
                DevOpsRun.project_id == project_id,
                DevOpsRun.pipeline_id == pipeline_id,
            )
            .order_by(desc(DevOpsRun.updated_at), desc(DevOpsRun.id))
            .limit(1)
        )
    ).scalars().first()


def _external_systems_from_diagnostics(diagnostics: NotificationDiagnosticsData) -> list[AcceptanceExternalSystem]:
    systems: list[AcceptanceExternalSystem] = []
    for provider in diagnostics.providerReadiness:
        missing_fields = list(provider.missingFields or [])
        status = _provider_status(bool(provider.configured), bool(provider.ready), missing_fields)
        systems.append(
            AcceptanceExternalSystem(
                provider=str(provider.provider).upper(),
                status=status,
                configured=bool(provider.configured),
                missingFields=missing_fields,
                detail=str(provider.reason or "Provider readiness generated from notification diagnostics."),
                recommendation="触发一次真实外部通知并确认平台回执。" if status == "READY" else "补齐配置并复跑外部系统诊断。",
            )
        )
    if not systems:
        systems.append(
            AcceptanceExternalSystem(
                provider="DINGTALK",
                status="WARN",
                configured=False,
                missingFields=["webhookUrl"],
                detail="尚未配置通知类外部系统。",
                recommendation="至少配置钉钉/飞书/企业微信/Webhook 之一用于验收通知。",
            )
        )
    return systems


def _build_checks(
    *,
    trial: DashboardTrialOperationData,
    diagnostics: NotificationDiagnosticsData,
    ops: OpsHealthSummaryData,
    external_systems: list[AcceptanceExternalSystem],
) -> list[AcceptanceCheck]:
    metrics = dict(trial.metrics or {})
    trial_status = _trial_status(trial.acceptanceSummary.level)
    external_status = _worst_status([item.status for item in external_systems])
    ops_status = _worst_status([check.status for check in ops.checks])

    return [
        AcceptanceCheck(
            key="realData",
            label="真实数据基线",
            status=trial_status,
            detail=trial.acceptanceSummary.conclusion,
            metric=metrics,
            recommendation="继续维护需求、用例、缺陷的导入批次与字段完整性。"
            if trial_status == "READY"
            else "补齐需求文档、测试用例或关闭阻塞缺陷后再进入生产验收。",
        ),
        AcceptanceCheck(
            key="externalSystems",
            label="外部系统联调",
            status=external_status,
            detail=f"通知诊断：{diagnostics.summary.status}，外部系统 {len(external_systems)} 项。",
            metric={
                "providers": len(external_systems),
                "readyProviders": sum(1 for item in external_systems if item.status == "READY"),
                "blocking": diagnostics.summary.blocking,
                "warnings": diagnostics.summary.warnings,
                "failedDeliveries": diagnostics.summary.failedDeliveries,
            },
            recommendation="执行钉钉/Jira/禅道/Jenkins 的真实业务闭环并保留回执。"
            if external_status != "READY"
            else "保持外部系统回执的定期 smoke。",
        ),
        AcceptanceCheck(
            key="opsHealth",
            label="运维可观测性",
            status=ops_status,
            detail=f"运维健康聚合状态：{ops.overallStatus}",
            metric={check.key: check.metric for check in ops.checks},
            recommendation="补齐 Prometheus/Grafana 告警、失败队列和 worker 心跳检查。"
            if ops_status != "READY"
            else "保持健康检查和告警阈值巡检。",
        ),
        AcceptanceCheck(
            key="acceptanceReport",
            label="验收报告",
            status="READY" if trial.acceptanceSummary.score >= 80 else "WARN",
            detail=f"当前真实数据验收评分 {trial.acceptanceSummary.score}。",
            metric={"score": trial.acceptanceSummary.score, "level": trial.acceptanceSummary.level},
            recommendation="导出本页 Markdown 作为阶段验收附件。",
        ),
    ]


def _build_next_actions(checks: list[AcceptanceCheck], external_systems: list[AcceptanceExternalSystem]) -> list[str]:
    actions: list[str] = []
    for check in checks:
        if check.status != "READY" and check.recommendation not in actions:
            actions.append(check.recommendation)
    for system in external_systems:
        if system.status != "READY":
            action = f"{system.provider}: {system.recommendation}"
            if action not in actions:
                actions.append(action)
    return actions[:6] or ["保持真实数据回归、外部系统 smoke、运维告警和性能基线的定期复跑。"]


async def get_acceptance_summary(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> AcceptanceSummaryData:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    trial = await get_dashboard_trial_operation(db, user=user, project_id=project.id)
    diagnostics = await get_notification_diagnostics(db, user=user, project_id=project.id)
    ops = await build_ops_health_summary(db, user)
    external_systems = [
        *_external_systems_from_diagnostics(diagnostics),
        *(await _load_devops_external_systems(db, user=user, project_id=project.id)),
    ]
    checks = _build_checks(trial=trial, diagnostics=diagnostics, ops=ops, external_systems=external_systems)
    overall_status = _worst_status([check.status for check in checks] + [item.status for item in external_systems])
    score = max(0, min(100, int(trial.acceptanceSummary.score) - sum(_score_penalty(check.status) for check in checks[1:])))

    return AcceptanceSummaryData(
        overallStatus=overall_status,
        generatedAt=datetime.now(timezone.utc),
        projectId=str(project.id),
        projectName=str(project.name),
        score=score,
        checks=checks,
        externalSystems=external_systems,
        metrics=dict(trial.metrics or {}),
        nextActions=_build_next_actions(checks, external_systems),
    )


def _render_report_markdown(summary: AcceptanceSummaryData) -> str:
    def _lines(items: list[str]) -> list[str]:
        return [f"- {item}" for item in items] if items else ["- 暂无"]

    check_lines = [
        f"- [{item.status}] {item.label}: {item.detail}；建议：{item.recommendation}"
        for item in summary.checks
    ]
    external_lines = [
        f"- [{item.status}] {item.provider}: configured={item.configured}, missing={','.join(item.missingFields) or '无'}；{item.detail}"
        for item in summary.externalSystems
    ]

    return "\n".join(
        [
            "# 生产验收中心报告",
            "",
            "## 结论",
            f"- 项目：{summary.projectName}",
            f"- 总体状态：{summary.overallStatus}",
            f"- 评分：{summary.score}",
            f"- 生成时间：{summary.generatedAt.isoformat()}",
            "",
            "## 真实数据",
            *[f"- {key}: {value}" for key, value in summary.metrics.items()],
            "",
            "## 验收检查",
            *check_lines,
            "",
            "## 外部系统联调",
            *external_lines,
            "",
            "## 下一步",
            *_lines(summary.nextActions),
        ]
    )


async def get_acceptance_report(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> AcceptanceReportData:
    summary = await get_acceptance_summary(db, user=user, project_id=project_id)
    return AcceptanceReportData(
        title="生产验收中心报告",
        generatedAt=summary.generatedAt,
        summary=summary,
        markdown=_render_report_markdown(summary),
    )
