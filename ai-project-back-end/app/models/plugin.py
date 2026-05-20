from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import PluginInstallStatus, PluginStatus
from app.models.mixins import TimestampMixin


class Plugin(TimestampMixin, Base):
    __tablename__ = "plugins"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plugin_type: Mapped[str] = mapped_column(String(50), default="executor", nullable=False)
    config_schema_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    entry_point: Mapped[str | None] = mapped_column(String(500), nullable=True)
    min_platform_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    icon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=PluginStatus.AVAILABLE.value, nullable=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_plugin_tenant_slug"),)


class PluginInstallation(TimestampMixin, Base):
    __tablename__ = "plugin_installations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    plugin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plugins.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=PluginInstallStatus.INSTALLING.value, nullable=False)
    config_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    installed_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    installed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (UniqueConstraint("project_id", "plugin_id", name="uq_plugin_install_project"),)
