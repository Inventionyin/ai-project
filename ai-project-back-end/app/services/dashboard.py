from __future__ import annotations

import uuid

from datetime import date, datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, to_unix_ts
from app.models.audit import AuditLog
from app.models.enums import CaseRunStatus, Priority, ProjectRole, RunStatus
from app.models.defect import Defect
from app.models.project import Project, ProjectMember
from app.models.run import CaseRun, Run
from app.models.suite import Suite
from app.models.testcase import TestCase
from app.models.requirement import RequirementDoc
from app.schemas.dashboard import (
    DashboardFailureTopData,
    DashboardFailureTopSuiteItem,
    DashboardFailureTopTestcaseItem,
    DashboardQualityGateData,
    DashboardQualityGateItem,
    DashboardSummaryData,
    DashboardTrialOperationAcceptanceSummary,
    DashboardTrialOperationData,
    DashboardTrialOperationReportData,
    DashboardTrialOperationReportSnapshotCreateRequest,
    DashboardTrialOperationReportSnapshotData,
    DashboardTrendData,
    DashboardTrendItem,
)
from app.services.defect import list_defect_clusters, list_defect_risk_hints


_TRIAL_OPERATION_REPORT_SNAPSHOT_MODULE = "trial-operation-report"
_TRIAL_OPERATION_REPORT_SNAPSHOT_ACTION = "SNAPSHOT_REPORT"
_TRIAL_OPERATION_REPORT_SNAPSHOT_RESOURCE_TYPE = "trial_operation_report_snapshot"


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


