from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.doc_parse_job import DocParseJobCreateRequest, DocParseJobDetail
from app.services.doc_parse_job import (
    create_doc_parse_job,
    get_doc_parse_job,
    list_doc_parse_jobs,
    retry_doc_parse_job,
)

router = APIRouter(prefix="/projects/{projectId}/doc-parse-jobs")


@router.post("", response_model=ApiResponse[DocParseJobDetail])
async def create_job(
    projectId: uuid.UUID,
    body: DocParseJobCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DocParseJobDetail]:
    result = await create_doc_parse_job(
        db, user=user, project_id=projectId,
        doc_id=uuid.UUID(body.docId), doc_version_id=uuid.UUID(body.docVersionId),
    )
    return ApiResponse(data=result, requestId=request_id)


@router.get("", response_model=ApiResponse[PageData[DocParseJobDetail]])
async def list_jobs(
    projectId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[DocParseJobDetail]]:
    total, items = await list_doc_parse_jobs(
        db, user=user, project_id=projectId, page=page, page_size=pageSize, status=status,
    )
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.get("/{jobId}", response_model=ApiResponse[DocParseJobDetail])
async def get_job(
    projectId: uuid.UUID,
    jobId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DocParseJobDetail]:
    result = await get_doc_parse_job(db, user=user, project_id=projectId, job_id=jobId)
    return ApiResponse(data=result, requestId=request_id)


@router.post("/{jobId}/retry", response_model=ApiResponse[DocParseJobDetail])
async def retry_job(
    projectId: uuid.UUID,
    jobId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[DocParseJobDetail]:
    result = await retry_doc_parse_job(db, user=user, project_id=projectId, job_id=jobId)
    return ApiResponse(data=result, requestId=request_id)
