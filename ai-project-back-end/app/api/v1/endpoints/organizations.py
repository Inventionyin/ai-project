from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id, to_unix_ts
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.organization import (
    OrganizationCreateRequest,
    OrganizationDetailData,
    OrganizationListItem,
    OrganizationUpdateRequest,
)
from app.services.organization import (
    create_organization,
    delete_organization,
    get_organization,
    list_organizations,
    update_organization,
)

router = APIRouter(prefix="/organizations")


def _to_detail(org, project_count: int) -> OrganizationDetailData:
    return OrganizationDetailData(
        id=str(org.id),
        name=org.name,
        description=org.description,
        settings=dict(org.settings_json) if org.settings_json else None,
        projectCount=project_count,
        createdAt=to_unix_ts(org.created_at),
        updatedAt=to_unix_ts(org.updated_at),
    )


@router.post("", response_model=ApiResponse[OrganizationDetailData])
async def create(
    payload: OrganizationCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[OrganizationDetailData]:
    try:
        org = await create_organization(
            db,
            user=user,
            name=payload.name,
            description=payload.description,
            settings=payload.settings,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    org, project_count = await get_organization(db, user=user, org_id=org.id)
    return ApiResponse(data=_to_detail(org, project_count), requestId=request_id)


@router.get("", response_model=ApiResponse[PageData[OrganizationListItem]])
async def list_(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    keyword: str | None = Query(None, max_length=255),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[PageData[OrganizationListItem]]:
    total, rows = await list_organizations(db, user=user, page=page, page_size=pageSize, keyword=keyword)
    items = [
        OrganizationListItem(
            id=str(org.id),
            name=org.name,
            description=org.description,
            projectCount=project_count,
            createdAt=to_unix_ts(org.created_at),
        )
        for org, project_count in rows
    ]
    return ApiResponse(
        data=PageData(page=page, pageSize=pageSize, total=total, items=items),
        requestId=request_id,
    )


@router.get("/{orgId}", response_model=ApiResponse[OrganizationDetailData])
async def get(
    orgId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[OrganizationDetailData]:
    org, project_count = await get_organization(db, user=user, org_id=orgId)
    return ApiResponse(data=_to_detail(org, project_count), requestId=request_id)


@router.put("/{orgId}", response_model=ApiResponse[OrganizationDetailData])
async def update(
    orgId: uuid.UUID,
    payload: OrganizationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[OrganizationDetailData]:
    try:
        org, project_count = await update_organization(
            db,
            user=user,
            org_id=orgId,
            name=payload.name,
            description=payload.description,
            settings=payload.settings,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=_to_detail(org, project_count), requestId=request_id)


@router.delete("/{orgId}", response_model=ApiResponse[dict])
async def delete(
    orgId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        await delete_organization(db, user=user, org_id=orgId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={}, requestId=request_id)
