from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ApiResponse(BaseSchema, Generic[T]):
    code: int = Field(default=0)
    message: str = Field(default="ok")
    data: T | None = None
    requestId: str = Field(min_length=1, max_length=64)


class PageData(BaseSchema, Generic[T]):
    page: int = Field(ge=1)
    pageSize: int = Field(ge=1, le=200)
    total: int = Field(ge=0)
    items: list[T]

