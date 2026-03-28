from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id, to_unix_ts
from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.environment import EnvironmentCreateRequest, EnvironmentPublic, EnvironmentUpdateRequest, HealthCheckConfig
from app.services.environment import (
    UNSET,
    create_environment,
    delete_environment,
    get_environment,
    get_secret_keys,
    list_environments,
    update_environment,
)

router = APIRouter(prefix="/projects/{projectId}/environments")


def _to_public(env) -> EnvironmentPublic:
    health_check = None
    if env.health_config_json:
        health_check = HealthCheckConfig(**env.health_config_json)
    return EnvironmentPublic(
        id=str(env.id),
        projectId=str(env.project_id),
        name=env.name,
        baseUrl=env.base_url,
        variables=dict(env.variables_json or {}),
        secretKeys=get_secret_keys(env),
        healthCheck=health_check,
        createdAt=to_unix_ts(env.created_at),
        updatedAt=to_unix_ts(env.updated_at),
    )


@router.post("", response_model=ApiResponse[EnvironmentPublic])
async def create(
    projectId: uuid.UUID,
    payload: EnvironmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[EnvironmentPublic]:
    try:
        env = await create_environment(
            db,
            user=user,
            project_id=projectId,
            name=payload.name,
            base_url=payload.baseUrl,
            variables=payload.variables,
            secrets=payload.secrets,
            health_check=payload.healthCheck.model_dump() if payload.healthCheck else None,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    env = await get_environment(db, user=user, project_id=projectId, env_id=env.id)
    return ApiResponse(data=_to_public(env), requestId=request_id)


@router.get("", response_model=ApiResponse[list[EnvironmentPublic]])
async def list_(
    projectId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[list[EnvironmentPublic]]:
    envs = await list_environments(db, user=user, project_id=projectId)
    return ApiResponse(data=[_to_public(e) for e in envs], requestId=request_id)


@router.get("/{envId}", response_model=ApiResponse[EnvironmentPublic])
async def get(
    projectId: uuid.UUID,
    envId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[EnvironmentPublic]:
    env = await get_environment(db, user=user, project_id=projectId, env_id=envId)
    return ApiResponse(data=_to_public(env), requestId=request_id)


@router.put("/{envId}", response_model=ApiResponse[EnvironmentPublic])
async def update(
    projectId: uuid.UUID,
    envId: uuid.UUID,
    payload: EnvironmentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[EnvironmentPublic]:
    fields_set = payload.model_fields_set
    name = payload.name if "name" in fields_set else None
    base_url = payload.baseUrl if "baseUrl" in fields_set else None
    variables = payload.variables if "variables" in fields_set else None
    secrets = payload.secrets if "secrets" in fields_set else None
    health_check = payload.healthCheck.model_dump() if payload.healthCheck else None
    try:
        env = await update_environment(
            db,
            user=user,
            project_id=projectId,
            env_id=envId,
            name=name,
            base_url=base_url,
            variables=variables,
            secrets=secrets,
            health_check=health_check if "healthCheck" in fields_set else UNSET,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    env = await get_environment(db, user=user, project_id=projectId, env_id=env.id)
    return ApiResponse(data=_to_public(env), requestId=request_id)


@router.delete("/{envId}", response_model=ApiResponse[dict])
async def delete(
    projectId: uuid.UUID,
    envId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[dict]:
    try:
        await delete_environment(db, user=user, project_id=projectId, env_id=envId)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={}, requestId=request_id)
