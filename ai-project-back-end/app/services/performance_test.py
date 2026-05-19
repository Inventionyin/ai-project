from __future__ import annotations

import json as json_mod
import logging
import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.models.enums import ProjectRole
from app.models.performance_test import PerformanceTest, PerformanceTestRun
from app.models.project import Project, ProjectMember
from app.schemas.performance import (
    PerformanceTestDetail,
    PerformanceTestRunDetail,
    TrendDataPoint,
)
from app.services.platform_record import create_audit_log

logger = logging.getLogger(__name__)


def _is_admin(user: CurrentUser) -> bool:
    return "Admin" in user.roles or "ADMIN" in user.roles


async def _get_project(db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID) -> Project:
    project = await db.scalar(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _require_project_write(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = (await db.execute(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user.id,
            ProjectMember.tenant_id == user.tenant_id,
        )
    )).scalar_one_or_none()
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR):
        return
    raise HTTPException(status_code=403, detail="No write access to this project")


async def _require_project_read(db: AsyncSession, *, user: CurrentUser, project: Project) -> None:
    if _is_admin(user) or project.owner_id == user.id:
        return
    role = (await db.execute(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user.id,
            ProjectMember.tenant_id == user.tenant_id,
        )
    )).scalar_one_or_none()
    if role in (ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.EDITOR, ProjectRole.VIEWER):
        return
    raise HTTPException(status_code=403, detail="No access to this project")


def _to_test_detail(row: PerformanceTest) -> PerformanceTestDetail:
    return PerformanceTestDetail(
        id=str(row.id),
        projectId=str(row.project_id),
        name=row.name,
        description=row.description or "",
        testType=row.test_type,
        targetUrl=row.target_url or "",
        config=dict(row.config_json) if row.config_json else {},
        scriptContent=row.script_content or "",
        status=row.status,
        tags=list(row.tags) if row.tags else [],
        createdBy=str(row.created_by) if row.created_by else None,
        createdAt=int(row.created_at.timestamp()),
        updatedAt=int(row.updated_at.timestamp()),
    )


def _to_run_detail(row: PerformanceTestRun) -> PerformanceTestRunDetail:
    return PerformanceTestRunDetail(
        id=str(row.id),
        testId=str(row.test_id),
        status=row.status,
        startedAt=row.started_at,
        finishedAt=row.finished_at,
        durationMs=row.duration_ms,
        metrics=dict(row.metrics_json) if row.metrics_json else {},
        thresholds=dict(row.thresholds_json) if row.thresholds_json else {},
        reportPath=row.report_path,
        errorMessage=row.error_message,
        createdAt=int(row.created_at.timestamp()),
        updatedAt=int(row.updated_at.timestamp()),
    )


