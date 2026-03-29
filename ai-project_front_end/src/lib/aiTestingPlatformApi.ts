export type ApiResponse<T> = {
  code?: number
  message?: string
  data?: T
  requestId?: string
}

export type TestCaseImportErrorItem = {
  rowNumber: number
  testCaseId?: string | null
  field?: string | null
  message: string
}

export type TestCaseImportData = {
  importedCount: number
  failedCount: number
  errors: TestCaseImportErrorItem[]
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

export type PageData<T> = {
  page: number
  pageSize: number
  total: number
  items: T[]
}

export type SuiteLite = {
  id: string
  name: string
}

export type RunProgress = {
  done: number
  total: number
}

export type RunMetrics = {
  total: number
  done: number
  passed: number
  failed: number
  skipped: number
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
  status: 'QUEUED' | 'RUNNING' | 'PASSED' | 'FAILED' | 'CANCELED'
  progress: RunProgress
  triggerType?: 'MANUAL' | 'CI' | 'CRON' | 'WEBHOOK' | null
  executionSource?: 'TESTCASE_DIRECT' | 'TESTCASE_HTTP_DIRECT' | null
  metrics?: RunMetrics | null
  suiteId: string
  envId?: string | null
  startAt: number
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
    const err = new Error(payload.message ? `${payload.message}${codeText}` : `请求失败${codeText}`)
    ;(err as { apiCode?: number; requestId?: string; httpStatus?: number }).apiCode =
      typeof payload.code === 'number' ? payload.code : undefined
    ;(err as { apiCode?: number; requestId?: string; httpStatus?: number }).requestId =
      typeof payload.requestId === 'string' ? payload.requestId : undefined
    ;(err as { apiCode?: number; requestId?: string; httpStatus?: number }).httpStatus = res.status
    throw err
  }
  return payload.data as T
}

async function requestFormData<T>(path: string, init: RequestInit) {
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
    const err = new Error(payload.message ? `${payload.message}${codeText}` : `请求失败${codeText}`)
    ;(err as { apiCode?: number; requestId?: string; httpStatus?: number }).apiCode =
      typeof payload.code === 'number' ? payload.code : undefined
    ;(err as { apiCode?: number; requestId?: string; httpStatus?: number }).requestId =
      typeof payload.requestId === 'string' ? payload.requestId : undefined
    ;(err as { apiCode?: number; requestId?: string; httpStatus?: number }).httpStatus = res.status
    throw err
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

export async function importTestcases(payload: { projectId: string; file: File; mode?: 'partial' | 'atomic' }) {
  const pid = String(payload.projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!payload.file) throw new Error('请选择文件')
  const form = new FormData()
  form.append('projectId', pid)
  form.append('mode', payload.mode || 'partial')
  form.append('file', payload.file, payload.file.name)
  return requestFormData<TestCaseImportData>('/api/testcases/import', {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader()
    },
    body: form
  })
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

export type DocIngestApiCandidate = {
  id: string
  name?: string | null
  feature?: string | null
  method?: string | null
  url?: string | null
  expectedStatusCode?: number | null
  expectedResult?: string | null
  tags?: string[] | null
  confidence?: number | null
}

export async function previewDocIngest(payload: { file: File; llmMode?: 'OFF' | 'SUGGEST' | 'AUTO'; instruction?: string }) {
  if (!payload?.file) throw new Error('请选择文件')
  const form = new FormData()
  form.append('llmMode', payload.llmMode || 'OFF')
  form.append('instruction', String(payload.instruction || '').trim())
  form.append('file', payload.file, payload.file.name)
  return requestFormData<{ meta: unknown; status: string; apiCandidates: DocIngestApiCandidate[] }>('/api/doc-ingest/preview', {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader()
    },
    body: form
  })
}

