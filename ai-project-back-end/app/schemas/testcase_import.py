from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema


class TestCaseImportErrorItem(BaseSchema):
    rowNumber: int = Field(ge=1)
    testCaseId: str | None = Field(default=None, min_length=1, max_length=64)
    field: str | None = Field(default=None, min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=5000)


class TestCaseImportData(BaseSchema):
    importedCount: int = Field(ge=0)
    failedCount: int = Field(ge=0)
    errors: list[TestCaseImportErrorItem] = Field(default_factory=list)