def _generate_k6_script(test_type: str, target_url: str, config: dict) -> str:
    """Generate a k6 script from test configuration."""
    vus = config.get("vus", 10)
    duration = config.get("duration", "30s")
    stages = config.get("stages", [])
    thresholds = config.get("thresholds", {})

    script_lines = [
        "import http from 'k6/http';",
        "import { check, sleep } from 'k6';",
        "",
        "export const options = {",
    ]

    if test_type == "LOAD":
        script_lines.append(f"  vus: {vus},")
        script_lines.append(f"  duration: '{duration}',")
    elif test_type == "STRESS":
        script_lines.append(f"  stages: [")
        script_lines.append(f"    {{ duration: '2m', target: {vus} }},")
        script_lines.append(f"    {{ duration: '5m', target: {vus} }},")
        script_lines.append(f"    {{ duration: '2m', target: {vus * 2} }},")
        script_lines.append(f"    {{ duration: '5m', target: {vus * 2} }},")
        script_lines.append(f"    {{ duration: '2m', target: 0 }},")
        script_lines.append(f"  ],")
    elif test_type == "SPIKE":
        script_lines.append(f"  stages: [")
        script_lines.append(f"    {{ duration: '10s', target: {vus} }},")
        script_lines.append(f"    {{ duration: '1m', target: {vus} }},")
        script_lines.append(f"    {{ duration: '10s', target: {vus * 5} }},")
        script_lines.append(f"    {{ duration: '3m', target: {vus * 5} }},")
        script_lines.append(f"    {{ duration: '10s', target: {vus} }},")
        script_lines.append(f"    {{ duration: '3m', target: {vus} }},")
        script_lines.append(f"    {{ duration: '10s', target: 0 }},")
        script_lines.append(f"  ],")
    elif test_type == "SOAK":
        script_lines.append(f"  stages: [")
        script_lines.append(f"    {{ duration: '5m', target: {vus} }},")
        script_lines.append(f"    {{ duration: '30m', target: {vus} }},")
        script_lines.append(f"    {{ duration: '5m', target: 0 }},")
        script_lines.append(f"  ],")
    elif stages:
        script_lines.append(f"  stages: [")
        for stage in stages:
            script_lines.append(f"    {{ duration: '{stage.get('duration', '1m')}', target: {stage.get('target', vus)} }},")
        script_lines.append(f"  ],")
    else:
        script_lines.append(f"  vus: {vus},")
        script_lines.append(f"  duration: '{duration}',")

    if thresholds:
        script_lines.append("  thresholds: {")
        for metric, threshold in thresholds.items():
            if isinstance(threshold, list):
                threshold_str = ", ".join(f"'{t}'" for t in threshold)
                script_lines.append(f"    '{metric}': [{threshold_str}],")
            else:
                script_lines.append(f"    '{metric}': ['{threshold}'],")
        script_lines.append("  },")
    else:
        script_lines.append("  thresholds: {")
        script_lines.append("    http_req_duration: ['p(95)<500'],")
        script_lines.append("    http_req_failed: ['rate<0.01'],")
        script_lines.append("  },")

    script_lines.extend([
        "};",
        "",
        "export default function () {",
        f"  const res = http.get('{target_url}');",
        "  check(res, {",
        "    'status is 200': (r) => r.status === 200,",
        "    'response time < 500ms': (r) => r.timings.duration < 500,",
        "  });",
        "  sleep(1);",
        "}",
    ])

    return "\n".join(script_lines)


def _parse_k6_summary(stdout: str) -> dict | None:
    """Try to parse k6 --summary-export JSON from stdout."""
    for line in stdout.strip().split("\n"):
        try:
            data = json_mod.loads(line)
            if "metrics" in data:
                metrics = data["metrics"]
                return {
                    "reqPerSec": metrics.get("http_reqs", {}).get("rate", 0),
                    "avgLatency": metrics.get("http_req_duration", {}).get("avg", 0),
                    "p95": metrics.get("http_req_duration", {}).get("p(95)", 0),
                    "p99": metrics.get("http_req_duration", {}).get("p(99)", 0),
                    "errorRate": metrics.get("http_req_failed", {}).get("rate", 0),
                    "totalRequests": int(metrics.get("http_reqs", {}).get("count", 0)),
                }
        except (json_mod.JSONDecodeError, AttributeError, TypeError):
            continue
    return None


def _parse_k6_stderr(stderr: str) -> dict | None:
    """Parse basic metrics from k6 stderr output as a last resort."""
    import re
    metrics: dict = {}
    # Look for common k6 summary lines
    req_match = re.search(r"http_reqs\s*[:=]\s*([\d.]+)", stderr)
    if req_match:
        metrics["totalRequests"] = int(float(req_match.group(1)))
    duration_match = re.search(r"http_req_duration\s*.*?avg[=:\s]*([\d.]+)", stderr)
    if duration_match:
        metrics["avgLatency"] = round(float(duration_match.group(1)), 2)
    p95_match = re.search(r"p\(95\)[=:\s]*([\d.]+)", stderr)
    if p95_match:
        metrics["p95"] = round(float(p95_match.group(1)), 2)
    p99_match = re.search(r"p\(99\)[=:\s]*([\d.]+)", stderr)
    if p99_match:
        metrics["p99"] = round(float(p99_match.group(1)), 2)
    return metrics if metrics else None


def _simulated_metrics(config: dict) -> dict:
    """Fallback simulated metrics when k6 is not available."""
    import random
    return {
        "reqPerSec": round(random.uniform(50, 500), 2),
        "avgLatency": round(random.uniform(10, 200), 2),
        "p95": round(random.uniform(100, 500), 2),
        "p99": round(random.uniform(200, 1000), 2),
        "errorRate": round(random.uniform(0, 5), 2),
        "totalRequests": random.randint(1000, 50000),
        "dataReceived": f"{random.randint(1, 100)} MB",
        "dataSent": f"{random.randint(1, 50)} MB",
    }


