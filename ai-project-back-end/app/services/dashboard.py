from __future__ import annotations

import uuid

from datetime import date, datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, to_unix_ts
from app.models.audit import AuditLog
from app.models.enums import CaseRunStatus, Priority, ProjectRole, RunStatus, TestCaseStatus, TriggerType
from app.models.defect import Defect
from app.models.project import Project, ProjectMember
from app.models.run import CaseRun, Run
from app.models.suite import Suite
from app.models.testcase import TestCase
from app.models.requirement import RequirementDoc
from app.schemas.dashboard import (
    DashboardCaseGovernanceData,
    DashboardCaseGovernanceDuplicateTitleItem,
    DashboardCaseGovernanceLowValueItem,
    DashboardCaseGovernanceModuleP0DensityItem,
    DashboardFailureTopData,
    DashboardFailureTopSuiteItem,
    DashboardFailureTopTestcaseItem,
    DashboardQualityGateData,
    DashboardQualityGateItem,
    DashboardSummaryData,
    DashboardTrialOperationExecutionImportData,
    DashboardTrialOperationExecutionImportRequest,
    DashboardTrialOperationAcceptanceSummary,
    DashboardTrialOperationData,
    DashboardTrialOperationGovernanceApplyData,
    DashboardTrialOperationGovernanceApplyRequest,
    DashboardTrialOperationGovernanceHistoryData,
    DashboardTrialOperationGovernanceHistoryItem,
    DashboardTrialOperationGovernanceSuggestionBatch,
    DashboardTrialOperationGovernanceSuggestionItem,
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
_TRIAL_OPERATION_GOVERNANCE_MODULE = "trial-operation-governance"
_TRIAL_OPERATION_GOVERNANCE_BATCH_ACTION = "GENERATE_SUGGESTIONS"
_TRIAL_OPERATION_GOVERNANCE_APPLY_ACTION = "APPLY_SUGGESTIONS"


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


async def _require_project_write(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = await _get_member_role(db, user=user, project_id=project.id)
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR):
        return
    raise HTTPException(status_code=403, detail="No write access to this project")


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
    executed_case_runs = int(
        (
            await db.execute(
                select(func.count(CaseRun.id))
                .join(Run, Run.id == CaseRun.run_id)
                .where(
                    Run.tenant_id == user.tenant_id,
                    Run.project_id == project.id,
                    CaseRun.tenant_id == user.tenant_id,
                    CaseRun.status.in_((CaseRunStatus.PASSED, CaseRunStatus.FAILED, CaseRunStatus.SKIPPED)),
                )
            )
        ).scalar()
        or 0
    )

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
            "executedCaseRuns": executed_case_runs,
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
            "executedCaseRuns": executed_case_runs,
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


def _round_percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _low_value_reasons(row: object) -> list[str]:
    title = str(getattr(row, "title", "") or "").strip()
    feature = str(getattr(row, "feature", "") or "").strip()
    content = str(getattr(row, "content_md", "") or "").strip()
    expected_result = ""
    meta = getattr(row, "ai_meta_json", None)
    if isinstance(meta, dict):
        expected_result = str(meta.get("expectedResult") or "").strip()

    reasons: list[str] = []
    if len(title) <= 4 or title in {"无反应", "验证", "测试", "检查"}:
        reasons.append("标题过短或语义不完整")
    if not feature or feature == "未分组":
        reasons.append("模块缺失或未分组")
    if len(content) < 24:
        reasons.append("步骤描述过短")
    if len(expected_result) < 6:
        reasons.append("预期结果过短")
    return reasons


async def get_dashboard_case_governance(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> DashboardCaseGovernanceData:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    base_filter = (TestCase.tenant_id == user.tenant_id, TestCase.project_id == project.id)
    summary_row = (
        await db.execute(
            select(
                func.count(TestCase.id).label("total"),
                func.count(func.distinct(TestCase.test_case_id)).label("unique_case_ids"),
                func.sum(case((or_(TestCase.test_case_id.is_(None), func.trim(TestCase.test_case_id) == ""), 1), else_=0)).label("empty_case_ids"),
                func.sum(case((or_(TestCase.title.is_(None), func.trim(TestCase.title) == ""), 1), else_=0)).label("empty_titles"),
                func.sum(case((TestCase.priority == Priority.P0, 1), else_=0)).label("p0_cases"),
                func.sum(
                    case(
                        (
                            and_(
                                TestCase.test_case_id.is_not(None),
                                func.trim(TestCase.test_case_id) != "",
                                TestCase.test_case_id.notlike("TC_IMPORT_%"),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("source_case_ids"),
                func.sum(case((TestCase.test_case_id.like("TC_IMPORT_%"), 1), else_=0)).label("generated_import_ids"),
            ).where(*base_filter)
        )
    ).mappings().one()

    total_cases = int(summary_row["total"] or 0)
    p0_cases = int(summary_row["p0_cases"] or 0)
    source_case_ids = int(summary_row["source_case_ids"] or 0)
    generated_import_ids = int(summary_row["generated_import_ids"] or 0)

    duplicate_rows = (
        await db.execute(
            select(TestCase.title, func.count(TestCase.id).label("count"), func.array_agg(func.distinct(TestCase.feature)).label("modules"))
            .where(*base_filter, TestCase.title.is_not(None), func.trim(TestCase.title) != "")
            .group_by(TestCase.title)
            .having(func.count(TestCase.id) > 1)
            .order_by(func.count(TestCase.id).desc(), TestCase.title.asc())
            .limit(12)
        )
    ).mappings().all()

    module_p0_rows = (
        await db.execute(
            select(
                TestCase.feature,
                func.count(TestCase.id).label("total"),
                func.sum(case((TestCase.priority == Priority.P0, 1), else_=0)).label("p0"),
            )
            .where(*base_filter, TestCase.feature.is_not(None), func.trim(TestCase.feature) != "")
            .group_by(TestCase.feature)
            .order_by((func.sum(case((TestCase.priority == Priority.P0, 1), else_=0)) * 1.0 / func.count(TestCase.id)).desc(), func.count(TestCase.id).desc())
            .limit(12)
        )
    ).mappings().all()

    candidate_rows = (
        await db.execute(
            select(TestCase)
            .where(*base_filter)
            .order_by(TestCase.priority.desc(), TestCase.updated_at.desc().nullslast())
            .limit(600)
        )
    ).scalars().all()
    low_value_items: list[DashboardCaseGovernanceLowValueItem] = []
    for row in candidate_rows:
        reasons = _low_value_reasons(row)
        if not reasons:
            continue
        low_value_items.append(
            DashboardCaseGovernanceLowValueItem(
                id=str(row.id),
                testCaseId=row.test_case_id,
                title=row.title,
                feature=row.feature,
                priority=_enum_key(row.priority),
                type=_enum_key(row.type),
                reasons=reasons,
            )
        )
        if len(low_value_items) >= 12:
            break

    return DashboardCaseGovernanceData(
        totalCases=total_cases,
        uniqueCaseIds=int(summary_row["unique_case_ids"] or 0),
        sourceCaseIds=source_case_ids,
        formalCases=source_case_ids,
        testPointCases=max(0, total_cases - source_case_ids),
        generatedImportIds=generated_import_ids,
        emptyCaseIds=int(summary_row["empty_case_ids"] or 0),
        emptyTitles=int(summary_row["empty_titles"] or 0),
        p0Cases=p0_cases,
        p0Density=_round_percent(p0_cases, total_cases),
        typeDistribution=await _distribution(db, TestCase.type, tenant_id=user.tenant_id, project_id=project.id),
        priorityDistribution=await _distribution(db, TestCase.priority, tenant_id=user.tenant_id, project_id=project.id),
        moduleDistribution=await _distribution(db, TestCase.feature, tenant_id=user.tenant_id, project_id=project.id, limit=20),
        duplicateTitleCandidates=[
            DashboardCaseGovernanceDuplicateTitleItem(
                title=str(row["title"]),
                count=int(row["count"] or 0),
                modules=[str(item) for item in (row["modules"] or []) if item][:8],
            )
            for row in duplicate_rows
        ],
        lowValueCandidates=low_value_items,
        moduleP0Density=[
            DashboardCaseGovernanceModuleP0DensityItem(
                feature=str(row["feature"]),
                total=int(row["total"] or 0),
                p0=int(row["p0"] or 0),
                p0Density=_round_percent(int(row["p0"] or 0), int(row["total"] or 0)),
            )
            for row in module_p0_rows
        ],
    )


async def _select_testcases_by_ids(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    ids: list[str],
) -> list[TestCase]:
    parsed: list[uuid.UUID] = []
    for value in ids:
        try:
            parsed.append(uuid.UUID(str(value)))
        except ValueError:
            continue
    if not parsed:
        return []
    rows = (
        await db.execute(
            select(TestCase).where(
                TestCase.tenant_id == tenant_id,
                TestCase.project_id == project_id,
                TestCase.id.in_(parsed),
            )
        )
    ).scalars().all()
    return list(rows)


async def _build_trial_operation_governance_suggestion_items(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    applied_fingerprints: set[str] | None = None,
) -> list[DashboardTrialOperationGovernanceSuggestionItem]:
    governance = await get_dashboard_case_governance(db, user=user, project_id=project_id)
    items: list[DashboardTrialOperationGovernanceSuggestionItem] = []
    applied = applied_fingerprints or set()

    def _fingerprint(action: str, ids: list[str]) -> str:
        return f"{action}:{','.join(sorted(str(item) for item in ids))}"

    def _append_if_new(item: DashboardTrialOperationGovernanceSuggestionItem) -> None:
        if _fingerprint(item.action, item.targetIds) in applied:
            return
        items.append(item)

    duplicate_rows = (
        await db.execute(
            select(TestCase.title, func.array_agg(TestCase.id).label("ids"), func.count(TestCase.id).label("count"))
            .where(
                TestCase.tenant_id == user.tenant_id,
                TestCase.project_id == project_id,
                TestCase.title.is_not(None),
                func.trim(TestCase.title) != "",
            )
            .group_by(TestCase.title)
            .having(func.count(TestCase.id) > 1)
            .order_by(func.count(TestCase.id).desc(), TestCase.title.asc())
            .limit(8)
        )
    ).mappings().all()
    for index, row in enumerate(duplicate_rows, start=1):
        ids = [str(item) for item in (row["ids"] or []) if item]
        _append_if_new(
            DashboardTrialOperationGovernanceSuggestionItem(
                id=f"dup-{index}",
                category="DUPLICATE_TITLE",
                title=f"合并重复标题：{str(row['title'])[:40]}",
                severity="MEDIUM",
                targetIds=ids,
                targetCount=int(row["count"] or len(ids)),
                reason="同一标题出现多次，容易造成执行统计重复和维护成本增加",
                recommendation="保留一条主用例，其余标记为重复候选，后续人工确认是否合并或废弃",
                action="TAG_DUPLICATE",
                confidence=0.78,
                canApply=bool(ids),
            )
        )

    for index, item in enumerate(governance.lowValueCandidates[:10], start=1):
        _append_if_new(
            DashboardTrialOperationGovernanceSuggestionItem(
                id=f"low-{index}",
                category="LOW_VALUE",
                title=f"标记低价值候选：{item.title[:40]}",
                severity="LOW" if len(item.reasons) <= 1 else "MEDIUM",
                targetIds=[item.id],
                targetCount=1,
                reason="；".join(item.reasons),
                recommendation="先标记为低价值候选，补齐步骤、预期结果或后续从验收执行集中剔除",
                action="MARK_LOW_VALUE",
                confidence=0.72,
                canApply=True,
            )
        )

    promotable_rows = (
        await db.execute(
            select(TestCase)
            .where(
                TestCase.tenant_id == user.tenant_id,
                TestCase.project_id == project_id,
                TestCase.test_case_id.like("TC_IMPORT_%"),
                TestCase.priority.in_((Priority.P0, Priority.P1)),
            )
            .order_by(TestCase.priority.asc(), TestCase.updated_at.desc().nullslast())
            .limit(10)
        )
    ).scalars().all()
    for index, row in enumerate(promotable_rows, start=1):
        _append_if_new(
            DashboardTrialOperationGovernanceSuggestionItem(
                id=f"promote-{index}",
                category="PROMOTE_TEST_POINT",
                title=f"待转正式用例：{row.title[:40]}",
                severity="HIGH" if row.priority == Priority.P0 else "MEDIUM",
                targetIds=[str(row.id)],
                targetCount=1,
                reason="高优先级测试点仍使用平台补号，建议进入正式用例库",
                recommendation="标记为待转正式用例并进入评审，确认后补充源用例编号",
                action="PROMOTE_TO_FORMAL",
                confidence=0.8,
                canApply=True,
            )
        )

    for index, row in enumerate(governance.moduleP0Density[-6:], start=1):
        if row.total < 10 or row.p0Density >= 5:
            continue
        module_rows = (
            await db.execute(
                select(TestCase.id)
                .where(
                    TestCase.tenant_id == user.tenant_id,
                    TestCase.project_id == project_id,
                    TestCase.feature == row.feature,
                )
                .order_by(TestCase.updated_at.desc().nullslast())
                .limit(20)
            )
        ).scalars().all()
        ids = [str(item) for item in module_rows]
        _append_if_new(
            DashboardTrialOperationGovernanceSuggestionItem(
                id=f"p0-gap-{index}",
                category="P0_COVERAGE_GAP",
                title=f"P0 覆盖不足：{row.feature[:40]}",
                severity="HIGH",
                targetIds=ids,
                targetCount=row.total,
                reason=f"模块 {row.feature} 共 {row.total} 条资产，P0 占比仅 {row.p0Density}%",
                recommendation="给模块加 P0 评审标签，补充核心链路或提高关键用例优先级",
                action="ADD_P0_REVIEW_TAG",
                confidence=0.76,
                canApply=bool(ids),
            )
        )

    return items[:30]


async def _load_applied_governance_fingerprints(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> set[str]:
    rows = (
        await db.execute(
            select(AuditLog.detail_json)
            .where(
                AuditLog.tenant_id == user.tenant_id,
                AuditLog.project_id == project_id,
                AuditLog.module == _TRIAL_OPERATION_GOVERNANCE_MODULE,
                AuditLog.action == _TRIAL_OPERATION_GOVERNANCE_BATCH_ACTION,
            )
            .order_by(desc(AuditLog.created_at))
            .limit(20)
        )
    ).scalars().all()
    suggestions_by_batch: dict[str, dict[str, dict]] = {}
    for detail in rows:
        if not isinstance(detail, dict):
            continue
        batch_id = str(detail.get("batchId") or "")
        if not batch_id:
            continue
        suggestions_by_batch[batch_id] = {
            str(item.get("id") or ""): item
            for item in list(detail.get("items") or [])
            if isinstance(item, dict) and item.get("id")
        }

    apply_rows = (
        await db.execute(
            select(AuditLog.resource_id, AuditLog.detail_json)
            .where(
                AuditLog.tenant_id == user.tenant_id,
                AuditLog.project_id == project_id,
                AuditLog.module == _TRIAL_OPERATION_GOVERNANCE_MODULE,
                AuditLog.action == _TRIAL_OPERATION_GOVERNANCE_APPLY_ACTION,
            )
            .order_by(desc(AuditLog.created_at))
            .limit(50)
        )
    ).all()
    fingerprints: set[str] = set()
    for batch_id, detail in apply_rows:
        if not isinstance(detail, dict):
            continue
        suggestions = suggestions_by_batch.get(str(batch_id), {})
        for suggestion_id in list(detail.get("appliedSuggestionIds") or []):
            suggestion = suggestions.get(str(suggestion_id))
            if not suggestion:
                continue
            action = str(suggestion.get("action") or "")
            ids = [str(item) for item in list(suggestion.get("targetIds") or [])]
            if action and ids:
                fingerprints.add(f"{action}:{','.join(sorted(ids))}")
    return fingerprints


def _governance_summary(items: list[DashboardTrialOperationGovernanceSuggestionItem]) -> dict[str, int]:
    return {
        "duplicates": sum(1 for item in items if item.category == "DUPLICATE_TITLE"),
        "lowValue": sum(1 for item in items if item.category == "LOW_VALUE"),
        "promotableTestPoints": sum(1 for item in items if item.category == "PROMOTE_TEST_POINT"),
        "p0CoverageGaps": sum(1 for item in items if item.category == "P0_COVERAGE_GAP"),
        "total": len(items),
    }


async def generate_dashboard_trial_operation_governance_suggestions(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
) -> DashboardTrialOperationGovernanceSuggestionBatch:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    applied_fingerprints = await _load_applied_governance_fingerprints(db, user=user, project_id=project.id)
    items = await _build_trial_operation_governance_suggestion_items(
        db,
        user=user,
        project_id=project.id,
        applied_fingerprints=applied_fingerprints,
    )
    batch_id = f"gov-{uuid.uuid4().hex[:12]}"
    generated_at = datetime.utcnow()
    batch = DashboardTrialOperationGovernanceSuggestionBatch(
        batchId=batch_id,
        generatedAt=to_unix_ts(generated_at),
        source="HYBRID",
        summary=_governance_summary(items),
        items=items,
    )
    db.add(
        AuditLog(
            tenant_id=user.tenant_id,
            project_id=project.id,
            user_id=user.id,
            module=_TRIAL_OPERATION_GOVERNANCE_MODULE,
            action=_TRIAL_OPERATION_GOVERNANCE_BATCH_ACTION,
            resource_type="trial_operation_governance_batch",
            resource_id=batch_id,
            summary=f"生成试运行治理建议：{len(items)} 条",
            detail_json=batch.model_dump(mode="json"),
        )
    )
    await db.flush()
    return batch


async def _load_governance_batch(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    batch_id: str,
) -> DashboardTrialOperationGovernanceSuggestionBatch:
    row = await db.scalar(
        select(AuditLog)
        .where(
            AuditLog.tenant_id == user.tenant_id,
            AuditLog.project_id == project_id,
            AuditLog.module == _TRIAL_OPERATION_GOVERNANCE_MODULE,
            AuditLog.action == _TRIAL_OPERATION_GOVERNANCE_BATCH_ACTION,
            AuditLog.resource_id == batch_id,
        )
        .order_by(desc(AuditLog.created_at))
        .limit(1)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="governance_batch_not_found")
    return DashboardTrialOperationGovernanceSuggestionBatch.model_validate(row.detail_json or {})


def _append_unique_tags(row: TestCase, tags: list[str]) -> bool:
    current = [str(item) for item in (row.tags_json or []) if str(item).strip()]
    changed = False
    for tag in tags:
        if tag not in current:
            current.append(tag)
            changed = True
    if changed:
        row.tags_json = current
    return changed


async def apply_dashboard_trial_operation_governance_suggestions(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    payload: DashboardTrialOperationGovernanceApplyRequest,
) -> DashboardTrialOperationGovernanceApplyData:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    batch = await _load_governance_batch(db, user=user, project_id=project.id, batch_id=payload.batchId)
    wanted = set(payload.suggestionIds or [item.id for item in batch.items if item.canApply])
    applied: list[str] = []
    skipped: list[str] = []
    updated_cases = 0

    for suggestion in batch.items:
        if suggestion.id not in wanted:
            continue
        if not suggestion.canApply:
            skipped.append(suggestion.id)
            continue
        rows = await _select_testcases_by_ids(
            db,
            tenant_id=user.tenant_id,
            project_id=project.id,
            ids=suggestion.targetIds,
        )
        if not rows:
            skipped.append(suggestion.id)
            continue
        tags: list[str]
        if suggestion.action == "TAG_DUPLICATE":
            tags = ["治理:重复候选"]
        elif suggestion.action == "MARK_LOW_VALUE":
            tags = ["治理:低价值候选"]
        elif suggestion.action == "PROMOTE_TO_FORMAL":
            tags = ["治理:待转正式用例"]
        else:
            tags = ["治理:P0覆盖待评审"]
        changed_count = 0
        for row in rows:
            meta = dict(row.ai_meta_json or {})
            governance_meta = list(meta.get("governanceSuggestions") or [])
            governance_meta.append(
                {
                    "batchId": payload.batchId,
                    "suggestionId": suggestion.id,
                    "category": suggestion.category,
                    "action": suggestion.action,
                    "appliedAt": to_unix_ts(datetime.utcnow()),
                }
            )
            meta["governanceSuggestions"] = governance_meta[-20:]
            row.ai_meta_json = meta
            if suggestion.action == "PROMOTE_TO_FORMAL" and row.status == TestCaseStatus.DRAFT:
                row.status = TestCaseStatus.REVIEWED
            tags_changed = _append_unique_tags(row, tags)
            if tags_changed or True:
                changed_count += 1
        if changed_count:
            updated_cases += changed_count
            applied.append(suggestion.id)
        else:
            skipped.append(suggestion.id)

    result = DashboardTrialOperationGovernanceApplyData(
        batchId=payload.batchId,
        appliedSuggestionIds=applied,
        skippedSuggestionIds=skipped,
        updatedCases=updated_cases,
        summary=f"已应用 {len(applied)} 条治理建议，更新 {updated_cases} 条用例",
    )
    db.add(
        AuditLog(
            tenant_id=user.tenant_id,
            project_id=project.id,
            user_id=user.id,
            module=_TRIAL_OPERATION_GOVERNANCE_MODULE,
            action=_TRIAL_OPERATION_GOVERNANCE_APPLY_ACTION,
            resource_type="trial_operation_governance_batch",
            resource_id=payload.batchId,
            summary=result.summary,
            detail_json=result.model_dump(mode="json"),
        )
    )
    await db.flush()
    return result


async def get_dashboard_trial_operation_governance_history(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    limit: int,
) -> DashboardTrialOperationGovernanceHistoryData:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)

    generate_rows = (
        await db.execute(
            select(AuditLog)
            .where(
                AuditLog.tenant_id == user.tenant_id,
                AuditLog.project_id == project.id,
                AuditLog.module == _TRIAL_OPERATION_GOVERNANCE_MODULE,
                AuditLog.action == _TRIAL_OPERATION_GOVERNANCE_BATCH_ACTION,
            )
            .order_by(desc(AuditLog.created_at))
            .limit(max(limit, 1))
        )
    ).scalars().all()
    all_apply_rows = (
        await db.execute(
            select(AuditLog)
            .where(
                AuditLog.tenant_id == user.tenant_id,
                AuditLog.project_id == project.id,
                AuditLog.module == _TRIAL_OPERATION_GOVERNANCE_MODULE,
                AuditLog.action == _TRIAL_OPERATION_GOVERNANCE_APPLY_ACTION,
            )
            .order_by(desc(AuditLog.created_at))
        )
    ).scalars().all()

    apply_by_batch: dict[str, list[AuditLog]] = {}
    total_applied_suggestions = 0
    total_updated_cases = 0
    for row in all_apply_rows:
        detail = dict(row.detail_json or {})
        batch_id = str(detail.get("batchId") or row.resource_id or "")
        if not batch_id:
            continue
        apply_by_batch.setdefault(batch_id, []).append(row)
        total_applied_suggestions += len(list(detail.get("appliedSuggestionIds") or []))
        total_updated_cases += int(detail.get("updatedCases") or 0)

    items: list[DashboardTrialOperationGovernanceHistoryItem] = []
    for row in generate_rows:
        detail = dict(row.detail_json or {})
        batch_id = str(detail.get("batchId") or row.resource_id or "")
        suggestions = list(detail.get("items") or [])
        apply_rows = apply_by_batch.get(batch_id, [])
        applied_count = 0
        updated_cases = 0
        for apply_row in apply_rows:
            apply_detail = dict(apply_row.detail_json or {})
            applied_count += len(list(apply_detail.get("appliedSuggestionIds") or []))
            updated_cases += int(apply_detail.get("updatedCases") or 0)
        total_suggestions = len(suggestions)
        if applied_count <= 0:
            status = "GENERATED"
        elif applied_count >= total_suggestions and total_suggestions > 0:
            status = "APPLIED"
        else:
            status = "PARTIAL_APPLIED"
        items.append(
            DashboardTrialOperationGovernanceHistoryItem(
                batchId=batch_id,
                generatedAt=int(detail.get("generatedAt") or to_unix_ts(row.created_at)),
                source=str(detail.get("source") or "HYBRID"),
                totalSuggestions=total_suggestions,
                appliedSuggestions=applied_count,
                updatedCases=updated_cases,
                status=status,
                summary=f"生成 {total_suggestions} 条，已应用 {applied_count} 条，更新 {updated_cases} 条用例",
            )
        )

    return DashboardTrialOperationGovernanceHistoryData(
        generatedBatches=len(generate_rows),
        appliedBatches=len(apply_by_batch),
        appliedSuggestions=total_applied_suggestions,
        updatedCases=total_updated_cases,
        latestBatchId=items[0].batchId if items else None,
        items=items,
    )


async def import_dashboard_trial_operation_execution_results(
    db: AsyncSession,
    *,
    user: CurrentUser,
    project_id: uuid.UUID,
    payload: DashboardTrialOperationExecutionImportRequest,
) -> DashboardTrialOperationExecutionImportData:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)

    failed_ids = {str(item) for item in payload.failedCaseIds}
    skipped_ids = {str(item) for item in payload.skippedCaseIds}
    rows = (
        await db.execute(
            select(TestCase)
            .where(
                TestCase.tenant_id == user.tenant_id,
                TestCase.project_id == project.id,
                TestCase.test_case_id.is_not(None),
                func.trim(TestCase.test_case_id) != "",
                TestCase.test_case_id.notlike("TC_IMPORT_%"),
            )
            .order_by(TestCase.priority.asc(), TestCase.updated_at.desc().nullslast(), TestCase.id.asc())
            .limit(payload.totalLimit)
        )
    ).scalars().all()
    if not rows:
        rows = (
            await db.execute(
                select(TestCase)
                .where(TestCase.tenant_id == user.tenant_id, TestCase.project_id == project.id)
                .order_by(TestCase.priority.asc(), TestCase.updated_at.desc().nullslast(), TestCase.id.asc())
                .limit(payload.totalLimit)
            )
        ).scalars().all()
    if not rows:
        raise HTTPException(status_code=422, detail="no_testcases_available_for_execution_import")

    now = datetime.utcnow()
    run_status = RunStatus.PASSED
    run = Run(
        tenant_id=user.tenant_id,
        project_id=project.id,
        suite_id=None,
        env_id=None,
        trigger_type=TriggerType.MANUAL,
        status=RunStatus.PASSED,
        start_at=now,
        end_at=now,
        summary_json={
            "source": "trial_operation_manual_import",
            "note": payload.note or "试运行执行结果接入",
        },
        idempotency_key=f"trial-operation-{uuid.uuid4().hex[:16]}",
        created_by=user.id,
    )
    db.add(run)
    await db.flush()

    passed = failed = skipped = 0
    for index, row in enumerate(rows, start=1):
        row_id = str(row.id)
        if row_id in skipped_ids:
            status = CaseRunStatus.SKIPPED
            skipped += 1
        elif row_id in failed_ids:
            status = CaseRunStatus.FAILED
            failed += 1
        else:
            status = CaseRunStatus.PASSED
            passed += 1
        if status == CaseRunStatus.FAILED:
            run_status = RunStatus.FAILED
        case_start = now + timedelta(milliseconds=index * 10)
        db.add(
            CaseRun(
                tenant_id=user.tenant_id,
                run_id=run.id,
                testcase_id=row.id,
                status=status,
                start_at=case_start,
                end_at=case_start + timedelta(milliseconds=120),
                error_type="ASSERTION" if status == CaseRunStatus.FAILED else None,
                error_message="试运行执行结果标记失败" if status == CaseRunStatus.FAILED else None,
                metrics_json={"durationMs": 120, "source": "trial_operation_execution_import"},
            )
        )
    run.status = run_status
    run.summary_json = {
        **dict(run.summary_json or {}),
        "total": len(rows),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
    }
    await db.flush()
    return DashboardTrialOperationExecutionImportData(
        runId=str(run.id),
        total=len(rows),
        passed=passed,
        failed=failed,
        skipped=skipped,
        summary=f"已写入执行结果：{len(rows)} 条，通过 {passed}，失败 {failed}，跳过 {skipped}",
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
    executed_case_runs = int(metrics.get("executedCaseRuns", 0) or 0)
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

    if executed_case_runs <= 0:
        return DashboardTrialOperationAcceptanceSummary(
            conclusion="待执行验证",
            score=60,
            level="INSUFFICIENT",
            highlights=highlights[:3],
            risks=(risks + ["尚未接入真实执行结果，0 缺陷不能代表已验收通过"])[:4],
            nextActions=(next_actions + ["执行核心用例或导入缺陷/执行结果后再形成验收结论"])[:4],
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
        f"- 已执行用例：{int(metrics.get('executedCaseRuns', 0) or 0)}",
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
    try:
        governance = await get_dashboard_case_governance(db, user=user, project_id=project_id)
        governance_lines = [
            "",
            "## 用例库治理",
            f"- 测试资产总量：{governance.totalCases}",
            f"- 正式用例：{governance.formalCases}",
            f"- 测试点：{governance.testPointCases}",
            f"- 平台补号：{governance.generatedImportIds}",
            f"- 重复标题候选：{len(governance.duplicateTitleCandidates)} 组",
            f"- 低价值候选：{len(governance.lowValueCandidates)} 条",
            f"- P0 覆盖密度：{governance.p0Density}%",
        ]
    except Exception:
        governance_lines = []
    return DashboardTrialOperationReportData(
        title="WeiTesting 真实数据试运行验收报告",
        generatedAt=to_unix_ts(datetime.utcnow()),
        markdown=_render_trial_operation_report_markdown(trial_data) + "\n".join(governance_lines),
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
