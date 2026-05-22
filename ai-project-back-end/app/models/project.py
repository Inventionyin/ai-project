from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ProjectRole
from app.models.mixins import CreatedAtMixin


class Project(Base, CreatedAtMixin):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_projects_tenant_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    ci_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ci_token_hint: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ci_token_rotated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ci_token_last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ci_token_rotated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    ci_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ci_token_revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ci_token_revoked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    ci_token_revoked_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ci_token_leak_reported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ci_token_leak_reported_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    ci_token_leak_report_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ci_token_allowed_runner_types: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    ci_token_allowed_testcase_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    ci_token_max_testcase_count: Mapped[int | None] = mapped_column(nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="projects")
    owner: Mapped["User"] = relationship(back_populates="owned_projects", foreign_keys=[owner_id])

    members: Mapped[list["ProjectMember"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    environments: Mapped[list["Environment"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    testcases: Mapped[list["TestCase"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    suites: Mapped[list["Suite"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    api_collections: Mapped[list["ApiCollection"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    test_data_sets: Mapped[list["TestDataSet"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    runs: Mapped[list["Run"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    ai_records: Mapped[list["AiRecord"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    ci_tokens: Mapped[list["ProjectCiToken"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectCiToken(Base, CreatedAtMixin):
    __tablename__ = "project_ci_tokens"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_project_ci_tokens_project_name"),
        UniqueConstraint("token_hash", name="uq_project_ci_tokens_token_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, default="primary")
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    token_hint: Mapped[str] = mapped_column(String(32), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rotated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rotated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    leak_reported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    leak_reported_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    leak_report_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    allowed_runner_types: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    allowed_testcase_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    max_testcase_count: Mapped[int | None] = mapped_column(nullable=True)

    project: Mapped["Project"] = relationship(back_populates="ci_tokens")


class ProjectMember(Base, CreatedAtMixin):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[ProjectRole] = mapped_column(Enum(ProjectRole, name="project_role"), nullable=False, default=ProjectRole.VIEWER)

    project: Mapped["Project"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")
