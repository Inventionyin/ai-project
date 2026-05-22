from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, UnixTs, VersionStr

SceneStr = Annotated[str, Field(min_length=1, max_length=64)]
TemplateNameStr = Annotated[str, Field(min_length=1, max_length=128)]


class PromptTemplateCreateRequest(BaseSchema):
    scene: SceneStr
    name: TemplateNameStr
    version: VersionStr
    content: Annotated[str, Field(min_length=1, max_length=20_000)]
    variablesJson: dict[str, object] = Field(default_factory=dict)
    isActive: bool = True

    @property
    def variables(self) -> dict[str, object]:
        return self.variablesJson


class PromptTemplateUpdateRequest(BaseSchema):
    content: Annotated[str, Field(min_length=1, max_length=20_000)] | None = None
    variablesJson: dict[str, object] | None = None
    isActive: bool | None = None

    @property
    def variables(self) -> dict[str, object] | None:
        return self.variablesJson


class PromptTemplateActivateRequest(BaseSchema):
    isActive: bool = True


class PromptTemplateGovernanceItem(BaseSchema):
    scene: str
    name: str
    activeVersion: str | None = None
    latestVersion: str
    versionCount: int
    policy: str = "SINGLE_ACTIVE"


class PromptTemplateRollbackRequest(BaseSchema):
    scene: SceneStr
    name: TemplateNameStr
    targetVersion: VersionStr


class PromptTemplateRollbackResult(BaseSchema):
    scene: str
    name: str
    activeVersion: str
    versionCount: int
    policy: str = "SINGLE_ACTIVE"


class PromptTemplateDetail(BaseSchema):
    id: IdStr
    projectId: IdStr
    scene: str
    name: str
    version: str
    content: str
    variablesJson: dict[str, object] = Field(default_factory=dict)
    isActive: bool
    createdBy: IdStr | None = None
    createdAt: UnixTs | None = None
    updatedAt: UnixTs | None = None

    @property
    def variables(self) -> dict[str, object]:
        return self.variablesJson
