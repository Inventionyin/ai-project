import { requestJson, authHeader } from './client'

export interface DevOpsPipeline {
  id: string
  projectId: string
  name: string
  provider: string
  repoFullName: string | null
  workflowFile: string | null
  config: Record<string, unknown> | null
  enabled: boolean
  status: string
  createdBy: string | null
  createdAt: number
  updatedAt: number
}

export interface DevOpsRun {
  id: string
  projectId: string
  pipelineId: string
  externalRunId: string | null
  status: string
  triggerType: string
  commitSha: string | null
  branch: string | null
  errorMessage: string | null
  logUrl: string | null
  meta: Record<string, unknown> | null
  createdBy: string | null
  createdAt: number
  updatedAt: number
}

export interface PageData<T> {
  page: number
  pageSize: number
  total: number
  items: T[]
}

export async function createPipeline(projectId: string, data: {
  name: string; provider?: string; repoFullName?: string; workflowFile?: string;
  config?: Record<string, unknown>; webhookSecret?: string;
}): Promise<DevOpsPipeline> {
  return requestJson<DevOpsPipeline>(`/api/projects/${projectId}/devops/pipelines`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(data),
  })
}

export async function listPipelines(projectId: string, page = 1, pageSize = 20): Promise<PageData<DevOpsPipeline>> {
  return requestJson<PageData<DevOpsPipeline>>(`/api/projects/${projectId}/devops/pipelines?page=${page}&pageSize=${pageSize}`, {
    method: 'GET',
    headers: authHeader(),
  })
}

export async function getPipeline(projectId: string, pipelineId: string): Promise<DevOpsPipeline> {
  return requestJson<DevOpsPipeline>(`/api/projects/${projectId}/devops/pipelines/${pipelineId}`, {
    method: 'GET',
    headers: authHeader(),
  })
}

export async function updatePipeline(projectId: string, pipelineId: string, data: Partial<DevOpsPipeline>): Promise<DevOpsPipeline> {
  return requestJson<DevOpsPipeline>(`/api/projects/${projectId}/devops/pipelines/${pipelineId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(data),
  })
}

export async function deletePipeline(projectId: string, pipelineId: string): Promise<void> {
  await requestJson<void>(`/api/projects/${projectId}/devops/pipelines/${pipelineId}`, {
    method: 'DELETE',
    headers: authHeader(),
  })
}

export async function triggerPipeline(projectId: string, pipelineId: string, data?: { branch?: string; commitSha?: string; params?: Record<string, unknown> }): Promise<DevOpsRun> {
  return requestJson<DevOpsRun>(`/api/projects/${projectId}/devops/pipelines/${pipelineId}/trigger`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(data || {}),
  })
}

export async function listRuns(projectId: string, pipelineId?: string, page = 1, pageSize = 20): Promise<PageData<DevOpsRun>> {
  const params = new URLSearchParams({ page: String(page), pageSize: String(pageSize) })
  if (pipelineId) params.set('pipelineId', pipelineId)
  return requestJson<PageData<DevOpsRun>>(`/api/projects/${projectId}/devops/runs?${params}`, {
    method: 'GET',
    headers: authHeader(),
  })
}
