from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import get_current_user
from app.core.config import get_settings


@pytest.mark.anyio
async def test_current_user_rejects_impersonation_headers_by_default(monkeypatch) -> None:
    monkeypatch.delenv("AUTH_HEADER_IMPERSONATION_ENABLED", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(HTTPException) as exc:
            await get_current_user(
                authorization=None,
                x_user_id=str(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")),
                x_tenant_id=str(uuid.UUID("11111111-1111-1111-1111-111111111111")),
                x_roles="ADMIN",
            )

        assert exc.value.status_code == 401
        assert exc.value.detail == "Not authenticated"
    finally:
        get_settings.cache_clear()


@pytest.mark.anyio
async def test_current_user_allows_impersonation_headers_only_when_explicitly_enabled(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_HEADER_IMPERSONATION_ENABLED", "true")
    get_settings.cache_clear()
    try:
        user = await get_current_user(
            authorization=None,
            x_user_id=str(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")),
            x_tenant_id=str(uuid.UUID("11111111-1111-1111-1111-111111111111")),
            x_roles="ADMIN,EDITOR",
        )

        assert user.id == uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        assert user.tenant_id == uuid.UUID("11111111-1111-1111-1111-111111111111")
        assert user.roles == frozenset({"ADMIN", "EDITOR"})
    finally:
        get_settings.cache_clear()
