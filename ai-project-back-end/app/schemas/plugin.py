from __future__ import annotations

from app.schemas.common import BaseSchema


class SandboxPolicy(BaseSchema):
    permissions: list[str]
    timeoutMs: int
    networkMode: str
    allowedHosts: list[str]
    maxPayloadBytes: int


class PluginCreateRequest(BaseSchema):
    name: str
    slug: str
    description: str | None = None
    version: str
    author: str | None = None
    pluginType: str = "executor"
    configSchema: dict | None = None
    entryPoint: str | None = None
    minPlatformVersion: str | None = None
    iconUrl: str | None = None


class PluginUpdateRequest(BaseSchema):
    name: str | None = None
    description: str | None = None
    version: str | None = None
    configSchema: dict | None = None
    entryPoint: str | None = None
    enabled: bool | None = None
    iconUrl: str | None = None


class PluginDetail(BaseSchema):
    id: str
    name: str
    slug: str
    description: str | None = None
    version: str
    author: str | None = None
    pluginType: str
    configSchema: dict | None = None
    entryPoint: str | None = None
    minPlatformVersion: str | None = None
    iconUrl: str | None = None
    enabled: bool
    status: str
    downloadCount: int
    createdAt: int
    updatedAt: int
    sandboxPolicy: SandboxPolicy


class PluginInstallRequest(BaseSchema):
    pluginId: str
    config: dict | None = None


class PluginInstallationDetail(BaseSchema):
    id: str
    projectId: str
    pluginId: str
    pluginName: str | None = None
    pluginSlug: str | None = None
    status: str
    config: dict | None = None
    installedVersion: str | None = None
    errorMessage: str | None = None
    installedBy: str | None = None
    createdAt: int
    updatedAt: int
    sandboxPolicy: SandboxPolicy


class PluginToggleRequest(BaseSchema):
    enabled: bool


class PluginInvokeResponse(BaseSchema):
    installationId: str
    pluginId: str
    pluginSlug: str
    status: str
    sandboxPolicy: SandboxPolicy
    executionId: str | None = None
    exitCode: int | None = None
    durationMs: int | None = None
    timedOut: bool = False
    output: dict | None = None
    error: str | None = None


class PluginInvokeRequest(BaseSchema):
    payload: dict | None = None


class PluginInvokeRecordDetail(BaseSchema):
    id: str
    installationId: str
    pluginId: str | None = None
    pluginSlug: str | None = None
    invokedBy: str | None = None
    status: str
    createdAt: int
