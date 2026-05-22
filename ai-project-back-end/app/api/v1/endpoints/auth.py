from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_request_id, to_unix_ts
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponseData, LogoutResponseData, MeResponseData, RegisterRequest, RegisterResponseData
from app.schemas.common import ApiResponse
from app.services.auth import authenticate_user, issue_access_token, register_user

router = APIRouter(prefix="/auth")

@router.post("/register", response_model=ApiResponse[RegisterResponseData])
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[RegisterResponseData]:
    try:
        user = await register_user(
            db,
            phone=payload.phone,
            username=payload.username,
            password=payload.password,
            captcha=payload.captcha,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ApiResponse(
        data=RegisterResponseData(
            userId=str(user.id),
            phone=user.phone or "",
            username=user.username or "",
            createdAt=to_unix_ts(user.created_at),
        ),
        requestId=request_id,
    )


@router.post("/login", response_model=ApiResponse[LoginResponseData])
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[LoginResponseData]:
    user = await authenticate_user(db, username_or_email=payload.username, password=payload.password)
    access_token, expires_in = issue_access_token(user=user)
    return ApiResponse(
        data=LoginResponseData(accessToken=access_token, expiresIn=expires_in),
        requestId=request_id,
    )


@router.post("/logout", response_model=ApiResponse[LogoutResponseData])
async def logout(
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[LogoutResponseData]:
    return ApiResponse(
        data=LogoutResponseData(),
        requestId=request_id,
    )


@router.get("/me", response_model=ApiResponse[MeResponseData])
async def me(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    request_id: str = Depends(get_request_id),
) -> ApiResponse[MeResponseData]:
    db_user = (
        await db.execute(
            select(User).where(User.id == user.id, User.tenant_id == user.tenant_id)
        )
    ).scalar_one_or_none()
    if db_user is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    return ApiResponse(
        data=MeResponseData(
            userId=str(db_user.id),
            email=db_user.email,
            phone=db_user.phone,
            username=db_user.username,
            name=db_user.name,
            roles=list(db_user.roles_json or []),
            tenantId=str(db_user.tenant_id),
        ),
        requestId=request_id,
    )
