from __future__ import annotations

import uuid

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint, desc
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ArtifactType, CaseRunStatus, JobStatus, RunStatus, TriggerType
from app.models.mixins import TimestampMixin, CreatedAtMixin


class Run(Base, TimestampMixin):
    __tablename__ = "runs"
    __table_args__ = (
        Index("ix_runs_project_start_at_desc", "project_id", desc("start_at")),
        UniqueConstraint("tenant_id", "project_id", "idempotency_key", name="uq_runs_tenant_project_idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    suite_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("suites.id"), nullable=True, index=True)
    env_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("environments.id"), nullable=True, index=True)

    trigger_type: Mapped[TriggerType] = mapped_column(Enum(TriggerType, name="trigger_type"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, name="run_status"), nullable=False, default=RunStatus.QUEUED)

    start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    summary_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    project: Mapped["Project"] = relationship(back_populates="runs")
    suite: Mapped["Suite"] = relationship(back_populates="runs")
    jobs: Mapped[list["Job"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    case_runs: Mapped[list["CaseRun"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False, index=True)
    worker_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=True, index=True)

    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, name="job_status"), nullable=False, default=JobStatus.QUEUED)
    start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    meta_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    run: Mapped["Run"] = relationship(back_populates="jobs")
    worker: Mapped["Worker"] = relationship(back_populates="jobs")


class CaseRun(Base, TimestampMixin):
    __tablename__ = "case_runs"
    __table_args__ = (Index("ix_case_runs_run_status", "run_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False, index=True)
    testcase_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("testcases.id"), nullable=False, index=True)

    status: Mapped[CaseRunStatus] = mapped_column(Enum(CaseRunStatus, name="case_run_status"), nullable=False, default=CaseRunStatus.QUEUED)
    start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    error_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    run: Mapped["Run"] = relationship(back_populates="case_runs")
    testcase: Mapped["TestCase"] = relationship()
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="case_run", cascade="all, delete-orphan")
    issue_links: Mapped[list["IssueLink"]] = relationship(back_populates="case_run", cascade="all, delete-orphan")


class Artifact(Base, CreatedAtMixin):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False, index=True)
    case_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("case_runs.id"), nullable=True, index=True)

    type: Mapped[ArtifactType] = mapped_column(Enum(ArtifactType, name="artifact_type"), nullable=False)
    storage_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    meta_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    run: Mapped["Run"] = relationship(back_populates="artifacts")
    case_run: Mapped["CaseRun"] = relationship(back_populates="artifacts")
