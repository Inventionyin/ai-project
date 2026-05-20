from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.knowledge import (
    KnowledgeRecommendationItem,
    KnowledgeRecommendationStatusUpdateRequest,
    KnowledgeTemplateCreateRequest,
    KnowledgeTemplateDetail,
    KnowledgeTemplateUpdateRequest,
    RecommendationEvaluateRequest,
    RecommendationEvaluateResponse,
    RunDraftRequest,
    RetrospectiveRecordCreateRequest,
    RetrospectiveRecordDetail,
    RetrospectiveRecordListItem,
    RetrospectiveRecordUpdateRequest,
)
from app.services.knowledge import (
    create_knowledge_template,
    create_retrospective_draft_from_run,
    create_retrospective_record,
    evaluate_recommendations,
    get_knowledge_template,
    get_retrospective_record,
    list_knowledge_templates,
    list_retrospective_records,
    update_recommendation_status,
    update_knowledge_template,
    update_retrospective_record,
)

router = APIRouter(prefix="/projects/{projectId}/knowledge")


@router.post("/retrospectives", response_model=ApiResponse[RetrospectiveRecordDetail])
async def create_project_retrospective(
    projectId: uuid.UUID,
    payload: RetrospectiveRecordCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RetrospectiveRecordDetail]:
    try:
        data = await create_retrospective_record(db, user=user, project_id=projectId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.post("/retrospectives/draft-from-run", response_model=ApiResponse[RetrospectiveRecordDetail])
async def create_project_retrospective_draft_from_run(
    projectId: uuid.UUID,
    payload: RunDraftRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RetrospectiveRecordDetail]:
    try:
        run_id = uuid.UUID(payload.runId)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_run_id") from exc
    try:
        data = await create_retrospective_draft_from_run(
            db,
            user=user,
            project_id=projectId,
            run_id=run_id,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get("/retrospectives", response_model=ApiResponse[PageData[RetrospectiveRecordListItem]])
async def list_project_retrospectives(
    projectId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    sourceType: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[RetrospectiveRecordListItem]]:
    total, items = await list_retrospective_records(
        db,
        user=user,
        project_id=projectId,
        page=page,
        page_size=pageSize,
        source_type=sourceType,
        status=status,
    )
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@router.get("/retrospectives/{recordId}", response_model=ApiResponse[RetrospectiveRecordDetail])
async def get_project_retrospective(
    projectId: uuid.UUID,
    recordId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RetrospectiveRecordDetail]:
    data = await get_retrospective_record(db, user=user, project_id=projectId, record_id=recordId)
    return ApiResponse(data=data, requestId=request_id)


@router.put("/retrospectives/{recordId}", response_model=ApiResponse[RetrospectiveRecordDetail])
async def update_project_retrospective(
    projectId: uuid.UUID,
    recordId: uuid.UUID,
    payload: RetrospectiveRecordUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RetrospectiveRecordDetail]:
    try:
        data = await update_retrospective_record(db, user=user, project_id=projectId, record_id=recordId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.post("/recommendations/evaluate", response_model=ApiResponse[RecommendationEvaluateResponse])
async def evaluate_project_recommendations(
    projectId: uuid.UUID,
    payload: RecommendationEvaluateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RecommendationEvaluateResponse]:
    try:
        data = await evaluate_recommendations(db, user=user, project_id=projectId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.put("/recommendations/{recommendationId}/status", response_model=ApiResponse[KnowledgeRecommendationItem])
async def update_project_recommendation_status(
    projectId: uuid.UUID,
    recommendationId: uuid.UUID,
    payload: KnowledgeRecommendationStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[KnowledgeRecommendationItem]:
    try:
        data = await update_recommendation_status(
            db,
            user=user,
            project_id=projectId,
            recommendation_id=recommendationId,
            status=payload.status,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


templates_router = APIRouter(prefix="/projects/{projectId}/knowledge/templates")


@templates_router.post("", response_model=ApiResponse[KnowledgeTemplateDetail])
async def create_project_knowledge_template(
    projectId: uuid.UUID,
    payload: KnowledgeTemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[KnowledgeTemplateDetail]:
    try:
        data = await create_knowledge_template(db, user=user, project_id=projectId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@templates_router.get("", response_model=ApiResponse[PageData[KnowledgeTemplateDetail]])
async def list_project_knowledge_templates(
    projectId: uuid.UUID,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[KnowledgeTemplateDetail]]:
    total, items = await list_knowledge_templates(
        db,
        user=user,
        project_id=projectId,
        page=page,
        page_size=pageSize,
        category=category,
        status=status,
    )
    return ApiResponse(data=PageData(page=page, pageSize=pageSize, total=total, items=items), requestId=request_id)


@templates_router.get("/{templateId}", response_model=ApiResponse[KnowledgeTemplateDetail])
async def get_project_knowledge_template(
    projectId: uuid.UUID,
    templateId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[KnowledgeTemplateDetail]:
    data = await get_knowledge_template(db, user=user, project_id=projectId, template_id=templateId)
    return ApiResponse(data=data, requestId=request_id)


@templates_router.put("/{templateId}", response_model=ApiResponse[KnowledgeTemplateDetail])
async def update_project_knowledge_template(
    projectId: uuid.UUID,
    templateId: uuid.UUID,
    payload: KnowledgeTemplateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[KnowledgeTemplateDetail]:
    try:
        data = await update_knowledge_template(
            db,
            user=user,
            project_id=projectId,
            template_id=templateId,
            payload=payload,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)
