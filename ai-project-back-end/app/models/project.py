from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
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
