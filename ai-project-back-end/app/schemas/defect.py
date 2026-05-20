from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, UnixTs


class DefectCreateRequest(BaseSchema):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    severity: str = Field(default="P2", min_length=1, max_length=16)


class DefectImportItem(BaseSchema):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    severity: str = Field(default="P2", min_length=1, max_length=16)
    runId: IdStr | None = None
    caseRunId: IdStr | None = None
    testcaseId: IdStr | None = None
    source: str | None = Field(default=None, max_length=128)


class DefectImportRequest(BaseSchema):
    items: list[DefectImportItem] = Field(min_length=1, max_length=1000)


class DefectImportErrorItem(BaseSchema):
    index: int = Field(ge=0)
    title: str | None = None
    error: str = Field(min_length=1, max_length=128)


class DefectImportResult(BaseSchema):
    total: int = Field(ge=0)
    success: int = Field(ge=0)
    failed: int = Field(ge=0)
    errors: list[DefectImportErrorItem]


class DefectAssignRequest(BaseSchema):
    assigneeId: IdStr
    note: str | None = Field(default=None, max_length=5000)


class DefectTransitionRequest(BaseSchema):
    toStatus: str = Field(min_length=1, max_length=32)
    note: str | None = Field(default=None, max_length=5000)


class DefectListItem(BaseSchema):
    id: IdStr
    projectId: IdStr
    title: str
    description: str | None = None
    status: str
    severity: str
    assigneeId: str | None = None
    reporterId: IdStr
    createdBy: IdStr
    createdAt: UnixTs
    updatedAt: UnixTs


class DefectDetail(DefectListItem):
    pass


class DefectClusterItem(BaseSchema):
    clusterKey: str = Field(min_length=1, max_length=128)
    count: int = Field(ge=1)
    sampleTitles: list[str]
    rootCauseHint: str = Field(min_length=1, max_length=255)
    confidence: float = Field(ge=0, le=1)


class DefectRiskHint(BaseSchema):
    defectId: IdStr
    title: str
    status: str
    severity: str
    updatedAt: UnixTs
    riskScore: float = Field(ge=0)
    hint: str = Field(min_length=1, max_length=255)
