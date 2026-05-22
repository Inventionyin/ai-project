from __future__ import annotations

import uuid
from datetime import datetime, timezone
import re

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.defect import Defect
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


def _defect_text(row: object) -> str:
    return f"{getattr(row, 'title', '') or ''} {getattr(row, 'description', '') or ''}".lower()


def _defect_sample(row: object) -> str:
    title = str(getattr(row, "title", "") or "").strip()
    return title[:120] if title else "-"


def _defect_cluster_key(row: object) -> str:
    title = str(getattr(row, "title", "") or "").lower()
    tokens = [part.strip(" 　\t\r\n") for part in re.findall(r"[【\[]([^】\]]+)[】\]]", title)]
    useful = [token for token in tokens if token and len(token) >= 2 and token not in {"体验问题", "双端", "客户端mvp"}]
    return "-".join(useful[:3]) if useful else title[:24]


def _build_defect_confirmation_groups(rows: list[object]) -> list[dict[str, object]]:
    buckets = [
        {
            "key": "must_fix",
            "label": "必须修复后再放行",
            "decision": "默认不建议豁免；P0、关键链路、崩溃、黑屏、支付、消息丢失等风险需关闭或负责人签字。",
            "samples": [],
        },
        {
            "key": "duplicate",
            "label": "疑似重复/同模块合并确认",
            "decision": "建议合并同类项，指定模块 owner 后统一关闭或拆分。",
            "samples": [],
        },
        {
            "key": "historical",
            "label": "疑似历史遗留/已知问题",
            "decision": "可进入延期候选，但需要需求方确认是否属于本轮验收范围。",
            "samples": [],
        },
        {
            "key": "experience",
            "label": "体验优化/展示类候选",
            "decision": "可作为观察项或排期优化，前提是不影响核心链路和验收标准。",
            "samples": [],
        },
        {
            "key": "deferrable",
            "label": "可延期/低风险候选",
            "decision": "默认可申请延期，但需给出截止日期和责任人。",
            "samples": [],
        },
    ]
    by_key = {str(item["key"]): item for item in buckets}
    cluster_counts: dict[str, int] = {}
    for row in rows:
        cluster_counts[_defect_cluster_key(row)] = cluster_counts.get(_defect_cluster_key(row), 0) + 1

    def _append(key: str, row: object) -> None:
        bucket = by_key[key]
        bucket["count"] = int(bucket.get("count", 0) or 0) + 1
        samples = bucket["samples"]
        if isinstance(samples, list) and len(samples) < 5:
            sample = _defect_sample(row)
            if sample not in samples:
                samples.append(sample)

    for row in rows:
        severity = str(getattr(row, "severity", "") or "").upper()
        text = _defect_text(row)
        cluster_key = _defect_cluster_key(row)
        if severity == "P0" or any(word in text for word in ("崩溃", "crash", "黑屏", "拉不到流", "支付", "消息丢失", "登录失败")):
            _append("must_fix", row)
        elif any(word in text for word in ("历史", "遗留", "老问题", "已知问题")):
            _append("historical", row)
        elif any(word in text for word in ("体验", "样式", "不美观", "缩略")):
            _append("experience", row)
        elif cluster_counts.get(cluster_key, 0) >= 3:
            _append("duplicate", row)
        else:
            _append("deferrable", row)

    for bucket in buckets:
        bucket.setdefault("count", 0)
    return buckets


def _provider_status(configured: bool, ready: bool, missing_fields: list[str]) -> AcceptanceStatus:
    if ready:
        return "READY"
    if configured and not missing_fields:
        return "WARN"
    return "BLOCKED"


