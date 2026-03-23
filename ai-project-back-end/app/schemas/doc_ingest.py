from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import UnixTs


class DocParserInfo(BaseSchema):
    name: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=64)


class DocMeta(BaseSchema):
    jobId: str | None = Field(default=None, max_length=128)
    sourceType: str = Field(min_length=1, max_length=32)
    fileName: str = Field(min_length=1, max_length=255)
    fileHash: str | None = Field(default=None, max_length=128)
    parsedAt: UnixTs
    parser: DocParserInfo
    language: str | None = Field(default=None, max_length=16)
    pageCount: int | None = Field(default=None, ge=0)


class DocSection(BaseSchema):
    id: str = Field(min_length=1, max_length=64)
    title: str | None = Field(default=None, max_length=255)
    level: int | None = Field(default=None, ge=0, le=12)
    text: str = Field(min_length=1, max_length=50000)
    page: int | None = Field(default=None, ge=0)
    tokensEstimate: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)


class ApiCandidate(BaseSchema):
    id: str = Field(min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=100)
    feature: str | None = Field(default=None, max_length=128)
    method: str | None = Field(default=None, max_length=16)
    url: str | None = Field(default=None, max_length=1024)
    params: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    expectedStatusCode: int | None = Field(default=None, ge=100, le=599)
    expectedResult: str | None = Field(default=None, max_length=5000)
    tags: list[str] = Field(default_factory=list, max_length=50)
    sourceRefs: dict = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)


class DocTable(BaseSchema):
    id: str = Field(min_length=1, max_length=64)
    headers: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    page: int | None = Field(default=None, ge=0)
    confidence: float = Field(ge=0.0, le=1.0)


class QualityIssue(BaseSchema):
    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=500)
    severity: str = Field(min_length=1, max_length=16)


class QualityReport(BaseSchema):
    hasStructuredApis: bool
    apiCandidateCount: int = Field(ge=0)
    methodCoverage: float = Field(ge=0.0, le=1.0)
    urlCoverage: float = Field(ge=0.0, le=1.0)
    expectedCoverage: float = Field(ge=0.0, le=1.0)
    issues: list[QualityIssue] = Field(default_factory=list)


class DocRaw(BaseSchema):
    textDigest: str = Field(min_length=0, max_length=20000)
    attachments: list[str] = Field(default_factory=list)


class DocParseStatus(str):
    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"


class DocParseResult(BaseSchema):
    meta: DocMeta
    sections: list[DocSection] = Field(default_factory=list)
    apiCandidates: list[ApiCandidate] = Field(default_factory=list)
    tables: list[DocTable] = Field(default_factory=list)
    quality: QualityReport
    raw: DocRaw
    status: str = Field(min_length=4, max_length=6)

class DocCsvGenerateData(BaseSchema):
    fileName: str = Field(min_length=1, max_length=255)
    csvText: str
    itemCount: int = Field(ge=0)
    status: str = Field(min_length=4, max_length=6)
