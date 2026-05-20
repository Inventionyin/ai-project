from __future__ import annotations

from app.schemas.common import BaseSchema


class DocParseJobCreateRequest(BaseSchema):
    docId: str
    docVersionId: str


class DocParseJobDetail(BaseSchema):
    id: str
    projectId: str
    docId: str
    docVersionId: str
    status: str
    attempts: int
    maxRetries: int
    errorMessage: str | None = None
    result: dict | None = None
    createdBy: str | None = None
    createdAt: int
    updatedAt: int


class DocParseJobRetryRequest(BaseSchema):
    job_id: str
