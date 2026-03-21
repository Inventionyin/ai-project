export type ApiResponse<T> = {
  code?: number
  message?: string
  data?: T
  requestId?: string
}

export type ApiTarget = {
  id: string
  projectId?: string
  name: string
  baseUrl: string
  method?: string | null
  path?: string | null
  description?: string | null
  isDefault?: boolean
  enabled?: boolean
  version?: number
  createdAt?: string
  updatedAt?: string
}

export type ProjectEnvironment = {
  id: string
  name: string
  baseUrl: string
}

export type CollectionListItem = {
  id: string
  projectId: string
  name: string
  requestCount: number
  updatedAt: number
}

export type CollectionRequest = {
  id: string
  collectionId: string
  groupId?: string | null
  name: string
  method: string
  url: string
  headers?: Record<string, unknown>
  auth?: Record<string, unknown>
  body?: Record<string, unknown>
  asserts?: Record<string, unknown>
  updatedAt?: number
}

export type CollectionGroup = {
  id: string
  collectionId: string
  name: string
  order: number
  requests: CollectionRequest[]
}

export type CollectionDetail = {
  id: string
  projectId: string
  name: string
  variables?: Record<string, unknown>
  groups: CollectionGroup[]
  requests: CollectionRequest[]
  updatedAt?: number
}

export type TestcaseBinding = {
  id: string
  name: string
  apiTargetId?: string | null
  datasetId?: string | null
  datasetName?: string | null
  params?: Record<string, unknown> | null
  priority?: number | null
  enabled?: boolean
  version?: number
}

export type BatchRunFormItem = {
  testcaseId: string
  bindingId: string
  overrideParams?: unknown
}

export type BatchRunFormState = {
  projectId: string
  envId: string
  triggerType: string
  meta: Record<string, unknown> & { source: string; runnerType?: string }
  concurrency: number
  stopOnFailure: boolean
  items: BatchRunFormItem[]
}

export type BatchRunDirectFormItem = {
  testcaseId: string
  overrideParams?: unknown
}

export type BatchRunDirectFormState = {
  projectId: string
  envId?: string
  triggerType: string
  meta: Record<string, unknown> & { source: string; runnerType?: string }
  concurrency: number
  stopOnFailure: boolean
  items: BatchRunDirectFormItem[]
}

export type RunDetailData = {
  id: string
  status: string
  progress?: {
    done?: number
    total?: number
  }
  suiteId?: string
  envId?: string
  startAt?: number
}

export type CaseRunItem = {
  caseRunId: string
  testcaseId?: string
  status?: string
  startAt?: number | null
  endAt?: number | null
  errorType?: string | null
  errorMessage?: string | null
  bindingSnapshot?: unknown
}

export type RunAllureReportGenerateData = {
  runId: string
  reportStatus: string
  reportUrl?: string | null
  reportPath?: string | null
  resultsPath?: string | null
  errorCode?: string | null
  errorMessage?: string | null
}

export type RunAllureReportListItem = {
  runId: string
  createdAt: number
  name?: string | null
  size?: number | null
  reportUrl: string
}

export type RunAllureReportDeleteData = {
  runId: string
  deletedArtifacts: number
  deletedFiles: number
  deletedDirs: number
}

const resolveApiBaseUrl = () => {
  const envBase = String(import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!envBase) return ''
  return envBase.endsWith('/') ? envBase.slice(0, -1) : envBase
}

const resolveAuthHeader = () => {
  const accessToken = localStorage.getItem('accessToken')
  if (!accessToken) {
    throw new Error('登录状态已失效，请重新登录')
  }
  return `Bearer ${accessToken}`
}

async function requestJson<T>(path: string, init: RequestInit) {
  const baseUrl = resolveApiBaseUrl()
  const res = await fetch(`${baseUrl}${path}`, init)
  let payload: ApiResponse<T> = {}
  try {
    payload = (await res.json()) as ApiResponse<T>
  } catch {
    payload = {}
  }
  if (!res.ok || payload.code !== 0) {
    const codeText = typeof payload.code === 'number' ? `（${payload.code}）` : ''
    throw new Error(payload.message ? `${payload.message}${codeText}` : `请求失败${codeText}`)
  }
  return payload.data as T
}

