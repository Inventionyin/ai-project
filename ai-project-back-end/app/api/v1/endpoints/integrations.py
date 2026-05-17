from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id
from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.integration import (
    NotificationConfigCreateRequest,
    NotificationConfigDetail,
    NotificationStrategyCenterItem,
    NotificationConfigUpdateRequest,
    NotificationDeliveryListData,
    NotificationDeliveryRetryResult,
    NotificationStrategySimulateBatchRequest,
    NotificationStrategySimulateRequest,
    NotificationStrategySimulationBatchResult,
    NotificationStrategySimulationResult,
)
from app.services.integration_config import (
    create_notification_config,
    delete_notification_config,
    list_notification_strategy_center,
    list_notification_configs,
    list_notification_deliveries,
    retry_notification_delivery,
    simulate_notification_strategy_batch,
    simulate_notification_strategy,
    update_notification_config,
)

router = APIRouter(prefix="/projects/{projectId}/integrations/notifications")


@router.get("", response_model=ApiResponse[list[NotificationConfigDetail]])
async def list_project_notifications(
    projectId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[NotificationConfigDetail]]:
    data = await list_notification_configs(db, user=user, project_id=projectId)
    return ApiResponse(data=data, requestId=request_id)


@router.post("", response_model=ApiResponse[NotificationConfigDetail])
async def create_project_notification(
    projectId: uuid.UUID,
    payload: NotificationConfigCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[NotificationConfigDetail]:
    try:
        data = await create_notification_config(db, user=user, project_id=projectId, payload=payload)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.put("/{notificationId}", response_model=ApiResponse[NotificationConfigDetail])
async def update_project_notification(
    projectId: uuid.UUID,
    notificationId: uuid.UUID,
    payload: NotificationConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[NotificationConfigDetail]:
    try:
        data = await update_notification_config(
            db,
            user=user,
            project_id=projectId,
            notification_id=notificationId,
            payload=payload,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.delete("/{notificationId}", response_model=ApiResponse[dict])
async def delete_project_notification(
    projectId: uuid.UUID,
    notificationId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        await delete_notification_config(
            db,
            user=user,
            project_id=projectId,
            notification_id=notificationId,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={}, requestId=request_id)


@router.get("/deliveries", response_model=ApiResponse[NotificationDeliveryListData])
async def list_project_notification_deliveries(
    projectId: uuid.UUID,
    status: str | None = Query(default=None),
    runId: uuid.UUID | None = Query(default=None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[NotificationDeliveryListData]:
    data = await list_notification_deliveries(
        db,
        user=user,
        project_id=projectId,
        status=status,
        run_id=runId,
        page=page,
        page_size=pageSize,
    )
    return ApiResponse(data=data, requestId=request_id)


@router.post("/deliveries/{deliveryId}/retry", response_model=ApiResponse[NotificationDeliveryRetryResult])
async def retry_project_notification_delivery(
    projectId: uuid.UUID,
    deliveryId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[NotificationDeliveryRetryResult]:
    try:
        data = await retry_notification_delivery(
            db,
            user=user,
            project_id=projectId,
            delivery_id=deliveryId,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=data, requestId=request_id)


@router.get("/strategy-center", response_model=ApiResponse[list[NotificationStrategyCenterItem]])
async def list_project_notification_strategy_center(
    projectId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[NotificationStrategyCenterItem]]:
    data = await list_notification_strategy_center(db, user=user, project_id=projectId)
    return ApiResponse(data=data, requestId=request_id)


@router.post("/strategy-center/simulate", response_model=ApiResponse[NotificationStrategySimulationResult])
async def simulate_project_notification_strategy(
    projectId: uuid.UUID,
    payload: NotificationStrategySimulateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[NotificationStrategySimulationResult]:
    try:
        notification_id = uuid.UUID(payload.notificationId)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="notificationId must be a UUID") from exc
    data = await simulate_notification_strategy(
        db,
        user=user,
        project_id=projectId,
        notification_id=notification_id,
        run_context=(payload.runContext.model_dump() if payload.runContext is not None else None),
    )
    return ApiResponse(data=data, requestId=request_id)


@router.post("/strategy-center/simulate-batch", response_model=ApiResponse[NotificationStrategySimulationBatchResult])
async def simulate_batch_project_notification_strategy(
    projectId: uuid.UUID,
    payload: NotificationStrategySimulateBatchRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[NotificationStrategySimulationBatchResult]:
    try:
        notification_id = uuid.UUID(payload.notificationId)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="notificationId must be a UUID") from exc
    data = await simulate_notification_strategy_batch(
        db,
        user=user,
        project_id=projectId,
        notification_id=notification_id,
        run_contexts=payload.runContexts,
    )
    return ApiResponse(data=data, requestId=request_id)
