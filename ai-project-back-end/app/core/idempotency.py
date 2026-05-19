"""Idempotency key helpers for cross-module request deduplication."""
from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def check_idempotency_key(
    db: AsyncSession,
    *,
    key: str,
    tenant_id: str,
) -> dict[str, Any] | None:
    """Check if an idempotency key was already used.

    Returns a dict with the cached run info if found, otherwise ``None``.
    """
    from app.models.run import Run

    existing = await db.scalar(
        select(Run).where(Run.idempotency_key == key, Run.tenant_id == tenant_id)
    )
    if existing:
        status_value = (
            existing.status.value
            if hasattr(existing.status, "value")
            else str(existing.status)
        )
        return {
            "runId": str(existing.id),
            "status": status_value,
        }
    return None


def make_idempotency_key(*parts: str) -> str:
    """Generate a deterministic idempotency key from the given parts.

    Example::

        key = make_idempotency_key(str(project_id), str(suite_id), "deploy")
    """
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
