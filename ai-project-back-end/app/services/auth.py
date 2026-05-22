from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, create_access_token, get_password_hash, verify_password
from app.models.enums import UserStatus
from app.models.tenant import Tenant
from app.models.user import User


async def _get_default_tenant(db: AsyncSession) -> Tenant:
    tenants = (await db.execute(select(Tenant).order_by(Tenant.created_at.asc()).limit(2))).scalars().all()
    if len(tenants) == 1:
        return tenants[0]

    tenant = (
        await db.execute(
            select(Tenant)
            .where(Tenant.name == "Default Tenant")
            .order_by(Tenant.created_at.asc(), Tenant.id.asc())
            .limit(1)
        )
    ).scalars().first()
    if tenant is not None:
        return tenant

    if tenants:
        return tenants[0]

    tenant = Tenant(name="Default Tenant")
    db.add(tenant)
    await db.flush()
    return tenant


async def register_user(
    db: AsyncSession,
    *,
    phone: str,
    username: str,
    password: str,
    captcha: str,
) -> User:
    """
    Register a new user with phone + username.

    Captcha is verified with a temporary stub rule: only "123456" is accepted.
    """
    if captcha.strip() != "123456":
        raise HTTPException(status_code=400, detail="Invalid captcha")

    normalized_phone = phone.strip()
    normalized_username = username.strip()
    if not normalized_phone:
        raise HTTPException(status_code=400, detail="Invalid phone")
    if not normalized_username:
        raise HTTPException(status_code=400, detail="Invalid username")

    tenant = await _get_default_tenant(db)

    existing_phone = (
        await db.execute(
            select(User.id).where(
                User.tenant_id == tenant.id,
                User.phone == normalized_phone,
            )
        )
    ).scalars().first()
    if existing_phone is not None:
        raise HTTPException(status_code=409, detail="Phone already exists")

    existing_username = (
        await db.execute(
            select(User.id).where(
                User.tenant_id == tenant.id,
                User.username == normalized_username,
            )
        )
    ).scalars().first()
    if existing_username is not None:
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        tenant_id=tenant.id,
        phone=normalized_phone,
        username=normalized_username,
        name=normalized_username,
        status=UserStatus.ACTIVE,
        hashed_password=get_password_hash(password),
        roles_json=["Viewer"],
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(
    db: AsyncSession,
    *,
    username_or_email: str,
    password: str,
) -> User:
    value = username_or_email.strip()
    if not value:
        raise HTTPException(status_code=401, detail="请输入正确的用户名和密码")

    stmt = select(User).where(or_(User.email == value, User.username == value, User.phone == value))
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="请输入正确的用户名和密码")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="User is disabled")
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="请输入正确的用户名和密码")
    return user


def issue_access_token(*, user: User) -> tuple[str, int]:
    roles = frozenset(r.strip() for r in (user.roles_json or []) if r and r.strip())
    return create_access_token(payload=TokenPayload(user_id=user.id, tenant_id=user.tenant_id, roles=roles))
