from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text, desc
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import CreatedAtMixin, TimestampMixin


class AiImportJob(Base, TimestampMixin):
    __tablename__ = "ai_import_jobs"
    __table_args__ = (
        CheckConstraint("source_type IN ('PRD_DOC', 'FIGMA_LINK', 'HTML_DOC')"),
        CheckConstraint("status IN ('PENDING', 'UPLOADED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'COMMITTED')"),
        Index("ix_ai_import_jobs_tenant_project_created", "tenant_id", "project_id", desc("created_at")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_ref_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    generate_config_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    skill_config_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)


class AiImportItem(Base, CreatedAtMixin):
    __tablename__ = "ai_import_items"
    __table_args__ = (
        Index("ix_ai_import_items_job", "job_id"),
        Index("ix_ai_import_items_project_story", "project_id", "story"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_import_jobs.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    priority: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    feature: Mapped[str | None] = mapped_column(String(128), nullable=True)
    epic: Mapped[str | None] = mapped_column(String(128), nullable=True)
    story: Mapped[str | None] = mapped_column(String(128), nullable=True)
    task: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps_json: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    api_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    api_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tags_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    ai_meta_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    selected: Mapped[bool] = mapped_column(nullable=False, default=True)
