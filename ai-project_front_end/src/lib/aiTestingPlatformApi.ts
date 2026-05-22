export type ApiResponse<T> = {
  code?: number
  message?: string
  data?: T
  requestId?: string
}

import { createApiError, handleAuthExpired, isAuthExpiredResponse } from '@/lib/api/client'

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

export type SuiteDetail = {
  id: string
  projectId: string
  name: string
  defaultEnvId?: string | null
  config?: Record<string, unknown>
  createdAt?: number
  updatedAt?: number
}

export type SuiteItem = {
  id?: string
  suiteId?: string
  testcaseId: string
  orderNo: number
  params?: Record<string, unknown>
  testcaseTitle?: string
  testcaseType?: string
  testcasePriority?: string
  testcaseStatus?: string
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

export type {
  ApiAssetBinding,
  CollectionListItem,
  CollectionRequest,
  CollectionGroup,
  CollectionDetail
} from '@/lib/api/collections'

export {
  fetchCollections,
  fetchCollectionDetail,
  createCollection,
  createCollectionGroup,
  createCollectionRequest,
  fetchCollectionBindings,
  fetchRequestBindings
} from '@/lib/api/collections'

export type TestcaseBinding = {
  id: string
  projectId?: string
  testcaseId?: string
  name: string
  linkType?: 'API_TARGET' | 'REQUEST' | 'COLLECTION'
  apiTargetId?: string | null
  requestId?: string | null
  collectionId?: string | null
  sourceType?: 'MANUAL' | 'AI' | 'IMPORT'
  assertSummary?: string
  lastRunStatus?: string | null
  lastRunAt?: number | null
  datasetId?: string | null
  datasetName?: string | null
  params?: Record<string, unknown> | null
  priority?: number | null
  enabled?: boolean
  version?: number
  updatedAt?: number
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

export type PerformanceReportListItem = {
  id: string
  name: string
  status: string
  createdAt: number
  duration: string
  vus: number
}

export type PerformanceReportDetail = {
  id: string
  name: string
  status: string
  createdAt: number
  duration: string
  vus: number
  tps: number
  avgResponseMs: number
  p95ResponseMs: number
  successRate: number
  resources: {
    cpuAvg: number
    cpuMax: number
    memoryAvg: number
    memoryMax: number
    ioReadMb: number
    ioWriteMb: number
  }
  trendPoints: Array<{ tps: number; avgResponseMs: number }>
  latencyDistribution: Array<{ label: string; count: number }>
  asserts: Array<{ apiName: string; passed: number; failed: number }>
}

export type UiTestReportSummary = {
  total: number
  passed: number
  failed: number
  skipped: number
  durationMs: number
}

export type UiTestReportListItem = {
  runId: string
  projectId: string
  pageId: string
  status: string
  result: string
  assertLevel: string
  total: number
  passed: number
  failed: number
  skipped: number
  durationMs: number
  reportDir: string
  reportIndexUrl: string
  createdAt: number
  finishedAt: number
}

export type UiTestFailedCase = {
  title: string
  error: string
  screenshot?: string | null
  trace?: string | null
}

export type UiTestReportDetail = {
  runId: string
  projectId: string
  pageId: string
  status: string
  result: string
  assertLevel: string
  specPath: string
  reportDir: string
  reportIndexUrl: string
  summary: UiTestReportSummary
  failedCases: UiTestFailedCase[]
  startedAt: number
  finishedAt: number
}

export type UiTestGenerateRunPayload = {
  projectId: string
  pageId: string
  figmaUrl?: string
  assertLevel?: 'P0' | 'P1' | 'P2'
  headed?: boolean
  baseUrl?: string
  updateManifest?: boolean
  triggerBy?: string
  meta?: Record<string, unknown>
}

export type UiTestGenerateRunData = {
  runId: string
  status: string
  result: string
  pageId: string
  assertLevel: string
  specPath: string
  reportDir: string
  reportIndexUrl: string
  summary: UiTestReportSummary
  startedAt: number
  finishedAt: number
  stdout: string
  stderr: string
}

export type CreateSuiteRunPayload = {
  projectId: string
  suiteId: string
  envId: string
  triggerType: 'MANUAL' | 'CI' | 'CRON' | 'WEBHOOK'
  meta?: Record<string, unknown>
  notifyRuleId?: string
}

export type ProjectTestcaseLite = {
  id: string
  projectId: string
  title: string
  name?: string
  type?: string
  priority?: string
  status?: string
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
    if (isAuthExpiredResponse(res, payload)) {
      throw handleAuthExpired()
    }
    throw createApiError(res, payload)
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
    if (isAuthExpiredResponse(res, payload)) {
      throw handleAuthExpired()
    }
    throw createApiError(res, payload)
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

export async function executeK6(scriptText: string, vus?: number, duration?: string, projectId?: string) {
  const form = new FormData()
  form.append('scriptText', scriptText)
  if (vus) form.append('vus', String(vus))
  if (duration) form.append('duration', duration)
  if (projectId) form.append('projectId', projectId)
  return requestFormData<{ stdout: string; stderr: string; exitCode: number; status: string; runId?: string | null }>('/api/doc-ingest/execute-k6', {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader()
    },
    body: form
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

export async function fetchSuiteDetail(suiteId: string) {
  const id = String(suiteId || '').trim()
  if (!id) throw new Error('suiteId 不能为空')
  return requestJson<SuiteDetail>(`/api/suites/${encodeURIComponent(id)}`, {
    method: 'GET',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
}

export async function fetchSuiteItems(suiteId: string) {
  const id = String(suiteId || '').trim()
  if (!id) return []
  const data = await requestJson<SuiteItem[] | { items?: SuiteItem[] }>(`/api/suites/${encodeURIComponent(id)}/items`, {
    method: 'GET',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
  if (Array.isArray(data)) return data
  return Array.isArray(data?.items) ? data.items : []
}

export async function upsertSuiteItems(suiteId: string, items: SuiteItem[]) {
  const id = String(suiteId || '').trim()
  if (!id) throw new Error('suiteId 不能为空')
  return requestJson<SuiteItem[]>(`/api/suites/${encodeURIComponent(id)}/items`, {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ items: Array.isArray(items) ? items : [] })
  })
}

export async function fetchProjectTestcasesLite(projectId: string, page = 1, pageSize = 20) {
  const pid = String(projectId || '').trim()
  if (!pid) {
    return {
      page,
      pageSize,
      total: 0,
      items: []
    } satisfies PageData<ProjectTestcaseLite>
  }
  const query = new URLSearchParams({
    projectId: pid,
    page: String(page),
    pageSize: String(pageSize)
  })
  return requestJson<PageData<ProjectTestcaseLite>>(`/api/testcases?${query.toString()}`, {
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

export async function createTestcaseBinding(testcaseId: string, payload: { name: string; apiTargetId?: string | null; requestId?: string | null; collectionId?: string | null; linkType?: 'API_TARGET' | 'REQUEST' | 'COLLECTION'; sourceType?: 'MANUAL' | 'AI' | 'IMPORT'; assertSummary?: string; datasetId?: string | null; params?: Record<string, unknown> | null; priority?: number | null; enabled?: boolean; version?: number }) {
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

export async function updateTestcaseBinding(bindingId: string, payload: { name?: string; apiTargetId?: string | null; requestId?: string | null; collectionId?: string | null; linkType?: 'API_TARGET' | 'REQUEST' | 'COLLECTION'; sourceType?: 'MANUAL' | 'AI' | 'IMPORT'; assertSummary?: string; datasetId?: string | null; params?: Record<string, unknown> | null; priority?: number | null; enabled?: boolean; version: number }) {
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

export async function createSuiteRun(payload: CreateSuiteRunPayload) {
  const body = {
    projectId: String(payload.projectId || '').trim(),
    suiteId: String(payload.suiteId || '').trim(),
    envId: String(payload.envId || '').trim(),
    triggerType: String(payload.triggerType || '').trim(),
    meta: payload.meta ?? {},
    notifyRuleId: String(payload.notifyRuleId || '').trim() || undefined
  }
  if (!body.projectId) throw new Error('projectId 不能为空')
  if (!body.suiteId) throw new Error('suiteId 不能为空')
  if (!body.envId) throw new Error('envId 不能为空')
  if (!body.triggerType) throw new Error('triggerType 不能为空')
  return requestJson<RunDetailData>('/api/runs', {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  })
}

export async function fetchRunCaseRuns(runId: string): Promise<CaseRunItem[]>
export async function fetchRunCaseRuns(
  runId: string,
  query: { status?: 'QUEUED' | 'RUNNING' | 'PASSED' | 'FAILED' | 'SKIPPED'; page?: number; pageSize?: number }
): Promise<PageData<CaseRunItem>>
export async function fetchRunCaseRuns(
  runId: string,
  query?: { status?: 'QUEUED' | 'RUNNING' | 'PASSED' | 'FAILED' | 'SKIPPED'; page?: number; pageSize?: number }
) {
  const id = String(runId || '').trim()
  if (!id) {
    if (!query) return []
    return {
      page: query.page ?? 1,
      pageSize: query.pageSize ?? 20,
      total: 0,
      items: []
    } satisfies PageData<CaseRunItem>
  }

  const qs = new URLSearchParams()
  if (query?.status) qs.set('status', String(query.status))
  if (typeof query?.page === 'number' && Number.isFinite(query.page)) qs.set('page', String(query.page))
  if (typeof query?.pageSize === 'number' && Number.isFinite(query.pageSize)) qs.set('pageSize', String(query.pageSize))
  const path = `/api/runs/${encodeURIComponent(id)}/case-runs${qs.toString() ? `?${qs.toString()}` : ''}`
  const data = await requestJson<CaseRunItem[] | PageData<CaseRunItem> | { items?: CaseRunItem[] }>(path, {
    method: 'GET',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
  if (!query) return normalizeCaseRuns(data)
  if (
    data &&
    typeof data === 'object' &&
    !Array.isArray(data) &&
    Array.isArray((data as { items?: unknown[] }).items) &&
    'total' in data
  ) {
    return data as PageData<CaseRunItem>
  }
  const items = normalizeCaseRuns(data)
  return {
    page: query.page ?? 1,
    pageSize: query.pageSize ?? (items.length || 20),
    total: items.length,
    items
  }
}

export async function fetchRunDetail(runId: string) {
  const id = String(runId || '').trim()
  if (!id) throw new Error('runId 不能为空')
  return requestJson<RunDetailData>(`/api/runs/${encodeURIComponent(id)}`, {
    method: 'GET',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
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

export async function fetchProjectPerformanceReports(projectId: string, page = 1, pageSize = 50) {
  const pid = String(projectId || '').trim()
  if (!pid) return []
  const query = new URLSearchParams({
    projectId: pid,
    page: String(page),
    pageSize: String(pageSize)
  })
  const data = await requestJson<{ items?: PerformanceReportListItem[] } | PerformanceReportListItem[]>(
    `/api/doc-ingest/perf-reports?${query.toString()}`,
    {
      method: 'GET',
      headers: {
        Authorization: resolveAuthHeader()
      }
    }
  )
  if (Array.isArray(data)) return data
  return Array.isArray(data?.items) ? data.items : []
}

export async function fetchPerformanceReportDetail(runId: string) {
  const id = String(runId || '').trim()
  if (!id) throw new Error('runId 不能为空')
  return requestJson<PerformanceReportDetail>(`/api/doc-ingest/perf-reports/${encodeURIComponent(id)}`, {
    method: 'GET',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
}

export async function fetchProjectUiTestReports(
  projectId: string,
  page = 1,
  pageSize = 50,
  filters?: { status?: string; result?: string; pageId?: string }
) {
  const pid = String(projectId || '').trim()
  if (!pid) return []
  const query = new URLSearchParams({
    projectId: pid,
    page: String(page),
    pageSize: String(pageSize)
  })
  if (filters?.status) query.set('status', String(filters.status))
  if (filters?.result) query.set('result', String(filters.result))
  if (filters?.pageId) query.set('pageId', String(filters.pageId))
  const data = await requestJson<{ items?: UiTestReportListItem[] } | UiTestReportListItem[]>(
    `/api/ui-tests/reports?${query.toString()}`,
    {
      method: 'GET',
      headers: {
        Authorization: resolveAuthHeader()
      }
    }
  )
  if (Array.isArray(data)) return data
  return Array.isArray(data?.items) ? data.items : []
}

export async function fetchUiTestReportDetail(runId: string) {
  const id = String(runId || '').trim()
  if (!id) throw new Error('runId 不能为空')
  return requestJson<UiTestReportDetail>(`/api/ui-tests/reports/${encodeURIComponent(id)}`, {
    method: 'GET',
    headers: {
      Authorization: resolveAuthHeader()
    }
  })
}

export async function generateAndRunUiTest(payload: UiTestGenerateRunPayload) {
  const pid = String(payload.projectId || '').trim()
  const pageId = String(payload.pageId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!pageId) throw new Error('pageId 不能为空')
  return requestJson<UiTestGenerateRunData>('/api/ui-tests/generate-and-run', {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      projectId: pid,
      pageId,
      figmaUrl: String(payload.figmaUrl || '').trim() || undefined,
      assertLevel: payload.assertLevel || 'P0',
      headed: Boolean(payload.headed),
      baseUrl: String(payload.baseUrl || '').trim() || undefined,
      updateManifest: payload.updateManifest ?? true,
      triggerBy: String(payload.triggerBy || 'AI_ASSISTANT'),
      meta: payload.meta || { source: 'ai_assistant_ui_tab' }
    })
  })
}

