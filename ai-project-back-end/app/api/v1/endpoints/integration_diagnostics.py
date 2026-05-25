from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.integration_diagnostics import ExternalIntegrationDiagnosticsData
from app.services.integration_diagnostics import get_external_integration_diagnostics

router = APIRouter(prefix="/projects/{projectId}/integrations/diagnostics")


@router.get("", response_model=ApiResponse[ExternalIntegrationDiagnosticsData])
async def get_project_external_integration_diagnostics(
    projectId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[ExternalIntegrationDiagnosticsData]:
    data = await get_external_integration_diagnostics(db, user=user, project_id=projectId)
    return ApiResponse(data=data, requestId=request_id)
