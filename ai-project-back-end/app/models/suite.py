from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, CreatedAtMixin


class Suite(Base, TimestampMixin):
    __tablename__ = "suites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    project: Mapped["Project"] = relationship(back_populates="suites")
    items: Mapped[list["SuiteItem"]] = relationship(back_populates="suite", cascade="all, delete-orphan")
    runs: Mapped[list["Run"]] = relationship(back_populates="suite")


class SuiteItem(Base, CreatedAtMixin):
    __tablename__ = "suite_items"
    __table_args__ = (
        Index("ix_suite_items_suite_order_no", "suite_id", "order_no", unique=True),
        Index("ix_suite_items_suite_id", "suite_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    suite_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suites.id"), nullable=False, index=True)
    testcase_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("testcases.id"), nullable=False, index=True)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    params_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    suite: Mapped["Suite"] = relationship(back_populates="items")
    testcase: Mapped["TestCase"] = relationship()

