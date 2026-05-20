from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse, BaseSchema, PageData
from app.schemas.worker import WorkerHeartbeatRequest, WorkerPollData, WorkerPollRequest, WorkerRegisterData, WorkerRegisterRequest, WorkerReportRequest
from app.schemas.worker import WorkerAdminDetailData, WorkerAdminListData, WorkerAdminListItem
from app.services.worker import (
    CurrentWorker,
    get_current_worker,
    get_worker_admin,
    heartbeat_worker,
    list_workers_admin,
    poll_job,
    register_worker,
    report_job_result,
)

router = APIRouter(prefix="/workers")


class WorkerAckData(BaseSchema):
    accepted: bool = True


def _parse_worker_id(worker_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(worker_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid workerId") from exc


def _parse_status(status: str | None) -> str | None:
    if status is None:
        return None
    normalized = status.strip().upper()
    if normalized not in {"ONLINE", "OFFLINE"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    return normalized


@router.get("", response_model=ApiResponse[PageData[WorkerAdminListItem]])
async def list_workers(
    page: int = 1,
    pageSize: int = 20,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[WorkerAdminListItem]]:
    total, rows = await list_workers_admin(
        db,
        tenant_id=user.tenant_id,
        page=page,
        page_size=pageSize,
        status=_parse_status(status),
    )
    return ApiResponse(
        data=PageData(page=page, pageSize=pageSize, total=total, items=rows),
        requestId=request_id,
    )


@router.get("/{workerId}", response_model=ApiResponse[WorkerAdminDetailData])
async def get_worker(
    workerId: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[WorkerAdminDetailData]:
    worker = await get_worker_admin(db, tenant_id=user.tenant_id, worker_id=_parse_worker_id(workerId))
    return ApiResponse(data=worker, requestId=request_id)


@router.post("/register", response_model=ApiResponse[WorkerRegisterData])
async def register(
    payload: WorkerRegisterRequest,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[WorkerRegisterData]:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-Id is required")
    try:
        tenant_id = uuid.UUID(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid X-Tenant-Id") from exc
    try:
        worker_id, token = await register_worker(db, tenant_id=tenant_id, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=WorkerRegisterData(workerId=str(worker_id), token=token), requestId=request_id)


@router.post("/heartbeat", response_model=ApiResponse[WorkerAckData])
async def heartbeat(
    payload: WorkerHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
    worker: CurrentWorker = Depends(get_current_worker),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[WorkerAckData]:
    try:
        await heartbeat_worker(db, worker=worker, worker_id=payload.workerId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=WorkerAckData(), requestId=request_id)


@router.post("/poll", response_model=ApiResponse[WorkerPollData])
async def poll(
    payload: WorkerPollRequest,
    db: AsyncSession = Depends(get_db),
    worker: CurrentWorker = Depends(get_current_worker),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[WorkerPollData]:
    try:
        poll_data = await poll_job(
            db,
            worker=worker,
            worker_id=payload.workerId,
            capabilities=payload.capabilities,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=poll_data, requestId=request_id)


@router.post("/report", response_model=ApiResponse[WorkerAckData])
async def report(
    payload: WorkerReportRequest,
    db: AsyncSession = Depends(get_db),
    worker: CurrentWorker = Depends(get_current_worker),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[WorkerAckData]:
    try:
        run_id = uuid.UUID(payload.runId)
        job_id = uuid.UUID(payload.jobId)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid runId or jobId") from exc
    try:
        await report_job_result(
            db,
            worker=worker,
            worker_id=payload.workerId,
            run_id=run_id,
            job_id=job_id,
            results=payload.results,
            job_status=payload.jobStatus,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=WorkerAckData(), requestId=request_id)
