from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class DefectProviderConfigDetail(BaseSchema):
    id: str
    projectId: str
    provider: str
    name: str
    baseUrl: str
    enabled: bool
    syncStatus: str
    lastSyncAt: int | None = None
    lastError: str | None = None


class DefectProviderConfigCreateRequest(BaseSchema):
    provider: str
    name: str
    baseUrl: str
    apiToken: str = ""
    username: str = ""
    projectKey: str = ""


class DefectProviderConfigUpdateRequest(BaseSchema):
    name: str | None = None
    baseUrl: str | None = None
    apiToken: str | None = None
    enabled: bool | None = None
