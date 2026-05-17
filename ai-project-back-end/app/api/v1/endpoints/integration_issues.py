from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.integration_issue import IntegrationIssueCreateRequest, IntegrationIssueDetail
from app.services.integration_issue import create_issue_link, list_issue_links

router = APIRouter(prefix="/projects/{projectId}/integrations/issues")


@router.get("", response_model=ApiResponse[list[IntegrationIssueDetail]])
async def list_project_issue_links(
    projectId: uuid.UUID,
    runId: uuid.UUID | None = Query(default=None),
    caseRunId: uuid.UUID | None = Query(default=None),
    provider: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[IntegrationIssueDetail]]:
    data = await list_issue_links(
        db,
        user=user,
        project_id=projectId,
        run_id=runId,
        case_run_id=caseRunId,
        provider=provider,
    )
    return ApiResponse(data=data, requestId=request_id)


@router.post("", response_model=ApiResponse[IntegrationIssueDetail])
async def create_project_issue_link(
    projectId: uuid.UUID,
    payload: IntegrationIssueCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[IntegrationIssueDetail]:
    try:
        data = await create_issue_link(db, user=user, project_id=projectId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)
