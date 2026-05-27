from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.devops_pipeline import DevOpsRun
from app.models.enums import JobStatus
from app.models.integration import NotificationOutbox
from app.models.plugin import PluginInstallation
from app.models.project import Project, ProjectCiToken
from app.models.run import Job
from app.models.worker import Worker
from app.schemas.ops import OpsHealthCheck, OpsHealthSummaryData


def _status_rank(status: str) -> int:
    order = {"READY": 0, "WARN": 1, "BLOCKED": 2}
    return order.get(status, 2)


def _best_status(statuses: list[str]) -> str:
    if not statuses:
        return "BLOCKED"
    return max(statuses, key=_status_rank)


def _blocked_check(key: str, label: str, detail: str, metric: dict, recommendation: str) -> OpsHealthCheck:
    return OpsHealthCheck(
        key=key,
        label=label,
        status="BLOCKED",
        detail=detail,
        metric=metric,
        recommendation=recommendation,
    )


async def _database_check(db: AsyncSession) -> OpsHealthCheck:
    try:
        _ = await db.scalar(select(1))
    except Exception as exc:
        return _blocked_check(
            "database",
            "Database",
            f"Database ping failed: {exc.__class__.__name__}",
            {"ok": False},
            "Check database connectivity and credentials.",
        )
    return OpsHealthCheck(
        key="database",
        label="Database",
        status="READY",
        detail="Database connection is healthy.",
        metric={"ok": True},
        recommendation="No action required.",
    )


async def _notification_outbox_check(db: AsyncSession, tenant_id) -> OpsHealthCheck:
    try:
        failed_count = int(
            (await db.scalar(select(func.count(NotificationOutbox.id)).where(NotificationOutbox.tenant_id == tenant_id, NotificationOutbox.status == "FAILED")))
            or 0
        )
        queued_count = int(
            (await db.scalar(select(func.count(NotificationOutbox.id)).where(NotificationOutbox.tenant_id == tenant_id, NotificationOutbox.status == "QUEUED")))
            or 0
        )
    except Exception as exc:
        return _blocked_check(
            "notificationOutbox",
            "Notification Outbox",
            f"Unable to query notification outbox: {exc.__class__.__name__}",
            {},
            "Inspect notification_outbox table and query permissions.",
        )
    status = "READY"
    if failed_count > 0 or queued_count > 50:
        status = "WARN"
    return OpsHealthCheck(
        key="notificationOutbox",
        label="Notification Outbox",
        status=status,
        detail="Outbox delivery queue status.",
        metric={"failedCount": failed_count, "queuedCount": queued_count},
        recommendation="Retry or inspect failed deliveries." if status == "WARN" else "No action required.",
    )


async def _workers_check(db: AsyncSession, tenant_id) -> OpsHealthCheck:
    try:
        stale_before = datetime.utcnow() - timedelta(minutes=5)
        stale_count = int(
            (await db.scalar(select(func.count(Worker.id)).where(Worker.tenant_id == tenant_id, Worker.last_seen_at.is_not(None), Worker.last_seen_at < stale_before)))
            or 0
        )
        total_count = int((await db.scalar(select(func.count(Worker.id)).where(Worker.tenant_id == tenant_id))) or 0)
    except Exception as exc:
        return _blocked_check(
            "workers",
            "Workers",
            f"Unable to query worker states: {exc.__class__.__name__}",
            {},
            "Verify workers table access and worker heartbeat flow.",
        )
    status = "READY"
    if total_count == 0 or stale_count > 0:
        status = "WARN"
    return OpsHealthCheck(
        key="workers",
        label="Workers",
        status=status,
        detail="Worker availability and heartbeat freshness.",
        metric={"staleCount": stale_count, "totalCount": total_count},
        recommendation="Bring workers online or investigate stale heartbeats." if status == "WARN" else "No action required.",
    )


async def _job_queue_check(db: AsyncSession, tenant_id) -> OpsHealthCheck:
    try:
        stuck_before = datetime.utcnow() - timedelta(seconds=60)
        stuck_queued_count = int(
            (
                await db.scalar(
                    select(func.count(Job.id)).where(
                        Job.tenant_id == tenant_id,
                        Job.status == JobStatus.QUEUED,
                        Job.created_at < stuck_before,
                    )
                )
            )
            or 0
        )
        queued_count = int(
            (await db.scalar(select(func.count(Job.id)).where(Job.tenant_id == tenant_id, Job.status == JobStatus.QUEUED)))
            or 0
        )
        running_count = int(
            (await db.scalar(select(func.count(Job.id)).where(Job.tenant_id == tenant_id, Job.status == JobStatus.RUNNING)))
            or 0
        )
    except Exception as exc:
        return _blocked_check(
            "executionQueue",
            "Execution Queue",
            f"Unable to query queued execution jobs: {exc.__class__.__name__}",
            {},
            "Check jobs table access and worker dispatch telemetry.",
        )
    status = "READY"
    if stuck_queued_count > 0 or queued_count > 20:
        status = "WARN"
    return OpsHealthCheck(
        key="executionQueue",
        label="Execution Queue",
        status=status,
        detail="Queued execution jobs and dispatch backlog.",
        metric={
            "stuckQueuedCount": stuck_queued_count,
            "queuedCount": queued_count,
            "runningCount": running_count,
        },
        recommendation=(
            "Investigate /api/workers/poll consumption, worker capabilities, and runner dispatch."
            if status == "WARN"
            else "No action required."
        ),
    )