export async function generateDocCsv(payload: {
  file: File
  llmMode?: 'OFF' | 'SUGGEST' | 'AUTO'
  instruction?: string
  candidateIds?: string[]
  caseGenMode?: 'OFF' | 'SUGGEST' | 'AUTO'
  skillId?: string
  maxCases?: number
  baseUrl?: string
}) {
  if (!payload?.file) throw new Error('请选择文件')
  const form = new FormData()
  form.append('llmMode', payload.llmMode || 'OFF')
  form.append('instruction', String(payload.instruction || '').trim())
  if (Array.isArray(payload.candidateIds)) {
    form.append('candidateIds', JSON.stringify(payload.candidateIds))
  }
  form.append('caseGenMode', payload.caseGenMode || 'OFF')
  form.append('skillId', String(payload.skillId || '').trim())
  if (typeof payload.maxCases === 'number' && Number.isFinite(payload.maxCases)) {
    form.append('maxCases', String(Math.max(1, Math.floor(payload.maxCases))))
  }
  if (payload.baseUrl) {
    form.append('baseUrl', payload.baseUrl)
  }
  form.append('file', payload.file, payload.file.name)
  return requestFormData<{ fileName: string; csvText: string; itemCount: number; status: string }>('/api/doc-ingest/generate-csv', {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader()
    },
    body: form
  })
}

export async function generateDocAndImport(payload: {
  projectId: string
  file: File
  mode?: 'partial' | 'atomic'
  llmMode?: 'OFF' | 'SUGGEST' | 'AUTO'
  candidateIds?: string[]
  instruction?: string
  caseGenMode?: 'OFF' | 'SUGGEST' | 'AUTO'
  skillId?: string
  maxCases?: number
  baseUrl?: string
}) {
  const pid = String(payload.projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!payload.file) throw new Error('请选择文件')
  const form = new FormData()
  form.append('projectId', pid)
  form.append('mode', payload.mode || 'partial')
  form.append('llmMode', payload.llmMode || 'OFF')
  form.append('instruction', String(payload.instruction || '').trim())
  form.append('caseGenMode', payload.caseGenMode || 'OFF')
  form.append('skillId', String(payload.skillId || '').trim())
  if (typeof payload.maxCases === 'number' && Number.isFinite(payload.maxCases)) {
    form.append('maxCases', String(Math.max(1, Math.floor(payload.maxCases))))
  }
  if (Array.isArray(payload.candidateIds)) {
    form.append('candidateIds', JSON.stringify(payload.candidateIds))
  }
  if (payload.baseUrl) {
    form.append('baseUrl', payload.baseUrl)
  }
  form.append('file', payload.file, payload.file.name)
  return requestFormData<TestCaseImportData>('/api/doc-ingest/generate-import', {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader()
    },
    body: form
  })
}

export async function generateK6(payload: {
  projectId: string
  file: File
  llmMode?: 'OFF' | 'SUGGEST' | 'AUTO'
  k6GenMode?: 'LLM' | 'HEURISTIC'
  baseUrl?: string
  vus?: number
  duration?: string
  candidateIds?: string[]
  instruction?: string
}) {
  const pid = String(payload.projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!payload?.file) throw new Error('请选择文件')
  const form = new FormData()
  form.append('projectId', pid)
  form.append('llmMode', payload.llmMode || 'OFF')
  form.append('k6GenMode', payload.k6GenMode || 'LLM')
  form.append('baseUrl', String(payload.baseUrl || '').trim())
  form.append('vus', String(payload.vus || 10))
  form.append('duration', String(payload.duration || '30s'))
  form.append('instruction', String(payload.instruction || '').trim())
  if (Array.isArray(payload.candidateIds)) {
    form.append('candidateIds', JSON.stringify(payload.candidateIds))
  }
  form.append('file', payload.file, payload.file.name)
  return requestFormData<{ fileName: string; scriptText: string; status: string; llm?: any }>('/api/doc-ingest/generate-k6', {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader()
    },
    body: form
  })
}

