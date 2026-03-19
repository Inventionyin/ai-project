from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin


class ApiCollection(Base, TimestampMixin):
    __tablename__ = "api_collections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    variables_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    project: Mapped["Project"] = relationship(back_populates="api_collections")
    groups: Mapped[list["ApiCollectionGroup"]] = relationship(
        back_populates="collection",
        cascade="all, delete-orphan",
    )
    requests: Mapped[list["ApiRequest"]] = relationship(back_populates="collection", cascade="all, delete-orphan")


class ApiCollectionGroup(Base, TimestampMixin):
    __tablename__ = "api_collection_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_collections.id"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    collection: Mapped["ApiCollection"] = relationship(back_populates="groups")
    requests: Mapped[list["ApiRequest"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class ApiRequest(Base, TimestampMixin):
    __tablename__ = "api_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    collection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("api_collections.id"), nullable=False, index=True)
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_collection_groups.id"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)

    headers_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    auth_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    body_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    asserts_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    collection: Mapped["ApiCollection"] = relationship(back_populates="requests")
    group: Mapped["ApiCollectionGroup | None"] = relationship(back_populates="requests")

