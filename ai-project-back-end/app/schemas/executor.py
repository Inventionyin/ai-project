from __future__ import annotations

from app.schemas.common import BaseSchema


class ExecutorCreateRequest(BaseSchema):
    name: str
    executorType: str
    description: str | None = None
    config: dict | None = None
    version: str | None = None


class ExecutorUpdateRequest(BaseSchema):
    name: str | None = None
    description: str | None = None
    config: dict | None = None
    enabled: bool | None = None
    version: str | None = None


class ExecutorDetail(BaseSchema):
    id: str
    projectId: str
    name: str
    executorType: str
    description: str | None = None
    config: dict | None = None
    enabled: bool
    version: str | None = None
    createdBy: str | None = None
    createdAt: int
    updatedAt: int
