from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin


class ApiTarget(Base, TimestampMixin):
    __tablename__ = "api_targets"
    __table_args__ = (Index("uq_api_targets_tenant_project_name", "tenant_id", "project_id", "name", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    default_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    default_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    headers_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    auth_ref_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=10000)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
