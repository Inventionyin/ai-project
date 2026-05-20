from __future__ import annotations

from app.schemas.common import BaseSchema


class AiJobRecordListItem(BaseSchema):
    id: str
    projectId: str
    jobType: str
    status: str
    triggerSource: str
    summary: str | None = None
    createdBy: str | None = None
    createdAt: int


class AuditLogListItem(BaseSchema):
    id: str
    projectId: str | None = None
    module: str | None = None
    action: str
    resourceType: str
    resourceId: str
    summary: str | None = None
    detail: dict
    userId: str | None = None
    createdAt: int
