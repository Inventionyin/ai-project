from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.types import IdStr, UnixTs


class AiTrainingJobCreateRequest(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=5000)
    trainingType: str = Field(default="FINE_TUNE", min_length=1, max_length=32)
    baseModel: str = Field(default="deepseek-chat", min_length=1, max_length=128)
    datasetConfig: dict[str, object] = Field(default_factory=dict)
    hyperparams: dict[str, object] = Field(default_factory=dict)


class AiTrainingJobUpdateRequest(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    trainingType: str | None = Field(default=None, min_length=1, max_length=32)
    baseModel: str | None = Field(default=None, min_length=1, max_length=128)
    datasetConfig: dict[str, object] | None = None
    hyperparams: dict[str, object] | None = None


class AiTrainingJobListItem(BaseSchema):
    id: IdStr
    projectId: IdStr
    name: str
    description: str
    trainingType: str
    baseModel: str
    status: str
    progress: float
    metrics: dict[str, object] = Field(default_factory=dict)
    modelRef: str | None = None
    errorMessage: str | None = None
    createdBy: IdStr | None = None
    createdAt: UnixTs | None = None
    updatedAt: UnixTs | None = None


class AiTrainingJobDetail(AiTrainingJobListItem):
    datasetConfig: dict[str, object] = Field(default_factory=dict)
    hyperparams: dict[str, object] = Field(default_factory=dict)


class AiTrainingJobProgress(BaseSchema):
    status: str
    progress: float
    metrics: dict[str, object] = Field(default_factory=dict)
    modelRef: str | None = None
    errorMessage: str | None = None


class AiTrainingDatasetCreateRequest(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    sourceType: str = Field(default="TESTCASES", min_length=1, max_length=32)
    config: dict[str, object] = Field(default_factory=dict)


class AiTrainingDatasetListItem(BaseSchema):
    id: IdStr
    projectId: IdStr
    name: str
    sourceType: str
    recordCount: int
    sampleJson: dict[str, object] = Field(default_factory=dict)
    configJson: dict[str, object] = Field(default_factory=dict)
    createdAt: UnixTs | None = None
    updatedAt: UnixTs | None = None