async def _devops_runs_check(db: AsyncSession, tenant_id) -> OpsHealthCheck:
    try:
        pending_count = int(
            (await db.scalar(select(func.count(DevOpsRun.id)).where(DevOpsRun.tenant_id == tenant_id, DevOpsRun.status.in_(("PENDING", "RUNNING")))))
            or 0
        )
    except Exception as exc:
        return _blocked_check(
            "devopsRuns",
            "DevOps Runs",
            f"Unable to query DevOps runs: {exc.__class__.__name__}",
            {},
            "Check devops_runs table and pipeline runner integration.",
        )
    status = "WARN" if pending_count > 20 else "READY"
    return OpsHealthCheck(
        key="devopsRuns",
        label="DevOps Runs",
        status=status,
        detail="Pending/running DevOps execution load.",
        metric={"pendingCount": pending_count},
        recommendation="Check pipeline congestion and stuck runs." if status == "WARN" else "No action required.",
    )


async def _plugins_check(db: AsyncSession, tenant_id) -> OpsHealthCheck:
    try:
        installed_count = int(
            (await db.scalar(select(func.count(PluginInstallation.id)).where(PluginInstallation.tenant_id == tenant_id, PluginInstallation.status == "INSTALLED")))
            or 0
        )
    except Exception as exc:
        return _blocked_check(
            "plugins",
            "Plugins",
            f"Unable to query plugin installations: {exc.__class__.__name__}",
            {},
            "Check plugin_installations table access.",
        )
    status = "WARN" if installed_count == 0 else "READY"
    return OpsHealthCheck(
        key="plugins",
        label="Plugins",
        status=status,
        detail="Installed plugin footprint.",
        metric={"installedCount": installed_count},
        recommendation="Install required plugins for your projects." if status == "WARN" else "No action required.",
    )


async def _ci_tokens_check(db: AsyncSession, tenant_id) -> OpsHealthCheck:
    try:
        legacy_active_count = int(
            (
                await db.scalar(
                    select(func.count(Project.id)).where(
                        Project.tenant_id == tenant_id,
                        Project.ci_token_hash.is_not(None),
                        Project.ci_token_revoked_at.is_(None),
                    )
                )
            )
            or 0
        )
        named_active_count = int(
            (
                await db.scalar(
                    select(func.count(func.distinct(ProjectCiToken.project_id))).where(
                        ProjectCiToken.tenant_id == tenant_id,
                        ProjectCiToken.revoked_at.is_(None),
                    )
                )
            )
            or 0
        )
        active_count = max(legacy_active_count, named_active_count)
    except Exception as exc:
        return _blocked_check(
            "ciTokens",
            "CI Tokens",
            f"Unable to query CI token coverage: {exc.__class__.__name__}",
            {},
            "Check projects table CI token columns and permissions.",
        )
    status = "WARN" if active_count == 0 else "READY"
    return OpsHealthCheck(
        key="ciTokens",
        label="CI Tokens",
        status=status,
        detail="Projects with active CI token.",
        metric={
            "activeProjectCount": active_count,
            "legacyActiveProjectCount": legacy_active_count,
            "namedActiveProjectCount": named_active_count,
        },
        recommendation="Rotate and enable CI tokens for active projects." if status == "WARN" else "No action required.",
    )


async def build_ops_health_summary(db: AsyncSession, user: CurrentUser) -> OpsHealthSummaryData:
    checks = [
        await _database_check(db),
        await _notification_outbox_check(db, user.tenant_id),
        await _workers_check(db, user.tenant_id),
        await _job_queue_check(db, user.tenant_id),
        await _devops_runs_check(db, user.tenant_id),
        await _plugins_check(db, user.tenant_id),
        await _ci_tokens_check(db, user.tenant_id),
    ]
    overall_status = _best_status([check.status for check in checks])
    return OpsHealthSummaryData(
        overallStatus=overall_status,
        generatedAt=datetime.now(timezone.utc),
        checks=checks,
    )
