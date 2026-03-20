from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id, to_unix_ts
from app.core.database import get_db
from app.models.enums import CaseRunStatus, RunStatus
from app.schemas.common import ApiResponse, PageData
from app.schemas.run import (
    CaseRunListItem,
    RunCancelResponseData,
    RunCreateRequest,
    RunDetailData,
    RunFromTestcasesHttpRequest,
    RunFromTestcasesRequest,
    RunProgress,
    RunRetryRequest,
)
from app.services.run import (
    cancel_run,
    create_run,
    create_run_from_testcases,
    create_run_from_testcases_http,
    get_run,
    list_case_runs,
    list_runs,
    retry_run,
)

router = APIRouter(prefix="/runs")


def _to_run_detail(run, done: int, total: int) -> RunDetailData:
    if run.suite_id is None:
        raise HTTPException(status_code=500, detail="Run data invalid")
    start_at = run.start_at or run.created_at
    return RunDetailData(
        id=str(run.id),
        status=run.status,
        progress=RunProgress(done=done, total=total),
        suiteId=str(run.suite_id),
        envId=str(run.env_id) if run.env_id else None,
        startAt=to_unix_ts(start_at),
    )


@router.post("", response_model=ApiResponse[RunDetailData])
async def create_(
    payload: RunCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunDetailData]:
    idem = (idempotency_key or "").strip() or None
    if idem is not None:
        idem = idem[:128]
    try:
        run = await create_run(
            db,
            user=user,
            project_id=uuid.UUID(payload.projectId),
            suite_id=uuid.UUID(payload.suiteId),
            env_id=uuid.UUID(payload.envId),
            trigger_type=payload.triggerType,
            meta=dict(payload.meta or {}),
            notify_rule_id=payload.notifyRuleId,
            idempotency_key=idem,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    run, done, total = await get_run(db, user=user, run_id=run.id)
    return ApiResponse(data=_to_run_detail(run, done, total), requestId=request_id)


@router.get("", response_model=ApiResponse[PageData[RunDetailData]])
async def list_(
    projectId: str | None = Query(default=None),
    status: RunStatus | None = None,
    fromTs: int | None = Query(default=None, alias="from"),
    toTs: int | None = Query(default=None, alias="to"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[RunDetailData]]:
    project_uuid: uuid.UUID | None = None
    if projectId:
        try:
            project_uuid = uuid.UUID(projectId)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid projectId") from exc

    total, rows = await list_runs(
        db,
        user=user,
        project_id=project_uuid,
        status=status,
        from_ts=fromTs,
        to_ts=toTs,
        page=page,
        page_size=pageSize,
    )
    items = [_to_run_detail(run, done, total_) for run, done, total_ in rows]
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.post("/from-testcases", response_model=ApiResponse[RunDetailData])
async def create_from_testcases_(
    payload: RunFromTestcasesRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunDetailData]:
    idem = (idempotency_key or "").strip() or None
    if idem is not None:
        idem = idem[:128]
    try:
        run = await create_run_from_testcases(
            db,
            user=user,
            project_id=uuid.UUID(payload.projectId),
            env_id=uuid.UUID(payload.envId),
            trigger_type=payload.triggerType,
            meta=dict(payload.meta or {}),
            concurrency=payload.concurrency,
            stop_on_failure=payload.stopOnFailure,
            items=[item.model_dump() for item in payload.items],
            notify_rule_id=payload.notifyRuleId,
            idempotency_key=idem,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    run, done, total = await get_run(db, user=user, run_id=run.id)
    return ApiResponse(data=_to_run_detail(run, done, total), requestId=request_id)


@router.post("/from-testcases-http", response_model=ApiResponse[RunDetailData])
async def create_from_testcases_http_(
    payload: RunFromTestcasesHttpRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunDetailData]:
    idem = (idempotency_key or "").strip() or None
    if idem is not None:
        idem = idem[:128]
    env_uuid: uuid.UUID | None = None
    if payload.envId:
        env_uuid = uuid.UUID(payload.envId)
    try:
        run = await create_run_from_testcases_http(
            db,
            user=user,
            project_id=uuid.UUID(payload.projectId),
            env_id=env_uuid,
            trigger_type=payload.triggerType,
            meta=dict(payload.meta or {}),
            concurrency=payload.concurrency,
            stop_on_failure=payload.stopOnFailure,
            items=[item.model_dump() for item in payload.items],
            notify_rule_id=payload.notifyRuleId,
            idempotency_key=idem,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    run, done, total = await get_run(db, user=user, run_id=run.id)
    return ApiResponse(data=_to_run_detail(run, done, total), requestId=request_id)


@router.get("/{runId}", response_model=ApiResponse[RunDetailData])
async def get_(
    runId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunDetailData]:
    run, done, total = await get_run(db, user=user, run_id=runId)
    return ApiResponse(data=_to_run_detail(run, done, total), requestId=request_id)


@router.get("/{runId}/case-runs", response_model=ApiResponse[PageData[CaseRunListItem]])
async def list_case_runs_(
    runId: uuid.UUID,
    status: CaseRunStatus | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[CaseRunListItem]]:
    run, total, rows = await list_case_runs(db, user=user, run_id=runId, status=status, page=page, page_size=pageSize)
    binding_snapshots = ((run.summary_json or {}).get("bindingSnapshots") or {}) if isinstance(run.summary_json, dict) else {}
    items = [
        CaseRunListItem(
            caseRunId=str(cr.id),
            testcaseId=str(cr.testcase_id),
            status=cr.status,
            startAt=to_unix_ts(cr.start_at) if cr.start_at else None,
            endAt=to_unix_ts(cr.end_at) if cr.end_at else None,
            errorType=cr.error_type,
            errorMessage=cr.error_message,
            bindingSnapshot=binding_snapshots.get(str(cr.id)),
        )
        for cr in rows
    ]
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.post("/{runId}/cancel", response_model=ApiResponse[RunCancelResponseData])
async def cancel_(
    runId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunCancelResponseData]:
    try:
        run = await cancel_run(db, user=user, run_id=runId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=RunCancelResponseData(runId=str(run.id), status=run.status), requestId=request_id)


@router.post("/{runId}/retry", response_model=ApiResponse[RunDetailData])
async def retry_(
    runId: uuid.UUID,
    payload: RunRetryRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RunDetailData]:
    idem = (idempotency_key or "").strip() or None
    if idem is not None:
        idem = idem[:128]
    try:
        new_run = await retry_run(
            db,
            user=user,
            run_id=runId,
            failed_only=bool(payload.failedOnly),
            idempotency_key=idem,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    run, done, total = await get_run(db, user=user, run_id=new_run.id)
    return ApiResponse(data=_to_run_detail(run, done, total), requestId=request_id)
