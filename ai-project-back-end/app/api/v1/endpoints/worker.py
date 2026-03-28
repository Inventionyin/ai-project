from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse, BaseSchema
from app.schemas.worker import WorkerHeartbeatRequest, WorkerPollData, WorkerPollRequest, WorkerRegisterData, WorkerRegisterRequest, WorkerReportRequest
from app.services.worker import CurrentWorker, get_current_worker, heartbeat_worker, poll_job, register_worker, report_job_result

router = APIRouter(prefix="/workers")


class WorkerAckData(BaseSchema):
    accepted: bool = True


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
