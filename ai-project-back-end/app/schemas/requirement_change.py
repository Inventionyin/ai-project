from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, UnixTs
from app.schemas.requirement import empty_analysis_payload


class RequirementAnalysisRevisionDetail(BaseSchema):
    id: IdStr
    projectId: IdStr
    analysisId: IdStr
    docId: IdStr
    docVersionId: IdStr
    revisionNo: int = Field(ge=1)
    changeReason: str
    summary: str | None = None
    riskLevel: str
    coverageScore: float | None = None
    analysis: dict = Field(default_factory=empty_analysis_payload)
    createdBy: IdStr
    createdAt: UnixTs


class RequirementAnalysisRollbackRequest(BaseSchema):
    revisionId: IdStr


class RequirementChangeSetCreateRequest(BaseSchema):
    baselineVersionId: IdStr
    targetVersionId: IdStr


class RequirementChangeItemDetail(BaseSchema):
    id: IdStr
    changeType: str
    title: str
    description: str | None = None
    impactLevel: str
    sourcePath: str | None = None


class RequirementChangeSetDetail(BaseSchema):
    id: IdStr
    projectId: IdStr
    docId: IdStr
    baselineVersionId: IdStr
    targetVersionId: IdStr
    summary: str | None = None
    status: str
    items: list[RequirementChangeItemDetail] = Field(default_factory=list)
    createdBy: IdStr
    createdAt: UnixTs
    updatedAt: UnixTs


class RequirementRegressionCaseDetail(BaseSchema):
    id: IdStr
    testcaseId: IdStr
    testcaseTitle: str | None = None
    priority: str
    reason: str | None = None
    sourcePaths: list[str] = Field(default_factory=list)


class RequirementRegressionSetDetail(BaseSchema):
    id: IdStr
    projectId: IdStr
    changeSetId: IdStr
    summary: str | None = None
    status: str
    cases: list[RequirementRegressionCaseDetail] = Field(default_factory=list)
    createdBy: IdStr
    createdAt: UnixTs
    updatedAt: UnixTs
