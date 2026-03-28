from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Header, HTTPException, Request

from app.core.security import decode_access_token


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: uuid.UUID
    tenant_id: uuid.UUID
    roles: frozenset[str]

def to_unix_ts(dt) -> int:
    return int(dt.timestamp())


async def get_request_id(request: Request) -> str:
    request_id = request.headers.get("X-Request-Id") or request.headers.get("X-RequestId")
    if request_id:
        return request_id[:64]
    return f"req_{uuid.uuid4().hex[:16]}"


async def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_roles: str | None = Header(default=None, alias="X-Roles"),
) -> CurrentUser:
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
            payload = decode_access_token(parts[1].strip())
            return CurrentUser(id=payload.user_id, tenant_id=payload.tenant_id, roles=payload.roles)

    if not x_user_id or not x_tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user_id = uuid.UUID(x_user_id)
        tenant_id = uuid.UUID(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid X-User-Id or X-Tenant-Id") from exc

    roles: frozenset[str]
    if x_roles:
        roles = frozenset(r.strip() for r in x_roles.split(",") if r.strip())
    else:
        roles = frozenset()

    return CurrentUser(id=user_id, tenant_id=tenant_id, roles=roles)