async def _load_open_defects_for_confirmation(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> list[object]:
    return (
        await db.execute(
            select(Defect.title, Defect.description, Defect.status, Defect.severity)
            .where(
                Defect.tenant_id == user.tenant_id,
                Defect.project_id == project_id,
                Defect.status.in_(("OPEN", "IN_PROGRESS")),
            )
            .order_by(Defect.severity.asc(), desc(Defect.updated_at), desc(Defect.id))
            .limit(1000)
        )
    ).all()


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


def _render_report_markdown(
    summary: AcceptanceSummaryData,
    *,
    trial: DashboardTrialOperationData | None = None,
    defect_confirmation_groups: list[dict[str, object]] | None = None,
) -> str:
    def _lines(items: list[str]) -> list[str]:
        return [f"- {item}" for item in items] if items else ["- 暂无"]

    def _distribution_lines(title: str, distribution: dict[str, int]) -> list[str]:
        if not distribution:
            return [f"- {title}: 暂无"]
        ordered = sorted(distribution.items(), key=lambda item: (-int(item[1] or 0), str(item[0])))
        return [f"- {title}: " + "，".join(f"{key}: {value}" for key, value in ordered)]

    def _cluster_lines() -> list[str]:
        if trial is None or not trial.topDefectClusters:
            return ["- Top 聚类：暂无"]
        lines: list[str] = []
        for item in trial.topDefectClusters[:5]:
            samples = "；".join(item.sampleTitles[:2]) if item.sampleTitles else "暂无样例"
            lines.append(
                f"- {item.clusterKey}: {item.count} 条，置信度 {item.confidence:.0%}，提示：{item.rootCauseHint}，样例：{samples}"
            )
        return lines

    def _risk_hint_lines() -> list[str]:
        if trial is None or not trial.topRiskHints:
            return ["- Top 风险：暂无"]
        return [
            f"- [{item.severity}/{item.status}] {item.title}，风险分 {item.riskScore:g}，提示：{item.hint}"
            for item in trial.topRiskHints[:5]
        ]

    def _confirmation_group_lines() -> list[str]:
        if not defect_confirmation_groups:
            return ["- 暂无未关闭缺陷确认分组。"]
        lines = ["| 分类 | 数量 | 默认确认口径 | 样例 |", "| --- | ---: | --- | --- |"]
        for item in defect_confirmation_groups:
            samples = item.get("samples")
            sample_text = "；".join(str(sample) for sample in samples[:2]) if isinstance(samples, list) and samples else "-"
            lines.append(
                f"| {item.get('label', '-')} | {int(item.get('count', 0) or 0)} | {item.get('decision', '-')} | {sample_text} |"
            )
        return lines

    checks_by_key = {item.key: item for item in summary.checks}
    real_data = checks_by_key.get("realData")
    external_systems = checks_by_key.get("externalSystems")
    ops_health = checks_by_key.get("opsHealth")
    real_data_blocked = real_data is not None and real_data.status == "BLOCKED"
    platform_ready = all(
        item is not None and item.status == "READY"
        for item in (external_systems, ops_health)
    )
    if summary.overallStatus == "READY":
        stage_decision = "可进入正式验收"
        stage_scope = "全量验收域已就绪。"
    elif real_data_blocked and platform_ready:
        stage_decision = "阶段验收暂缓，可做有条件放行评审"
        stage_scope = "外部系统联调与运维健康已就绪；真实数据生产验收仍暂缓。"
    else:
        stage_decision = "阶段验收暂缓"
        stage_scope = "仍存在平台联调、运维健康或真实数据阻塞项。"

    defects = int(summary.metrics.get("defects", 0) or 0)
    risk_hints = int(summary.metrics.get("riskHints", 0) or 0)
    executed_case_runs = int(summary.metrics.get("executedCaseRuns", 0) or 0)
    exit_criteria = [
        "完成 P0/阻塞缺陷清单确认，并关闭或形成带审批的豁免记录。",
        "补齐核心链路真实执行结果，确保关键用例有可追溯回执。",
        "复跑生产验收中心，确认 realData 不再阻塞或完成有条件放行签署。",
    ]
    if defects > 0:
        exit_criteria.insert(0, f"处理当前缺陷：{defects} 条，优先收敛阻塞和高风险项。")
    if risk_hints > 0:
        exit_criteria.insert(1, f"复核风险提示：{risk_hints} 条，标记重复、历史或可豁免项。")
    defect_severity_distribution = dict(trial.defectSeverityDistribution or {}) if trial else {}
    defect_status_distribution = dict(trial.defectStatusDistribution or {}) if trial else {}
    blocking_questions = [
        f"{defects} 个未关闭缺陷是否都属于当前验收范围？" if defects else "当前缺陷范围是否已由需求方确认？",
        "P0 是否必须清零作为放行硬门槛？",
        "哪些缺陷是历史遗留、重复或已修未关，可进入延期/豁免白名单？",
        "P1/P2/P3 是否允许分批处理，审批人和截止日期分别是谁？",
        "动态、直播间、媒体日志等高频聚类是否需要指定专项 owner？",
    ]

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
            "## 阶段验收结论",
            f"- 决策：{stage_decision}",
            f"- 范围：{stage_scope}",
            f"- 说明：本报告不伪造通过结论，真实数据阻塞项需按退出条件闭环。",
            "",
            "## 真实数据",
            *[f"- {key}: {value}" for key, value in summary.metrics.items()],
            "",
            "## 有条件放行前置条件",
            f"- 已执行用例：{executed_case_runs}",
            *[f"- {item}" for item in exit_criteria[:6]],
            "",
            "## 阻塞缺陷治理清单",
            *_distribution_lines("严重级别分布", defect_severity_distribution),
            *_distribution_lines("状态分布", defect_status_distribution),
            f"- 未关闭缺陷：{defects}",
            f"- 风险提示：{risk_hints}",
            "### Top 缺陷聚类",
            *_cluster_lines(),
            "### Top 风险提示",
            *_risk_hint_lines(),
            "",
            "## 默认验收确认口径",
            "- 说明：以下为系统按保守规则自动分组，用于减少人工梳理成本；最终放行仍需需求方/测试负责人确认。",
            *_confirmation_group_lines(),
            "",
            "## 需需求方确认",
            *_lines(blocking_questions),
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
    trial = await get_dashboard_trial_operation(db, user=user, project_id=project_id)
    defect_confirmation_groups = _build_defect_confirmation_groups(
        await _load_open_defects_for_confirmation(db, user=user, project_id=project_id)
    )
    return AcceptanceReportData(
        title="生产验收中心报告",
        generatedAt=summary.generatedAt,
        summary=summary,
        markdown=_render_report_markdown(summary, trial=trial, defect_confirmation_groups=defect_confirmation_groups),
    )