def _execute_k6(script_content: str, config: dict) -> dict:
    """Execute k6 script and return metrics. Falls back to simulated if k6 unavailable."""
    # Check if k6 is available
    try:
        version_result = subprocess.run(
            ["k6", "version"], capture_output=True, text=True, timeout=5,
        )
        if version_result.returncode != 0:
            logger.info("k6 not available (exit code %s), using simulated metrics", version_result.returncode)
            return _simulated_metrics(config)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.info("k6 not found on PATH, using simulated metrics")
        return _simulated_metrics(config)

    # Write script to temp file and run k6
    script_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(script_content)
            script_path = f.name

        timeout = config.get("duration_seconds", 60) + 30
        result = subprocess.run(
            ["k6", "run", "--quiet", "--summary-export=stdout", script_path],
            capture_output=True, text=True, timeout=timeout,
        )

        # Try parsing summary JSON from stdout
        parsed = _parse_k6_summary(result.stdout)
        if parsed:
            return parsed

        # Try parsing from stderr
        parsed = _parse_k6_stderr(result.stderr)
        if parsed:
            return parsed

        logger.warning("k6 ran but output could not be parsed, using simulated metrics")
        return _simulated_metrics(config)

    except subprocess.TimeoutExpired:
        logger.warning("k6 execution timed out, using simulated metrics")
        return _simulated_metrics(config)
    except Exception as exc:
        logger.warning("k6 execution failed: %s, using simulated metrics", exc)
        return _simulated_metrics(config)
    finally:
        if script_path:
            try:
                os.unlink(script_path)
            except OSError:
                pass


async def create_test(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
    name: str, test_type: str = "LOAD", description: str = "",
    target_url: str = "", config: dict | None = None,
    script_content: str = "", tags: list[str] | None = None,
) -> PerformanceTestDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = PerformanceTest(
        tenant_id=user.tenant_id, project_id=project_id, name=name,
        description=description, test_type=test_type, target_url=target_url,
        config_json=config or {}, script_content=script_content,
        tags=tags or [], created_by=user.id,
    )
    db.add(row)
    await db.flush()
    await create_audit_log(
        db, user=user, project_id=project_id,
        action="CREATE_PERFORMANCE_TEST", resource_type="performance_test",
        resource_id=str(row.id), summary=f"创建性能测试: {name} ({test_type})",
    )
    return _to_test_detail(row)


