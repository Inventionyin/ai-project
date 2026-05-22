from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from jose import JWTError, jwt
import bcrypt

from app.core.config import get_settings



@dataclass(frozen=True, slots=True)
class TokenPayload:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    roles: frozenset[str]


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(*, payload: TokenPayload, expires_in: int | None = None) -> tuple[str, int]:
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise HTTPException(status_code=500, detail="JWT secret key is not configured")

    ttl = int(expires_in if expires_in is not None else settings.jwt_access_token_expires_in)
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=ttl)

    encoded = jwt.encode(
        {
            "user_id": str(payload.user_id),
            "tenant_id": str(payload.tenant_id),
            "roles": sorted(payload.roles),
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded, ttl


def decode_access_token(token: str) -> TokenPayload:
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise HTTPException(status_code=500, detail="JWT secret key is not configured")

    try:
        data = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    user_id_raw = data.get("user_id")
    tenant_id_raw = data.get("tenant_id")
    roles_raw = data.get("roles") or []

    try:
        user_id = uuid.UUID(str(user_id_raw))
        tenant_id = uuid.UUID(str(tenant_id_raw))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token payload") from exc

    if not isinstance(roles_raw, list):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    roles = frozenset(str(r).strip() for r in roles_raw if str(r).strip())
    return TokenPayload(user_id=user_id, tenant_id=tenant_id, roles=roles)