function normalizeApiTargets(data: unknown) {
  if (Array.isArray(data)) return data as ApiTarget[]
  if (data && typeof data === 'object' && Array.isArray((data as { items?: unknown[] }).items)) {
    return ((data as { items: unknown[] }).items ?? []) as ApiTarget[]
  }
  return []
}

function normalizeCaseRuns(data: unknown) {
  if (Array.isArray(data)) return data as CaseRunItem[]
  if (data && typeof data === 'object' && Array.isArray((data as { items?: unknown[] }).items)) {
    return ((data as { items: unknown[] }).items ?? []) as CaseRunItem[]
  }
  return []
}

export async function fetchApiTargets(projectId: string) {
  const pid = String(projectId || '').trim()
  if (!pid) return []
  const query = new URLSearchParams({ projectId: pid })
  const data = await requestJson<ApiTarget[] | { items?: ApiTarget[] }>(`/api/api-targets?${query.toString()}`, {
    method: 'GET',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
  return normalizeApiTargets(data)
}

export async function fetchCollections(projectId: string, page = 1, pageSize = 200) {
  const pid = String(projectId || '').trim()
  if (!pid) return []
  const query = new URLSearchParams({
    projectId: pid,
    page: String(page),
    pageSize: String(pageSize)
  })
  const data = await requestJson<CollectionListItem[] | { items?: CollectionListItem[] }>(`/api/collections?${query.toString()}`, {
    method: 'GET',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
  if (Array.isArray(data)) return data
  return Array.isArray(data?.items) ? data.items : []
}

export async function fetchCollectionDetail(collectionId: string) {
  const id = String(collectionId || '').trim()
  if (!id) throw new Error('集合 ID 不能为空')
  return requestJson<CollectionDetail>(`/api/collections/${encodeURIComponent(id)}`, {
    method: 'GET',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
}

export async function createCollection(payload: { projectId: string; name: string; variables?: Record<string, unknown> }) {
  return requestJson<CollectionDetail>('/api/collections', {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
}

export async function createCollectionGroup(collectionId: string, payload: { name: string }) {
  const id = String(collectionId || '').trim()
  if (!id) throw new Error('集合 ID 不能为空')
  return requestJson<{ id: string; collectionId: string; name: string; order: number }>(`/api/collections/${encodeURIComponent(id)}/groups`, {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
}

export async function createCollectionRequest(
  collectionId: string,
  payload: {
    groupId?: string | null
    name: string
    method: string
    url: string
    headers?: Record<string, unknown>
    auth?: Record<string, unknown>
    body?: Record<string, unknown>
    asserts?: Record<string, unknown>
  }
) {
  const id = String(collectionId || '').trim()
  if (!id) throw new Error('集合 ID 不能为空')
  return requestJson<CollectionRequest>(`/api/collections/${encodeURIComponent(id)}/requests`, {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
}

export async function fetchProjectEnvironments(projectId: string) {
  const pid = String(projectId || '').trim()
  if (!pid) return []
  return requestJson<ProjectEnvironment[]>(`/api/projects/${encodeURIComponent(pid)}/environments`, {
    method: 'GET',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
}

export async function fetchTestcaseBindings(testcaseId: string) {
  const id = String(testcaseId || '').trim()
  if (!id) return []
  const data = await requestJson<TestcaseBinding[] | { items?: TestcaseBinding[] }>(`/api/testcases/${encodeURIComponent(id)}/bindings`, {
    method: 'GET',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
  if (Array.isArray(data)) return data
  return Array.isArray(data?.items) ? data.items : []
}

export async function fetchBindingsByTestcaseIds(testcaseIds: string[]) {
  const ids = Array.isArray(testcaseIds) ? testcaseIds.map((v) => String(v || '').trim()).filter(Boolean) : []
  const entries = await Promise.all(ids.map(async (id) => [id, await fetchTestcaseBindings(id)] as const))
  return entries.reduce<Record<string, TestcaseBinding[]>>((acc, [id, bindings]) => {
    acc[id] = bindings
    return acc
  }, {})
}

export async function createTestcaseBinding(testcaseId: string, payload: { name: string; apiTargetId?: string | null; datasetId?: string | null; datasetName?: string | null; params?: Record<string, unknown> | null; priority?: number | null; enabled?: boolean; version?: number }) {
  const id = String(testcaseId || '').trim()
  if (!id) throw new Error('用例 ID 不能为空')
  return requestJson<TestcaseBinding>(`/api/testcases/${encodeURIComponent(id)}/bindings`, {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
}

export async function updateTestcaseBinding(bindingId: string, payload: { name?: string; apiTargetId?: string | null; datasetId?: string | null; datasetName?: string | null; params?: Record<string, unknown> | null; priority?: number | null; enabled?: boolean; version: number }) {
  const id = String(bindingId || '').trim()
  if (!id) throw new Error('绑定 ID 不能为空')
  return requestJson<TestcaseBinding>(`/api/testcase-bindings/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: {
      Authorization: resolveAuthHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
}

export async function deleteTestcaseBinding(bindingId: string) {
  const id = String(bindingId || '').trim()
  if (!id) throw new Error('绑定 ID 不能为空')
  return requestJson<Record<string, never>>(`/api/testcase-bindings/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
}

export async function createApiTarget(payload: { projectId: string; name: string; baseUrl: string; description?: string | null; isDefault?: boolean; enabled?: boolean }) {
  return requestJson<ApiTarget>('/api/api-targets', {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
}

export async function updateApiTarget(apiTargetId: string, payload: { name?: string; baseUrl?: string; description?: string | null; isDefault?: boolean; enabled?: boolean; version: number }) {
  const id = String(apiTargetId || '').trim()
  if (!id) throw new Error('接口目标 ID 不能为空')
  return requestJson<ApiTarget>(`/api/api-targets/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: {
      Authorization: resolveAuthHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
}

export async function deleteApiTarget(apiTargetId: string) {
  const id = String(apiTargetId || '').trim()
  if (!id) throw new Error('接口目标 ID 不能为空')
  return requestJson<Record<string, never>>(`/api/api-targets/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
}

export function buildRunPayload(state: BatchRunFormState) {
  const projectId = String(state.projectId || '').trim()
  const envId = String(state.envId || '').trim()
  const triggerType = String(state.triggerType || '').trim()
  const source = String(state.meta?.source || '').trim()
  const runnerType = String(state.meta?.runnerType || '').trim().toUpperCase()
  const concurrency = Number.isFinite(state.concurrency) ? Math.min(100, Math.max(1, Math.floor(state.concurrency))) : 1
  const stopOnFailure = Boolean(state.stopOnFailure)
  const items = Array.isArray(state.items) ? state.items : []
  const normalizedItems = items
    .map((item) => ({
      testcaseId: String(item?.testcaseId || '').trim(),
      bindingId: String(item?.bindingId || '').trim(),
      overrideParams: item?.overrideParams
    }))
    .filter((item) => item.testcaseId && item.bindingId)
    .map((item) => (item.overrideParams === undefined ? { testcaseId: item.testcaseId, bindingId: item.bindingId } : item))

  if (!projectId) throw new Error('projectId 不能为空')
  if (!envId) throw new Error('envId 不能为空')
  if (!triggerType) throw new Error('triggerType 不能为空')
  if (!source) throw new Error('meta.source 不能为空')
  if (!normalizedItems.length) throw new Error('items 不能为空')

  const dedupe = new Set<string>()
  for (const item of normalizedItems) {
    const key = `${item.testcaseId}::${item.bindingId}`
    if (dedupe.has(key)) throw new Error('请求中存在重复的 testcaseId 与 bindingId 组合')
    dedupe.add(key)
  }

  return {
    projectId,
    envId,
    triggerType,
    meta: runnerType ? { source, runnerType } : { source },
    concurrency,
    stopOnFailure,
    items: normalizedItems
  }
}

export async function runFromTestcases(payload: BatchRunFormState, idempotencyKey?: string) {
  const body = buildRunPayload(payload)
  const headers: Record<string, string> = {
    Authorization: resolveAuthHeader(),
    'Content-Type': 'application/json'
  }
  const ik = String(idempotencyKey || '').trim()
  if (ik) headers['Idempotency-Key'] = ik

  return requestJson<RunDetailData>('/api/runs/from-testcases', {
    method: 'POST',
    headers,
    body: JSON.stringify(body)
  })
}

export function buildRunPayloadDirect(state: BatchRunDirectFormState) {
  const projectId = String(state.projectId || '').trim()
  const envId = String(state.envId || '').trim()
  const triggerType = String(state.triggerType || '').trim()
  const source = String(state.meta?.source || '').trim()
  const runnerType = String(state.meta?.runnerType || '').trim().toUpperCase()
  const concurrency = Number.isFinite(state.concurrency) ? Math.min(100, Math.max(1, Math.floor(state.concurrency))) : 1
  const stopOnFailure = Boolean(state.stopOnFailure)
  const items = Array.isArray(state.items) ? state.items : []
  const normalizedItems = items
    .map((item) => ({
      testcaseId: String(item?.testcaseId || '').trim(),
      overrideParams: item?.overrideParams
    }))
    .filter((item) => item.testcaseId)
    .map((item) => (item.overrideParams === undefined ? { testcaseId: item.testcaseId } : item))

  if (!projectId) throw new Error('projectId 不能为空')
  if (!triggerType) throw new Error('triggerType 不能为空')
  if (!source) throw new Error('meta.source 不能为空')
  if (!normalizedItems.length) throw new Error('items 不能为空')

  const dedupe = new Set<string>()
  for (const item of normalizedItems) {
    if (dedupe.has(item.testcaseId)) throw new Error('请求中存在重复的 testcaseId')
    dedupe.add(item.testcaseId)
  }

  const body = {
    projectId,
    triggerType,
    meta: runnerType ? { source, runnerType } : { source },
    concurrency,
    stopOnFailure,
    items: normalizedItems
  } as {
    projectId: string
    envId?: string
    triggerType: string
    meta: { source: string; runnerType?: string }
    concurrency: number
    stopOnFailure: boolean
    items: Array<{ testcaseId: string; overrideParams?: unknown }>
  }
  if (envId) body.envId = envId
  return body
}

export async function runFromTestcasesHttp(payload: BatchRunDirectFormState, idempotencyKey?: string) {
  const body = buildRunPayloadDirect(payload)
  const headers: Record<string, string> = {
    Authorization: resolveAuthHeader(),
    'Content-Type': 'application/json'
  }
  const ik = String(idempotencyKey || '').trim()
  if (ik) headers['Idempotency-Key'] = ik

  return requestJson<RunDetailData>('/api/runs/from-testcases-http', {
    method: 'POST',
    headers,
    body: JSON.stringify(body)
  })
}

export async function fetchRunCaseRuns(runId: string) {
  const id = String(runId || '').trim()
  if (!id) return []
  const data = await requestJson<CaseRunItem[] | { items?: CaseRunItem[] }>(`/api/runs/${encodeURIComponent(id)}/case-runs`, {
    method: 'GET',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
  return normalizeCaseRuns(data)
}

export async function fetchProjectAllureReports(projectId: string, page = 1, pageSize = 50) {
  const pid = String(projectId || '').trim()
  if (!pid) return []
  const query = new URLSearchParams({
    projectId: pid,
    page: String(page),
    pageSize: String(pageSize)
  })
  const data = await requestJson<{ items?: RunAllureReportListItem[] } | RunAllureReportListItem[]>(`/api/runs/allure-reports?${query.toString()}`, {
    method: 'GET',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
  if (Array.isArray(data)) return data
  return Array.isArray(data?.items) ? data.items : []
}

export async function deleteRunAllureReport(runId: string) {
  const id = String(runId || '').trim()
  if (!id) throw new Error('runId 不能为空')
  return requestJson<RunAllureReportDeleteData>(`/api/runs/${encodeURIComponent(id)}/allure-report`, {
    method: 'DELETE',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
}

export async function generateRunAllureReport(runId: string) {
  const id = String(runId || '').trim()
  if (!id) {
    throw new Error('runId 不能为空')
  }
  return requestJson<RunAllureReportGenerateData>(`/api/runs/${encodeURIComponent(id)}/allure-report/generate`, {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
}