async def _get_project(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> Project:
    project = await db.scalar(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_member_role(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> ProjectRole | None:
    return (
        await db.execute(
            select(ProjectMember.role).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user.id,
                ProjectMember.tenant_id == user.tenant_id,
            )
        )
    ).scalar_one_or_none()


async def _require_project_read(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = await _get_member_role(db, user=user, project_id=project.id)
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER):
        return
    raise HTTPException(status_code=403, detail="No access to this project")


async def get_dashboard_summary(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    target_date: date | None,
) -> DashboardSummaryData:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    summary_date = target_date or datetime.utcnow().date()
    day_start = datetime.combine(summary_date, time.min)
    day_end = day_start + timedelta(days=1)

    rows = (
        await db.execute(
            select(Run.status, func.count(Run.id))
            .join(Project, Run.project_id == Project.id)
            .outerjoin(
                ProjectMember,
                and_(
                    ProjectMember.project_id == Project.id,
                    ProjectMember.user_id == user.id,
                    ProjectMember.tenant_id == user.tenant_id,
                ),
            )
            .where(
                Run.tenant_id == user.tenant_id,
                Run.project_id == project.id,
                Run.start_at >= day_start,
                Run.start_at < day_end,
            )
            .where(
                or_(
                    _is_admin(user),
                    Project.owner_id == user.id,
                    ProjectMember.role.in_((ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER)),
                )
            )
            .group_by(Run.status)
        )
    ).all()

    counters = {status: int(count or 0) for status, count in rows}
    passed_runs = counters.get(RunStatus.PASSED, 0)
    failed_runs = counters.get(RunStatus.FAILED, 0)
    running_runs = counters.get(RunStatus.RUNNING, 0) + counters.get(RunStatus.QUEUED, 0)
    canceled_runs = counters.get(RunStatus.CANCELED, 0)
    total_runs = passed_runs + failed_runs + running_runs + canceled_runs

    finished_runs = passed_runs + failed_runs
    pass_rate = round((passed_runs / finished_runs) * 100, 1) if finished_runs > 0 else 0.0

    return DashboardSummaryData(
        date=summary_date.isoformat(),
        totalRuns=total_runs,
        passedRuns=passed_runs,
        failedRuns=failed_runs,
        runningRuns=running_runs,
        canceledRuns=canceled_runs,
        passRate=pass_rate,
    )


def _normalize_dimension(dimension: str | None) -> str:
    normalized = (dimension or "testcase").strip().lower()
    if not normalized:
        return "testcase"
    if normalized not in ("testcase", "suite"):
        raise HTTPException(status_code=422, detail="dimension must be testcase or suite")
    return normalized


def _normalize_trend_days(days: int) -> int:
    if days not in (7, 14, 30):
        raise HTTPException(status_code=422, detail="days must be one of 7, 14, 30")
    return days


def _to_iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.replace(microsecond=0).isoformat() + "Z"


def _format_percent(value: float) -> str:
    rounded = round(value, 1)
    if rounded.is_integer():
        return f"{int(rounded)}%"
    return f"{rounded:.1f}%"


def _enum_key(value: object) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "未填写")


async def _count_rows(db: AsyncSession, model: object, *, tenant_id: uuid.UUID, project_id: uuid.UUID) -> int:
    return int(
        (
            await db.execute(
                select(func.count())
                .select_from(model)
                .where(model.tenant_id == tenant_id, model.project_id == project_id)
            )
        ).scalar_one()
        or 0
    )


async def _distribution(
    db: AsyncSession,
    field: object,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    limit: int | None = None,
) -> dict[str, int]:
    stmt = (
        select(field, func.count())
        .where(field.class_.tenant_id == tenant_id, field.class_.project_id == project_id)
        .group_by(field)
        .order_by(func.count().desc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    rows = (await db.execute(stmt)).all()
    return {_enum_key(key): int(count or 0) for key, count in rows}


def _build_unknown_quality_gate() -> DashboardQualityGateData:
    return DashboardQualityGateData(
        overall="UNKNOWN",
        lastCheckedAt=None,
        linkedRunId=None,
        gates=[
            DashboardQualityGateItem(name="整体通过率", threshold="≥90%", current="N/A", passed=False),
            DashboardQualityGateItem(name="P0 用例全通过", threshold="100%", current="N/A", passed=False),
            DashboardQualityGateItem(name="关键路径通过率", threshold="≥95%", current="N/A", passed=False),
            DashboardQualityGateItem(name="平均响应时间", threshold="≤2000ms", current="N/A", passed=False),
        ],
    )


async def _get_testcase_suite_names(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    testcase_ids: list[uuid.UUID],
    since_at: datetime,
) -> dict[uuid.UUID, list[str]]:
    if not testcase_ids:
        return {}
    rows = (
        await db.execute(
            select(CaseRun.testcase_id, Suite.name)
            .join(Run, Run.id == CaseRun.run_id)
            .join(Suite, Suite.id == Run.suite_id)
            .where(
                CaseRun.tenant_id == tenant_id,
                Run.tenant_id == tenant_id,
                Run.project_id == project_id,
                Run.start_at >= since_at,
                CaseRun.testcase_id.in_(testcase_ids),
            )
            .distinct()
        )
    ).all()
    mapping: dict[uuid.UUID, set[str]] = {}
    for testcase_id, suite_name in rows:
        mapping.setdefault(testcase_id, set()).add(suite_name)
    return {testcase_id: sorted(names) for testcase_id, names in mapping.items()}


async def _get_failure_top_testcase(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    since_at: datetime,
    limit: int,
) -> DashboardFailureTopData:
    failed_expr = case((CaseRun.status == CaseRunStatus.FAILED, 1), else_=0)
    passed_expr = case((CaseRun.status == CaseRunStatus.PASSED, 1), else_=0)
    rows = (
        await db.execute(
            select(
                TestCase.id,
                TestCase.title,
                func.sum(failed_expr).label("fail_count"),
                func.count(CaseRun.id).label("total_count"),
                func.sum(passed_expr).label("pass_count"),
            )
            .join(CaseRun, CaseRun.testcase_id == TestCase.id)
            .join(Run, Run.id == CaseRun.run_id)
            .where(
                TestCase.tenant_id == tenant_id,
                TestCase.project_id == project_id,
                Run.tenant_id == tenant_id,
                Run.project_id == project_id,
                Run.start_at >= since_at,
            )
            .group_by(TestCase.id, TestCase.title)
            .order_by(func.sum(failed_expr).desc(), func.count(CaseRun.id).desc(), TestCase.title.asc())
            .limit(limit)
        )
    ).all()
    testcase_ids = [row.id for row in rows]
    suite_names_by_testcase = await _get_testcase_suite_names(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        testcase_ids=testcase_ids,
        since_at=since_at,
    )
    items = [
        DashboardFailureTopTestcaseItem(
            id=str(row.id),
            name=row.title,
            failCount=int(row.fail_count or 0),
            totalRuns=int(row.total_count or 0),
            flake=bool((row.fail_count or 0) > 0 and (row.pass_count or 0) > 0),
            suiteNames=suite_names_by_testcase.get(row.id, []),
        )
        for row in rows
    ]
    return DashboardFailureTopData(dimension="testcase", items=items)


async def _get_failure_top_suite(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    since_at: datetime,
    limit: int,
) -> DashboardFailureTopData:
    failed_expr = case((CaseRun.status == CaseRunStatus.FAILED, 1), else_=0)
    rows = (
        await db.execute(
            select(
                Suite.id,
                Suite.name,
                func.sum(failed_expr).label("fail_count"),
                func.count(func.distinct(Run.id)).label("total_runs"),
                func.max(Run.start_at).label("last_run_at"),
            )
            .join(Run, Run.suite_id == Suite.id)
            .join(CaseRun, CaseRun.run_id == Run.id)
            .where(
                Suite.tenant_id == tenant_id,
                Suite.project_id == project_id,
                Run.tenant_id == tenant_id,
                Run.project_id == project_id,
                Run.start_at >= since_at,
            )
            .group_by(Suite.id, Suite.name)
            .order_by(func.sum(failed_expr).desc(), func.count(func.distinct(Run.id)).desc(), Suite.name.asc())
            .limit(limit)
        )
    ).all()
    items = [
        DashboardFailureTopSuiteItem(
            id=str(row.id),
            name=row.name,
            failCount=int(row.fail_count or 0),
            totalRuns=int(row.total_runs or 0),
            lastRunAt=_to_iso_utc(row.last_run_at),
        )
        for row in rows
    ]
    return DashboardFailureTopData(dimension="suite", items=items)


async def get_dashboard_failure_top(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    dimension: str | None,
    days: int,
    limit: int,
) -> DashboardFailureTopData:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    normalized_dimension = _normalize_dimension(dimension)
    since_at = datetime.utcnow() - timedelta(days=days)

    if normalized_dimension == "suite":
        return await _get_failure_top_suite(
            db,
            tenant_id=user.tenant_id,
            project_id=project.id,
            since_at=since_at,
            limit=limit,
        )
    return await _get_failure_top_testcase(
        db,
        tenant_id=user.tenant_id,
        project_id=project.id,
        since_at=since_at,
        limit=limit,
    )


async def get_dashboard_trend(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    days: int,
) -> DashboardTrendData:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    normalized_days = _normalize_trend_days(days)
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=normalized_days - 1)
    start_at = datetime.combine(start_date, time.min)
    end_at = datetime.combine(today + timedelta(days=1), time.min)

    rows = (
        await db.execute(
            select(func.date(Run.start_at), Run.status, func.count(Run.id))
            .where(
                Run.tenant_id == user.tenant_id,
                Run.project_id == project.id,
                Run.start_at >= start_at,
                Run.start_at < end_at,
            )
            .group_by(func.date(Run.start_at), Run.status)
        )
    ).all()

    counters_by_day: dict[date, dict[RunStatus, int]] = {}
    for day_value, status, count in rows:
        if day_value is None:
            continue
        day_counters = counters_by_day.setdefault(day_value, {})
        day_counters[status] = int(count or 0)

    items: list[DashboardTrendItem] = []
    for offset in range(normalized_days):
        current_date = start_date + timedelta(days=offset)
        counters = counters_by_day.get(current_date, {})
        passed = counters.get(RunStatus.PASSED, 0)
        failed = counters.get(RunStatus.FAILED, 0)
        total_runs = sum(counters.values())
        finished = passed + failed
        pass_rate = round((passed / finished) * 100, 1) if finished > 0 else 0.0
        items.append(
            DashboardTrendItem(
                date=current_date.strftime("%m-%d"),
                passRate=pass_rate,
                failCount=failed,
                totalRuns=total_runs,
            )
        )
    return DashboardTrendData(days=normalized_days, items=items)


async def get_dashboard_quality_gate(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> DashboardQualityGateData:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    latest_run = await db.scalar(
        select(Run)
        .where(
            Run.tenant_id == user.tenant_id,
            Run.project_id == project.id,
            Run.status.in_((RunStatus.PASSED, RunStatus.FAILED, RunStatus.CANCELED)),
        )
        .order_by(Run.start_at.desc().nullslast(), Run.created_at.desc())
        .limit(1)
    )
    if latest_run is None:
        return _build_unknown_quality_gate()

    rows = (
        await db.execute(
            select(
                CaseRun.status,
                CaseRun.metrics_json,
                CaseRun.start_at,
                CaseRun.end_at,
                TestCase.priority,
                TestCase.tags_json,
            )
            .join(TestCase, TestCase.id == CaseRun.testcase_id)
            .where(
                CaseRun.tenant_id == user.tenant_id,
                CaseRun.run_id == latest_run.id,
                TestCase.tenant_id == user.tenant_id,
                TestCase.project_id == project.id,
            )
        )
    ).all()

    total_finished = 0
    total_passed = 0
    p0_finished = 0
    p0_passed = 0
    critical_finished = 0
    critical_passed = 0
    duration_values: list[int] = []
    critical_tags = {"critical", "关键路径", "keypath", "key-path"}

    for status, metrics_json, start_at, end_at, priority, tags_json in rows:
        is_passed = status == CaseRunStatus.PASSED
        is_failed = status == CaseRunStatus.FAILED
        is_finished = is_passed or is_failed
        if is_finished:
            total_finished += 1
            if is_passed:
                total_passed += 1

        if priority == Priority.P0 and is_finished:
            p0_finished += 1
            if is_passed:
                p0_passed += 1

        normalized_tags = {str(tag).strip().lower() for tag in (tags_json or []) if str(tag).strip()}
        is_critical = bool(normalized_tags & critical_tags)
        if is_critical and is_finished:
            critical_finished += 1
            if is_passed:
                critical_passed += 1

        duration_ms: int | None = None
        if isinstance(metrics_json, dict):
            raw_duration = metrics_json.get("durationMs")
            if isinstance(raw_duration, (int, float)) and raw_duration >= 0:
                duration_ms = int(raw_duration)
        if duration_ms is None and start_at is not None and end_at is not None and end_at >= start_at:
            duration_ms = int((end_at - start_at).total_seconds() * 1000)
        if duration_ms is not None:
            duration_values.append(duration_ms)

    total_pass_rate = (total_passed / total_finished * 100) if total_finished > 0 else None
    p0_pass_rate = (p0_passed / p0_finished * 100) if p0_finished > 0 else None
    critical_pass_rate = (critical_passed / critical_finished * 100) if critical_finished > 0 else None
    avg_duration = (sum(duration_values) / len(duration_values)) if duration_values else None

    gates = [
        DashboardQualityGateItem(
            name="整体通过率",
            threshold="≥90%",
            current=_format_percent(total_pass_rate) if total_pass_rate is not None else "N/A",
            passed=bool(total_pass_rate is not None and total_pass_rate >= 90),
        ),
        DashboardQualityGateItem(
            name="P0 用例全通过",
            threshold="100%",
            current=_format_percent(p0_pass_rate) if p0_pass_rate is not None else "N/A",
            passed=bool(p0_pass_rate is None or p0_pass_rate >= 100),
        ),
        DashboardQualityGateItem(
            name="关键路径通过率",
            threshold="≥95%",
            current=_format_percent(critical_pass_rate) if critical_pass_rate is not None else "N/A",
            passed=bool(critical_pass_rate is None or critical_pass_rate >= 95),
        ),
        DashboardQualityGateItem(
            name="平均响应时间",
            threshold="≤2000ms",
            current=f"{round(avg_duration)}ms" if avg_duration is not None else "N/A",
            passed=bool(avg_duration is not None and avg_duration <= 2000),
        ),
    ]
    effective_gates = [gate for gate in gates if gate.current != "N/A"]
    if not effective_gates:
        overall = "UNKNOWN"
    elif all(gate.passed for gate in effective_gates):
        overall = "PASSED"
    elif any(gate.passed for gate in effective_gates):
        overall = "PARTIAL_FAIL"
    else:
        overall = "FAILED"

    checked_at = latest_run.end_at or latest_run.start_at or latest_run.created_at
    return DashboardQualityGateData(
        overall=overall,
        lastCheckedAt=to_unix_ts(checked_at) if checked_at else None,
        linkedRunId=str(latest_run.id),
        gates=gates,
    )


async def get_dashboard_trial_operation(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> DashboardTrialOperationData:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    requirement_docs = await _count_rows(db, RequirementDoc, tenant_id=user.tenant_id, project_id=project.id)
    testcases = await _count_rows(db, TestCase, tenant_id=user.tenant_id, project_id=project.id)
    defects = await _count_rows(db, Defect, tenant_id=user.tenant_id, project_id=project.id)

    clusters = await list_defect_clusters(db, user=user, project_id=project.id)
    risk_hints = await list_defect_risk_hints(db, user=user, project_id=project.id)

    sample_rows = (
        await db.execute(
            select(TestCase.title)
            .where(TestCase.tenant_id == user.tenant_id, TestCase.project_id == project.id)
            .order_by(TestCase.updated_at.desc().nullslast(), TestCase.id.desc())
            .limit(8)
        )
    ).all()

    defect_severity_distribution = await _distribution(
        db, Defect.severity, tenant_id=user.tenant_id, project_id=project.id
    )
    acceptance_summary = _build_trial_operation_acceptance_summary(
        metrics={
            "requirementDocs": requirement_docs,
            "testcases": testcases,
            "defects": defects,
            "defectClusters": len(clusters),
            "riskHints": len(risk_hints),
        },
        defect_severity_distribution=defect_severity_distribution,
    )

    return DashboardTrialOperationData(
        metrics={
            "requirementDocs": requirement_docs,
            "testcases": testcases,
            "defects": defects,
            "defectClusters": len(clusters),
            "riskHints": len(risk_hints),
        },
        testcasePriorityDistribution=await _distribution(
            db, TestCase.priority, tenant_id=user.tenant_id, project_id=project.id
        ),
        testcaseStatusDistribution=await _distribution(
            db, TestCase.status, tenant_id=user.tenant_id, project_id=project.id
        ),
        testcaseTypeDistribution=await _distribution(
            db, TestCase.type, tenant_id=user.tenant_id, project_id=project.id
        ),
        testcaseFeatureDistribution=await _distribution(
            db, TestCase.feature, tenant_id=user.tenant_id, project_id=project.id, limit=16
        ),
        defectSeverityDistribution=defect_severity_distribution,
        defectStatusDistribution=await _distribution(
            db, Defect.status, tenant_id=user.tenant_id, project_id=project.id
        ),
        topDefectClusters=[item.model_dump() for item in clusters[:8]],
        topRiskHints=[item.model_dump() for item in risk_hints[:8]],
        sampleTestcases=[str(row[0]) for row in sample_rows if row and row[0]],
        acceptanceSummary=acceptance_summary,
    )


def _build_trial_operation_acceptance_summary(
    *,
    metrics: dict[str, int],
    defect_severity_distribution: dict[str, int],
) -> DashboardTrialOperationAcceptanceSummary:
    requirement_docs = int(metrics.get("requirementDocs", 0) or 0)
    testcases = int(metrics.get("testcases", 0) or 0)
    defects = int(metrics.get("defects", 0) or 0)
    risk_hints = int(metrics.get("riskHints", 0) or 0)
    p0_defects = int(defect_severity_distribution.get("P0", 0) or 0)

    highlights = [
        f"已纳入 {testcases} 条测试用例",
        f"覆盖 {requirement_docs} 份需求文档",
        f"已汇总 {defects} 条缺陷记录",
    ]

    risks: list[str] = []
    next_actions: list[str] = []
    if p0_defects > 0:
        risks.append(f"仍有 {p0_defects} 个 P0 缺陷未关闭")
        next_actions.append("优先关闭 P0 缺陷并补充回归")
    if risk_hints > 20:
        risks.append(f"当前风险提示总量 {risk_hints} 条")
        next_actions.append("按风险提示清单推进修复验收")

    if testcases == 0 or requirement_docs == 0:
        score = 30 if (testcases > 0 or requirement_docs > 0) else 0
        return DashboardTrialOperationAcceptanceSummary(
            conclusion="数据不足",
            score=score,
            level="INSUFFICIENT",
            highlights=highlights[:3],
            risks=(risks + ["需求文档或测试用例基线不足"])[:4],
            nextActions=(next_actions + ["补充需求文档和测试用例后再评审"])[:4],
        )

    if p0_defects > 0:
        score = max(50, 72 - min(p0_defects, 10))
        level = "BLOCKED" if p0_defects >= 5 else "WARNING"
        conclusion = "建议暂缓" if level == "BLOCKED" else "建议谨慎通过"
        return DashboardTrialOperationAcceptanceSummary(
            conclusion=conclusion,
            score=score,
            level=level,
            highlights=highlights[:3],
            risks=risks[:4],
            nextActions=(next_actions + ["明确修复完成标准与复测窗口"])[:4],
        )

    if risk_hints > 20:
        score = max(50, 79 - min((risk_hints - 20) // 5, 15))
        return DashboardTrialOperationAcceptanceSummary(
            conclusion="建议谨慎通过",
            score=score,
            level="WARNING",
            highlights=highlights[:3],
            risks=risks[:4],
            nextActions=(next_actions + ["按风险等级拆分治理责任人"])[:4],
        )

    score = 88 + min(12, requirement_docs // 20 + testcases // 300)
    return DashboardTrialOperationAcceptanceSummary(
        conclusion="建议通过",
        score=min(100, score),
        level="PASS",
        highlights=highlights[:3],
        risks=[],
        nextActions=["持续跟踪新增缺陷与回归结果", "保持需求与用例字段完整性"][:4],
    )


def _render_trial_operation_report_markdown(data: DashboardTrialOperationData) -> str:
    def _lines(items: list[str], *, limit: int | None = None) -> list[str]:
        picked = items[:limit] if limit is not None else items
        if not picked:
            return ["- 暂无"]
        return [f"- {item}" for item in picked]

    metrics = data.metrics
    summary = data.acceptanceSummary
    cluster_lines = [
        f"- {item.clusterKey}: {item.count}（置信度 {round(item.confidence * 100)}%）"
        for item in data.topDefectClusters[:5]
    ] or ["- 暂无"]
    risk_hint_lines = [
        f"- [{item.severity}] {item.title}（风险分 {item.riskScore:.1f}）"
        for item in data.topRiskHints[:5]
    ] or ["- 暂无"]

    lines: list[str] = [
        "# WeiTesting 真实数据试运行验收报告",
        "",
        "## 结论",
        f"- 结论：{summary.conclusion}",
        f"- 评分：{summary.score}",
        f"- 等级：{summary.level}",
        "",
        "## 核心数据",
        f"- 需求文档：{int(metrics.get('requirementDocs', 0) or 0)}",
        f"- 测试用例：{int(metrics.get('testcases', 0) or 0)}",
        f"- 缺陷：{int(metrics.get('defects', 0) or 0)}",
        f"- 缺陷聚类：{int(metrics.get('defectClusters', 0) or 0)}",
        f"- 风险提示：{int(metrics.get('riskHints', 0) or 0)}",
        "",
        "### 缺陷聚类（Top）",
        *cluster_lines,
        "",
        "### 风险提示（Top）",
        *risk_hint_lines,
        "",
        "## 亮点",
        *_lines(summary.highlights),
        "",
        "## 风险",
        *_lines(summary.risks),
        "",
        "## 下一步",
        *_lines(summary.nextActions),
        "",
        "## 样例用例",
        *_lines(data.sampleTestcases, limit=5),
    ]
    return "\n".join(lines)


async def get_dashboard_trial_operation_report(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> DashboardTrialOperationReportData:
    trial_data = await get_dashboard_trial_operation(db, user=user, project_id=project_id)
    return DashboardTrialOperationReportData(
        title="WeiTesting 真实数据试运行验收报告",
        generatedAt=to_unix_ts(datetime.utcnow()),
        markdown=_render_trial_operation_report_markdown(trial_data),
        summary=trial_data.acceptanceSummary,
    )


def _to_trial_operation_report_snapshot(row: AuditLog) -> DashboardTrialOperationReportSnapshotData:
    detail = dict(row.detail_json or {})
    summary = dict(detail.get("summary") or {})
    score = detail.get("score", detail.get("acceptanceScore"))
    level = detail.get("level", detail.get("acceptanceLevel"))
    return DashboardTrialOperationReportSnapshotData(
        id=str(row.id),
        projectId=str(row.project_id) if row.project_id else None,
        title=str(detail.get("title") or row.summary or "WeiTesting 真实数据试运行验收报告"),
        generatedAt=int(detail.get("generatedAt") or 0),
        markdown=str(detail.get("markdown") or ""),
        summary=summary,
        score=score,
        level=level,
        acceptanceScore=score,
        acceptanceLevel=level,
        createdBy=str(row.user_id) if row.user_id else None,
        createdAt=to_unix_ts(row.created_at),
    )


def _trial_operation_report_snapshot_detail(report: DashboardTrialOperationReportData) -> dict:
    payload = report.model_dump()
    summary = payload.get("summary") or {}
    payload["score"] = summary.get("score")
    payload["level"] = summary.get("level")
    payload["acceptanceScore"] = payload["score"]
    payload["acceptanceLevel"] = payload["level"]
    return payload


async def create_dashboard_trial_operation_report_snapshot(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    payload: DashboardTrialOperationReportSnapshotCreateRequest | None = None,
) -> DashboardTrialOperationReportSnapshotData:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    report = payload or await get_dashboard_trial_operation_report(db, user=user, project_id=project_id)
    detail = _trial_operation_report_snapshot_detail(report)
    row = AuditLog(
        tenant_id=user.tenant_id,
        project_id=project.id,
        user_id=user.id,
        module=_TRIAL_OPERATION_REPORT_SNAPSHOT_MODULE,
        action=_TRIAL_OPERATION_REPORT_SNAPSHOT_ACTION,
        resource_type=_TRIAL_OPERATION_REPORT_SNAPSHOT_RESOURCE_TYPE,
        resource_id=str(uuid.uuid4()),
        summary=report.title,
        detail_json=detail,
    )
    db.add(row)
    await db.flush()
    return _to_trial_operation_report_snapshot(row)


async def list_dashboard_trial_operation_report_snapshots(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    page: int,
    page_size: int,
) -> tuple[int, list[DashboardTrialOperationReportSnapshotData]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    base_stmt = select(AuditLog).where(
        AuditLog.tenant_id == user.tenant_id,
        AuditLog.project_id == project.id,
        AuditLog.module == _TRIAL_OPERATION_REPORT_SNAPSHOT_MODULE,
        AuditLog.action == _TRIAL_OPERATION_REPORT_SNAPSHOT_ACTION,
        AuditLog.resource_type == _TRIAL_OPERATION_REPORT_SNAPSHOT_RESOURCE_TYPE,
    )
    total = int((await db.execute(select(func.count()).select_from(base_stmt.subquery()))).scalar_one() or 0)
    rows = (
        await db.execute(base_stmt.order_by(desc(AuditLog.created_at)).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    return total, [_to_trial_operation_report_snapshot(row) for row in rows]


async def get_dashboard_trial_operation_report_snapshot(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    snapshot_id: uuid.UUID,
) -> DashboardTrialOperationReportSnapshotData:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    row = await db.scalar(
        select(AuditLog).where(
            AuditLog.id == snapshot_id,
            AuditLog.tenant_id == user.tenant_id,
            AuditLog.project_id == project.id,
            AuditLog.module == _TRIAL_OPERATION_REPORT_SNAPSHOT_MODULE,
            AuditLog.action == _TRIAL_OPERATION_REPORT_SNAPSHOT_ACTION,
            AuditLog.resource_type == _TRIAL_OPERATION_REPORT_SNAPSHOT_RESOURCE_TYPE,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="trial_operation_report_snapshot_not_found")
    return _to_trial_operation_report_snapshot(row)
