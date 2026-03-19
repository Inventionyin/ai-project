from __future__ import annotations

import uuid

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, desc
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import WorkerStatus
from app.models.mixins import TimestampMixin


class Worker(Base, TimestampMixin):
    __tablename__ = "workers"
    __table_args__ = (Index("ix_workers_tenant_last_seen_at_desc", "tenant_id", desc("last_seen_at")),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    capabilities_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    slots: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[WorkerStatus] = mapped_column(Enum(WorkerStatus, name="worker_status"), nullable=False, default=WorkerStatus.OFFLINE)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="workers")
    jobs: Mapped[list["Job"]] = relationship(back_populates="worker")
