from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse

router = APIRouter()


@router.get("/performance/slo", response_model=ApiResponse[dict])
async def get_slo_metrics(
    projectId: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    """Get SLO metrics for the platform."""
    from app.models.run import Run
    from app.models.testcase import TestCase
    from app.models.defect import Defect

    project_filter = []
    if projectId:
        try:
            pid = uuid.UUID(projectId)
            project_filter.append(Run.project_id == pid)
        except ValueError:
            pass

    # Run stats
    run_q = (
        select(func.count())
        .select_from(Run)
        .where(Run.tenant_id == user.tenant_id, *project_filter)
    )
    total_runs = (await db.execute(run_q)).scalar() or 0

    # Recent run pass rate
    run_filters = [Run.tenant_id == user.tenant_id]
    if projectId:
        try:
            run_filters.append(Run.project_id == uuid.UUID(projectId))
        except ValueError:
            pass
    recent_runs_q = (
        select(Run.status, func.count())
        .where(*run_filters)
        .group_by(Run.status)
    )
    run_stats = {
        str(r.status.value if hasattr(r.status, "value") else r.status): r.count
        for r in (await db.execute(recent_runs_q)).all()
    }

    # Test case count
    tc_filters = [TestCase.tenant_id == user.tenant_id]
    if projectId:
        try:
            tc_filters.append(TestCase.project_id == uuid.UUID(projectId))
        except ValueError:
            pass
    tc_q = select(func.count()).select_from(TestCase).where(*tc_filters)
    total_cases = (await db.execute(tc_q)).scalar() or 0

    # Defect count
    defect_filters = [Defect.tenant_id == user.tenant_id]
    if projectId:
        try:
            defect_filters.append(Defect.project_id == uuid.UUID(projectId))
        except ValueError:
            pass
    defect_q = select(func.count()).select_from(Defect).where(*defect_filters)
    total_defects = (await db.execute(defect_q)).scalar() or 0

    passed = run_stats.get("PASSED", 0)
    failed = run_stats.get("FAILED", 0)
    total_finished = passed + failed
    pass_rate = round(passed / total_finished * 100, 1) if total_finished > 0 else 0

    return ApiResponse(
        data={
            "totalRuns": total_runs,
            "runStatusBreakdown": run_stats,
            "passRate": pass_rate,
            "totalTestCases": total_cases,
            "totalDefects": total_defects,
            "slo": {
                "targetPassRate": 95.0,
                "actualPassRate": pass_rate,
                "met": pass_rate >= 95.0,
            },
        },
        requestId=request_id,
    )
