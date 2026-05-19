import { requestJson, authHeader } from './client'

export interface UiTestScript {
  id: string
  projectId: string
  name: string
  description: string
  scriptType: string
  scriptContent: string
  recordingJson: Record<string, unknown>
  status: string
  browser: string
  viewportWidth: number
  viewportHeight: number
  baseUrl: string
  tags: string[]
  createdBy: string | null
  createdAt: number
  updatedAt: number
}

export interface UiTestRun {
  id: string
  scriptId: string
  status: string
  startedAt: string | null
  finishedAt: string | null
  durationMs: number | null
  stepsTotal: number
  stepsPassed: number
  stepsFailed: number
  screenshotPaths: string[]
  errorMessage: string | null
  tracePath: string | null
  reportPath: string | null
  createdAt: number
  updatedAt: number
}

export interface PageData<T> {
  page: number
  pageSize: number
  total: number
  items: T[]
}

export async function listScripts(projectId: string, page = 1, pageSize = 20): Promise<PageData<UiTestScript>> {
  return requestJson<PageData<UiTestScript>>(
    `/api/projects/${projectId}/ui-automation/scripts?page=${page}&pageSize=${pageSize}`,
    { method: 'GET', headers: authHeader() }
  )
}

export async function getScript(projectId: string, scriptId: string): Promise<UiTestScript> {
  return requestJson<UiTestScript>(
    `/api/projects/${projectId}/ui-automation/scripts/${scriptId}`,
    { method: 'GET', headers: authHeader() }
  )
}

export async function createScript(projectId: string, data: {
  name: string; description?: string; scriptType?: string;
  browser?: string; viewportWidth?: number; viewportHeight?: number;
  baseUrl?: string; tags?: string[];
}): Promise<UiTestScript> {
  return requestJson<UiTestScript>(
    `/api/projects/${projectId}/ui-automation/scripts`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: JSON.stringify(data),
    }
  )
}

export async function updateScript(projectId: string, scriptId: string, data: Partial<UiTestScript>): Promise<UiTestScript> {
  return requestJson<UiTestScript>(
    `/api/projects/${projectId}/ui-automation/scripts/${scriptId}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: JSON.stringify(data),
    }
  )
}

export async function deleteScript(projectId: string, scriptId: string): Promise<void> {
  await requestJson<void>(
    `/api/projects/${projectId}/ui-automation/scripts/${scriptId}`,
    { method: 'DELETE', headers: authHeader() }
  )
}

export async function saveRecording(projectId: string, scriptId: string, actions: Record<string, unknown>[]): Promise<UiTestScript> {
  return requestJson<UiTestScript>(
    `/api/projects/${projectId}/ui-automation/scripts/${scriptId}/record`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: JSON.stringify({ actions }),
    }
  )
}

export async function generateScript(projectId: string, scriptId: string): Promise<UiTestScript> {
  return requestJson<UiTestScript>(
    `/api/projects/${projectId}/ui-automation/scripts/${scriptId}/generate`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: JSON.stringify({}),
    }
  )
}

export async function runTest(projectId: string, scriptId: string): Promise<UiTestRun> {
  return requestJson<UiTestRun>(
    `/api/projects/${projectId}/ui-automation/scripts/${scriptId}/run`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: JSON.stringify({}),
    }
  )
}

export async function listRuns(projectId: string, scriptId?: string, page = 1, pageSize = 20): Promise<PageData<UiTestRun>> {
  const params = new URLSearchParams({ page: String(page), pageSize: String(pageSize) })
  if (scriptId) params.set('scriptId', scriptId)
  return requestJson<PageData<UiTestRun>>(
    `/api/projects/${projectId}/ui-automation/runs?${params}`,
    { method: 'GET', headers: authHeader() }
  )
}

export async function getRun(projectId: string, runId: string): Promise<UiTestRun> {
  return requestJson<UiTestRun>(
    `/api/projects/${projectId}/ui-automation/runs/${runId}`,
    { method: 'GET', headers: authHeader() }
  )
}
