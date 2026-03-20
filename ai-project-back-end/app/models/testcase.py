from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text, desc
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import Priority, TestCaseStatus, TestCaseType
from app.models.mixins import CreatedAtMixin, TimestampMixin


class TestCase(Base, TimestampMixin):
    __tablename__ = "testcases"
    __table_args__ = (Index("ix_testcases_project_updated_at_desc", "project_id", desc("updated_at")),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[TestCaseType] = mapped_column(Enum(TestCaseType, name="testcase_type"), nullable=False)
    priority: Mapped[Priority] = mapped_column(Enum(Priority, name="priority"), nullable=False)
    status: Mapped[TestCaseStatus] = mapped_column(Enum(TestCaseStatus, name="testcase_status"), nullable=False, default=TestCaseStatus.DRAFT)

    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    feature: Mapped[str | None] = mapped_column(String(128), nullable=True)
    story: Mapped[str | None] = mapped_column(String(128), nullable=True)
    api_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    api_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ai_meta_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    generated_by_ai: Mapped[bool] = mapped_column(nullable=False, default=False)

    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    project: Mapped["Project"] = relationship(back_populates="testcases")
    versions: Mapped[list["TestCaseVersion"]] = relationship(back_populates="testcase", cascade="all, delete-orphan")


class TestCaseVersion(Base, CreatedAtMixin):
    __tablename__ = "testcase_versions"
    __table_args__ = (Index("ix_testcase_versions_testcase_version", "testcase_id", "version", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    testcase_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("testcases.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    testcase: Mapped["TestCase"] = relationship(back_populates="versions")
