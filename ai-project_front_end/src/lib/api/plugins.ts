import { requestJson, authHeader } from './client'

export interface SandboxPolicy {
  permissions: string[]
  timeoutMs: number
  networkMode: string
  allowedHosts: string[]
  maxPayloadBytes: number
}

export interface Plugin {
  id: string
  name: string
  slug: string
  description: string | null
  version: string
  author: string | null
  pluginType: string
  configSchema: Record<string, unknown> | null
  entryPoint: string | null
  minPlatformVersion: string | null
  iconUrl: string | null
  enabled: boolean
  status: string
  downloadCount: number
  createdAt: number
  updatedAt: number
  sandboxPolicy: SandboxPolicy
  sandboxPolicyValid: boolean
  sandboxPolicyError: string | null
}

export interface PluginInstallation {
  id: string
  projectId: string
  pluginId: string
  pluginName: string | null
  pluginSlug: string | null
  status: string
  config: Record<string, unknown> | null
  installedVersion: string | null
  errorMessage: string | null
  installedBy: string | null
  createdAt: number
  updatedAt: number
  sandboxPolicy: SandboxPolicy
  sandboxPolicyValid: boolean
  sandboxPolicyError: string | null
}

export interface PageData<T> {
  page: number
  pageSize: number
  total: number
  items: T[]
}

export async function createPlugin(data: {
  name: string; slug: string; version: string; description?: string;
  author?: string; pluginType?: string; configSchema?: Record<string, unknown>;
  entryPoint?: string; minPlatformVersion?: string; iconUrl?: string;
}): Promise<Plugin> {
  return requestJson<Plugin>('/api/plugins', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(data),
  })
}

export async function listPlugins(page = 1, pageSize = 20): Promise<PageData<Plugin>> {
  return requestJson<PageData<Plugin>>(`/api/plugins?page=${page}&pageSize=${pageSize}`, {
    method: 'GET',
    headers: authHeader(),
  })
}

export async function getPlugin(pluginId: string): Promise<Plugin> {
  return requestJson<Plugin>(`/api/plugins/${pluginId}`, {
    method: 'GET',
    headers: authHeader(),
  })
}

export async function updatePlugin(pluginId: string, data: Partial<Plugin>): Promise<Plugin> {
  return requestJson<Plugin>(`/api/plugins/${pluginId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(data),
  })
}

export async function deletePlugin(pluginId: string): Promise<void> {
  await requestJson<void>(`/api/plugins/${pluginId}`, {
    method: 'DELETE',
    headers: authHeader(),
  })
}

export async function installPlugin(projectId: string, pluginId: string, config?: Record<string, unknown>): Promise<PluginInstallation> {
  return requestJson<PluginInstallation>(`/api/projects/${projectId}/plugins/install`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ pluginId, config }),
  })
}

export async function listInstallations(projectId: string, page = 1, pageSize = 20): Promise<PageData<PluginInstallation>> {
  return requestJson<PageData<PluginInstallation>>(`/api/projects/${projectId}/plugins/installations?page=${page}&pageSize=${pageSize}`, {
    method: 'GET',
    headers: authHeader(),
  })
}

export async function uninstallPlugin(projectId: string, installationId: string): Promise<void> {
  await requestJson<void>(`/api/projects/${projectId}/plugins/installations/${installationId}/uninstall`, {
    method: 'POST',
    headers: authHeader(),
  })
}

export async function togglePlugin(projectId: string, installationId: string, enabled: boolean): Promise<PluginInstallation> {
  return requestJson<PluginInstallation>(`/api/projects/${projectId}/plugins/installations/${installationId}/toggle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ enabled }),
  })
}

export interface PluginInvokeResponse {
  installationId: string
  pluginId: string
  pluginSlug: string
  status: string
  sandboxPolicy: SandboxPolicy
  executionId: string | null
  exitCode: number | null
  durationMs: number | null
  timedOut: boolean
  output: Record<string, unknown> | null
  error: string | null
}

export interface PluginInvokeRecord {
  id: string
  installationId: string
  pluginId: string | null
  pluginSlug: string | null
  invokedBy: string | null
  status: string
  createdAt: number
}

export async function invokePlugin(projectId: string, installationId: string, payload?: Record<string, unknown>): Promise<PluginInvokeResponse> {
  return requestJson<PluginInvokeResponse>(`/api/projects/${projectId}/plugins/installations/${installationId}/invoke`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: payload === undefined ? undefined : JSON.stringify({ payload }),
  })
}

export async function listPluginInvocations(projectId: string, installationId: string, page = 1, pageSize = 20): Promise<PageData<PluginInvokeRecord>> {
  return requestJson<PageData<PluginInvokeRecord>>(`/api/projects/${projectId}/plugins/installations/${installationId}/invocations?page=${page}&pageSize=${pageSize}`, {
    method: 'GET',
    headers: authHeader(),
  })
}
