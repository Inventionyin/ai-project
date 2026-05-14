from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, UnixTs

DOC_SOURCE_TYPES = {"PRD", "SPEC", "PROTOTYPE", "DOCX", "PDF", "MARKDOWN", "URL", "MANUAL", "OTHER"}
DOC_STATUSES = {"DRAFT", "REVIEWING", "PUBLISHED", "ARCHIVED"}


def normalize_doc_source_type(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized == "MD":
        normalized = "MARKDOWN"
    if normalized not in DOC_SOURCE_TYPES:
        return "OTHER"
    return normalized


def normalize_doc_status(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized == "ACTIVE":
        normalized = "PUBLISHED"
    if normalized in {"DEPRECATED", "DISABLED"}:
        normalized = "ARCHIVED"
    if normalized not in DOC_STATUSES:
        return "DRAFT"
    return normalized


ANALYSIS_STATUSES = {"DRAFT", "GENERATED", "REVIEWED", "ARCHIVED"}
RISK_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
TEST_POINT_STATUSES = {"DRAFT", "ACCEPTED", "REJECTED", "CONVERTED"}
SCENARIO_TYPES = {"POSITIVE", "NEGATIVE", "BOUNDARY", "EXCEPTION"}
CASE_DRAFT_STATUSES = {"PENDING", "APPROVED", "REJECTED", "COMMITTED"}


def normalize_analysis_status(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized not in ANALYSIS_STATUSES:
        return "GENERATED"
    return normalized


def normalize_risk_level(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized not in RISK_LEVELS:
        return "MEDIUM"
    return normalized


def normalize_test_point_status(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized not in TEST_POINT_STATUSES:
        return "DRAFT"
    return normalized


def normalize_scenario_type(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized not in SCENARIO_TYPES:
        return "POSITIVE"
    return normalized


def empty_analysis_payload() -> dict:
    return {
        "featurePoints": [],
        "businessRules": [],
        "testPoints": [],
        "riskPoints": [],
        "boundaryCases": [],
        "coverageSuggestions": [],
    }


class RequirementDocCreateRequest(BaseSchema):
    title: str = Field(min_length=1, max_length=255)
    sourceType: str = Field(min_length=1, max_length=32)
    ownerId: IdStr | None = None
    status: str = Field(default="DRAFT", min_length=1, max_length=32)
    tags: list[str] = Field(default_factory=list)


class RequirementDocUpdateRequest(BaseSchema):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    sourceType: str | None = Field(default=None, min_length=1, max_length=32)
    ownerId: IdStr | None = None
    status: str | None = Field(default=None, min_length=1, max_length=32)
    tags: list[str] | None = None


class RequirementDocDetail(BaseSchema):
    id: IdStr
    projectId: IdStr
    title: str
    sourceType: str
    ownerId: IdStr | None = None
    status: str
    tags: list[str] = Field(default_factory=list)
    createdBy: IdStr
    createdAt: UnixTs
    updatedAt: UnixTs


class RequirementDocVersionDetail(BaseSchema):
    id: IdStr
    docId: IdStr
    projectId: IdStr
    version: int = Field(ge=1)
    fileName: str
    fileType: str
    storageUrl: str
    contentHash: str
    parsedTextUrl: str | None = None
    parsedTextPreview: str | None = None
    changeSummary: str | None = None
    effectiveScope: str | None = None
    publishedAt: UnixTs | None = None
    createdBy: IdStr
    createdAt: UnixTs
    updatedAt: UnixTs


class RequirementAnalysisGenerateRequest(BaseSchema):
    instruction: str | None = Field(default=None, max_length=2000)


class RequirementAnalysisUpdateRequest(BaseSchema):
    status: str | None = Field(default=None, min_length=1, max_length=32)
    summary: str | None = Field(default=None, max_length=10000)
    riskLevel: str | None = Field(default=None, min_length=1, max_length=16)
    coverageScore: float | None = Field(default=None, ge=0.0, le=1.0)
    analysis: dict | None = None


class RequirementAnalysisDetail(BaseSchema):
    id: IdStr
    projectId: IdStr
    docId: IdStr
    docVersionId: IdStr
    status: str
    summary: str | None = None
    riskLevel: str
    coverageScore: float | None = None
    analysis: dict = Field(default_factory=empty_analysis_payload)
    aiTaskId: IdStr | None = None
    createdBy: IdStr
    updatedBy: IdStr | None = None
    createdAt: UnixTs
    updatedAt: UnixTs


class RequirementTestPointUpdateRequest(BaseSchema):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    scenarioType: str | None = Field(default=None, min_length=1, max_length=32)
    priority: str | None = Field(default=None, min_length=1, max_length=16)
    riskLevel: str | None = Field(default=None, min_length=1, max_length=16)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    aiMeta: dict | None = None


class RequirementTestPointDetail(BaseSchema):
    id: IdStr
    projectId: IdStr
    analysisId: IdStr
    title: str
    description: str | None = None
    scenarioType: str
    priority: str
    riskLevel: str
    sourcePath: str | None = None
    status: str
    aiMeta: dict = Field(default_factory=dict)
    createdBy: IdStr
    updatedBy: IdStr | None = None
    createdAt: UnixTs
    updatedAt: UnixTs


class GenerateCaseDraftsRequest(BaseSchema):
    mode: str = Field(default="ACCEPTED_ONLY", min_length=1, max_length=32)
    testPointIds: list[IdStr] = Field(default_factory=list)
    forceRegenerate: bool = False


class GeneratedCaseDraftDetail(BaseSchema):
    id: IdStr
    projectId: IdStr
    analysisId: IdStr
    testPointId: IdStr | None = None
    title: str
    type: str
    priority: str
    preconditions: str | None = None
    steps: list = Field(default_factory=list)
    expectedResults: list = Field(default_factory=list)
    testData: dict = Field(default_factory=dict)
    status: str
    confidence: float | None = None
    aiMeta: dict = Field(default_factory=dict)
    createdBy: IdStr
    reviewedBy: IdStr | None = None
    createdAt: UnixTs
    updatedAt: UnixTs


class RequirementCaseLinkDetail(BaseSchema):
    id: IdStr
    projectId: IdStr
    docId: IdStr
    docVersionId: IdStr
    analysisId: IdStr
    testPointId: IdStr | None = None
    caseDraftId: IdStr
    testcaseId: IdStr
    testcaseTitle: str | None = None
    linkType: str
    confidence: float | None = None
    createdBy: IdStr
    createdAt: UnixTs


class BulkApproveCaseDraftsRequest(BaseSchema):
    draftIds: list[IdStr] = Field(min_length=1)


class BulkApproveCaseDraftsResult(BaseSchema):
    approvedDraftCount: int
    createdTestCaseCount: int
    testCaseIds: list[IdStr] = Field(default_factory=list)