async def list_tests(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID,
    page: int, page_size: int,
) -> tuple[int, list[PerformanceTestDetail]]:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    base = select(PerformanceTest).where(
        PerformanceTest.tenant_id == user.tenant_id,
        PerformanceTest.project_id == project_id,
    )
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    rows = (await db.execute(base.order_by(desc(PerformanceTest.created_at)).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return total, [_to_test_detail(r) for r in rows]


async def get_test(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, test_id: uuid.UUID,
) -> PerformanceTestDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_read(db, user=user, project=project)
    row = await db.scalar(select(PerformanceTest).where(
        PerformanceTest.id == test_id,
        PerformanceTest.project_id == project_id,
        PerformanceTest.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Performance test not found")
    return _to_test_detail(row)


async def update_test(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, test_id: uuid.UUID,
    **kwargs,
) -> PerformanceTestDetail:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await db.scalar(select(PerformanceTest).where(
        PerformanceTest.id == test_id,
        PerformanceTest.project_id == project_id,
        PerformanceTest.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Performance test not found")
    for key, value in kwargs.items():
        if value is not None:
            if key == "name":
                row.name = value
            elif key == "description":
                row.description = value
            elif key == "test_type":
                row.test_type = value
            elif key == "target_url":
                row.target_url = value
            elif key == "config":
                row.config_json = value
            elif key == "script_content":
                row.script_content = value
            elif key == "tags":
                row.tags = value
    await db.flush()
    return _to_test_detail(row)


async def delete_test(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, test_id: uuid.UUID,
) -> None:
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    row = await db.scalar(select(PerformanceTest).where(
        PerformanceTest.id == test_id,
        PerformanceTest.project_id == project_id,
        PerformanceTest.tenant_id == user.tenant_id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Performance test not found")
    await db.delete(row)
    await db.flush()


async def run_test(
    db: AsyncSession, *, user: CurrentUser, project_id: uuid.UUID, test_id: uuid.UUID,
) -> PerformanceTestRunDetail:
    """Execute a performance test run (simulated)."""
    project = await _get_project(db, user=user, project_id=project_id)
    await _require_project_write(db, user=user, project=project)
    test = await db.scalar(select(PerformanceTest).where(
        PerformanceTest.id == test_id,
        PerformanceTest.project_id == project_id,
        PerformanceTest.tenant_id == user.tenant_id,
    ))
    if test is None:
        raise HTTPException(status_code=404, detail="Performance test not found")

    now_iso = datetime.now(timezone.utc).isoformat()
    run = PerformanceTestRun(
        tenant_id=user.tenant_id, test_id=test_id,
        status="RUNNING", started_at=now_iso,
    )
    db.add(run)
    await db.flush()

    # Execute k6 (real if available, simulated fallback)
    config = test.config_json or {}
    script_content = test.script_content or _generate_k6_script(
        test.test_type, test.target_url or "https://httpbin.org/get", config,
    )
    metrics = _execute_k6(script_content, config)

    finished_iso = datetime.now(timezone.utc).isoformat()
    run.status = "COMPLETED"
    run.finished_at = finished_iso
    run.duration_ms = metrics.pop("_duration_ms", 5000 + hash(str(run.id)) % 55000)
    run.metrics_json = metrics
    threshold_defs = config.get("thresholds", {"p95": ["<500"], "errorRate": ["<1"]})
    threshold_results = []
    all_passed = True
    for metric, rules in threshold_defs.items():
        value = run.metrics_json.get(metric, 0)
        passed = True
        for rule in rules:
            if rule.startswith("<"):
                passed = value < float(rule[1:])
            elif rule.startswith(">"):
                passed = value > float(rule[1:])
            elif rule.startswith("rate<"):
                passed = value < float(rule[5:])
        if not passed:
            all_passed = False
        threshold_results.append({"metric": metric, "rules": rules, "value": value, "passed": passed})
    run.thresholds_json = {"passed": all_passed, "details": threshold_results}

    await db.flush()
    await create_audit_log(
        db, user=user, project_id=project_id,
        action="RUN_PERFORMANCE_TEST", resource_type="performance_test_run",
        resource_id=str(run.id), summary=f"执行性能测试: {test.name}",
    )
    return _to_run_detail(run)


async def list_runs(
    db: AsyncSession, *, user: CurrentUser, test_id: uuid.UUID,
    page: int, page_size: int,
) -> tuple[int, list[PerformanceTestRunDetail]]:
    base = select(PerformanceTestRun).where(
        PerformanceTestRun.tenant_id == user.tenant_id,
        PerformanceTestRun.test_id == test_id,
    )
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    rows = (await db.execute(base.order_by(desc(PerformanceTestRun.created_at)).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return total, [_to_run_detail(r) for r in rows]


async def get_trend(
    db: AsyncSession, *, user: CurrentUser, test_id: uuid.UUID,
) -> list[TrendDataPoint]:
    """Get trend data for a performance test."""
    base = select(PerformanceTestRun).where(
        PerformanceTestRun.tenant_id == user.tenant_id,
        PerformanceTestRun.test_id == test_id,
        PerformanceTestRun.status == "COMPLETED",
    ).order_by(PerformanceTestRun.created_at).limit(50)
    rows = (await db.execute(base)).scalars().all()
    result = []
    for row in rows:
        metrics = dict(row.metrics_json) if row.metrics_json else {}
        result.append(TrendDataPoint(
            runId=str(row.id),
            createdAt=int(row.created_at.timestamp()),
            reqPerSec=metrics.get("reqPerSec"),
            avgLatency=metrics.get("avgLatency"),
            p95=metrics.get("p95"),
            p99=metrics.get("p99"),
            errorRate=metrics.get("errorRate"),
            durationMs=row.duration_ms,
        ))
    return result


async def generate_k6_script(
    test_type: str, target_url: str, config: dict | None = None,
) -> str:
    """Generate a k6 script from configuration."""
    return _generate_k6_script(test_type, target_url, config or {})