export async function executeK6(scriptText: string, vus?: number, duration?: string) {
  const form = new FormData()
  form.append('scriptText', scriptText)
  if (vus) form.append('vus', String(vus))
  if (duration) form.append('duration', duration)
  return requestFormData<{ stdout: string; stderr: string; exitCode: number; status: string }>('/api/doc-ingest/execute-k6', {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader()
    },
    body: form
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

export async function fetchSuitesLite(projectId: string, page = 1, pageSize = 200) {
  const pid = String(projectId || '').trim()
  if (!pid) {
    return {
      page,
      pageSize,
      total: 0,
      items: []
    } satisfies PageData<SuiteLite>
  }
  const query = new URLSearchParams({
    projectId: pid,
    page: String(page),
    pageSize: String(pageSize)
  })
  return requestJson<PageData<SuiteLite>>(`/api/suites?${query.toString()}`, {
    method: 'GET',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
}

export async function fetchRuns(payload: {
  projectId: string
  page?: number
  pageSize?: number
  status?: RunDetailData['status']
  from?: number
  to?: number
}) {
  const pid = String(payload.projectId || '').trim()
  if (!pid) {
    return {
      page: payload.page ?? 1,
      pageSize: payload.pageSize ?? 20,
      total: 0,
      items: []
    } satisfies PageData<RunDetailData>
  }
  const query = new URLSearchParams({
    projectId: pid,
    page: String(payload.page ?? 1),
    pageSize: String(payload.pageSize ?? 20)
  })
  if (payload.status) query.set('status', payload.status)
  if (typeof payload.from === 'number' && Number.isFinite(payload.from)) query.set('from', String(payload.from))
  if (typeof payload.to === 'number' && Number.isFinite(payload.to)) query.set('to', String(payload.to))
  return requestJson<PageData<RunDetailData>>(`/api/runs?${query.toString()}`, {
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
  try {
    return await requestJson<RunAllureReportDeleteData>(`/api/runs/${encodeURIComponent(id)}/allure-report`, {
      method: 'DELETE',
      headers: {
        Authorization: resolveAuthHeader()
      }
    })
  } catch (error) {
    const apiCode = (error as { apiCode?: number } | null)?.apiCode
    if (apiCode === 40501) {
      return requestJson<RunAllureReportDeleteData>(`/api/runs/${encodeURIComponent(id)}/allure-report/delete`, {
        method: 'POST',
        headers: {
          Authorization: resolveAuthHeader()
        }
      })
    }
    throw error
  }
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

export type ApiImportJobStatus = 'PENDING' | 'UPLOADED' | 'PARSING' | 'PARSED_PREVIEW' | 'COMMITTED' | 'FAILED'

export type ApiImportPreviewRequest = {
  method: string
  url: string
  name?: string
  headers?: Record<string, unknown>
  body?: unknown
  diffStatus: 'new' | 'updated' | 'unchanged'
}

export type ApiImportPreviewGroup = {
  name: string
  requests: ApiImportPreviewRequest[]
}

export type ApiImportPreviewResult = {
  collectionName?: string | null
  groups: ApiImportPreviewGroup[]
}

export type ApiImportJobDetail = {
  id: string
  status: ApiImportJobStatus
  warnings?: string[] | null
  preview?: ApiImportPreviewResult | null
}

export async function createApiCollectionImportJob(projectId: string) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  return requestJson<{ id: string }>('/api/collections/import-jobs', {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ projectId: pid })
  })
}

export async function uploadApiCollectionImportFile(jobId: string, file: File) {
  const id = String(jobId || '').trim()
  if (!id) throw new Error('任务 ID 不能为空')
  if (!file) throw new Error('请选择文件')
  const form = new FormData()
  form.append('file', file, file.name)
  return requestFormData<{ status: ApiImportJobStatus }>(`/api/collections/import-jobs/${encodeURIComponent(id)}/file`, {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader()
    },
    body: form
  })
}

export async function fetchApiCollectionImportJob(jobId: string) {
  const id = String(jobId || '').trim()
  if (!id) throw new Error('任务 ID 不能为空')
  return requestJson<ApiImportJobDetail>(`/api/collections/import-jobs/${encodeURIComponent(id)}`, {
    method: 'GET',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
}

export async function commitApiCollectionImportJob(
  jobId: string,
  payload: { selected: Array<{ method: string; url: string }>; overrideExisting?: boolean }
) {
  const id = String(jobId || '').trim()
  if (!id) throw new Error('任务 ID 不能为空')
  const selected = Array.isArray(payload.selected)
    ? payload.selected.map((v) => ({ method: String(v.method || '').trim(), url: String(v.url || '').trim() })).filter((v) => v.method && v.url)
    : []
  if (!selected.length) throw new Error('未选择任何接口')
  return requestJson<{ status: ApiImportJobStatus; importedCount?: number; updatedCount?: number }>(
    `/api/collections/import-jobs/${encodeURIComponent(id)}/commit`,
    {
      method: 'POST',
      headers: {
        Authorization: resolveAuthHeader(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ selected, overrideExisting: Boolean(payload.overrideExisting) })
    }
  )
}

