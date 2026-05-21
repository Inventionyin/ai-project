from __future__ import annotations

from typing import Literal

from pydantic import Field

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


TrialOperationImportType = Literal["requirements", "testcases", "defects"]
TrialOperationImportStatus = Literal["SUCCESS", "PARTIAL_SUCCESS", "FAILED"]


class TrialOperationImportRecordCreateRequest(BaseSchema):
    importType: TrialOperationImportType
    fileName: str = Field(min_length=1, max_length=255)
    status: TrialOperationImportStatus
    totalRows: int = Field(ge=0)
    successRows: int = Field(ge=0)
    failedRows: int = Field(ge=0)
    summary: str | None = Field(default=None, max_length=255)
    detail: dict = Field(default_factory=dict)


class TrialOperationImportRecordItem(BaseSchema):
    id: str
    projectId: str | None = None
    importType: TrialOperationImportType
    fileName: str
    status: TrialOperationImportStatus
    totalRows: int
    successRows: int
    failedRows: int
    summary: str | None = None
    detail: dict
    createdBy: str | None = None
    createdAt: int
