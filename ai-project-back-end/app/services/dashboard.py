from __future__ import annotations

import uuid

from datetime import date, datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, to_unix_ts
from app.models.enums import CaseRunStatus, Priority, ProjectRole, RunStatus
from app.models.project import Project, ProjectMember
from app.models.run import CaseRun, Run
from app.models.suite import Suite
from app.models.testcase import TestCase
from app.schemas.dashboard import (
    DashboardFailureTopData,
    DashboardFailureTopSuiteItem,
    DashboardFailureTopTestcaseItem,
    DashboardQualityGateData,
    DashboardQualityGateItem,
    DashboardSummaryData,
    DashboardTrendData,
    DashboardTrendItem,
)


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
