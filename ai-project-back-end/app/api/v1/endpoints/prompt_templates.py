from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.prompt_template import (
    PromptTemplateActivateRequest,
    PromptTemplateCreateRequest,
    PromptTemplateDetail,
    PromptTemplateGovernanceItem,
    PromptTemplateRollbackRequest,
    PromptTemplateRollbackResult,
    PromptTemplateUpdateRequest,
)
from app.services.prompt_template import (
    activate_prompt_template,
    create_prompt_template,
    list_prompt_template_governance,
    list_prompt_templates,
    rollback_prompt_template,
    update_prompt_template,
)

router = APIRouter(prefix="/projects/{projectId}/prompt-templates")


@router.get("", response_model=ApiResponse[list[PromptTemplateDetail]])
async def list_project_prompt_templates(
    projectId: uuid.UUID,
    scene: str | None = Query(default=None),
    name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[PromptTemplateDetail]]:
    data = await list_prompt_templates(db, user=user, project_id=projectId, scene=scene, name=name)
    return ApiResponse(data=data, requestId=request_id)


@router.post("", response_model=ApiResponse[PromptTemplateDetail])
async def create_project_prompt_template(
    projectId: uuid.UUID,
    payload: PromptTemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PromptTemplateDetail]:
    try:
        data = await create_prompt_template(db, user=user, project_id=projectId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.put("/{templateId}", response_model=ApiResponse[PromptTemplateDetail])
async def update_project_prompt_template(
    projectId: uuid.UUID,
    templateId: uuid.UUID,
    payload: PromptTemplateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PromptTemplateDetail]:
    try:
        data = await update_prompt_template(db, user=user, project_id=projectId, template_id=templateId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.post("/{templateId}/activate", response_model=ApiResponse[PromptTemplateDetail])
async def activate_project_prompt_template(
    projectId: uuid.UUID,
    templateId: uuid.UUID,
    payload: PromptTemplateActivateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PromptTemplateDetail]:
    try:
        data = await activate_prompt_template(
            db,
            user=user,
            project_id=projectId,
            template_id=templateId,
            payload=payload or PromptTemplateActivateRequest(),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get("/governance", response_model=ApiResponse[list[PromptTemplateGovernanceItem]])
async def list_project_prompt_templates_governance(
    projectId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[PromptTemplateGovernanceItem]]:
    data = await list_prompt_template_governance(db, user=user, project_id=projectId)
    return ApiResponse(data=data, requestId=request_id)


@router.post("/rollback", response_model=ApiResponse[PromptTemplateRollbackResult])
async def rollback_project_prompt_template(
    projectId: uuid.UUID,
    payload: PromptTemplateRollbackRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PromptTemplateRollbackResult]:
    try:
        data = await rollback_prompt_template(db, user=user, project_id=projectId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)
