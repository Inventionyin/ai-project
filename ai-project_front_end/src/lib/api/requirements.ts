import { authHeader, requestJson } from '@/lib/api/client'

export type RequirementDocStatus = 'DRAFT' | 'REVIEWING' | 'PUBLISHED' | 'ARCHIVED'
export type RequirementSourceType = 'PRD' | 'SPEC' | 'PROTOTYPE' | 'OTHER'

export type RequirementDoc = {
  id: string
  projectId: string
  title: string
  status: RequirementDocStatus
  tags: string[]
  sourceType: RequirementSourceType
  latestVersionId?: string | null
  currentVersionId?: string | null
  createdAt?: number | null
  updatedAt?: number | null
}

export type RequirementDocVersion = {
  id: string
  docId: string
  version: number
  changeSummary?: string | null
  effectiveScope?: string | null
  parseStatus?: 'pending' | 'processing' | 'done' | 'failed' | null
  createdAt?: number | null
}

export type RequirementAnalysisPayload = {
  featurePoints: Array<Record<string, unknown>>
  businessRules: Array<Record<string, unknown>>
  testPoints: Array<Record<string, unknown>>
  riskPoints: Array<Record<string, unknown>>
  boundaryCases: Array<Record<string, unknown>>
  coverageSuggestions: Array<Record<string, unknown>>
}

export type RequirementAnalysis = {
  id: string
  projectId: string
  docId: string
  docVersionId: string
  status: 'DRAFT' | 'GENERATED' | 'REVIEWED' | 'ARCHIVED'
  summary?: string | null
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  coverageScore?: number | null
  analysis: RequirementAnalysisPayload
  aiTaskId?: string | null
  createdAt?: number | null
  updatedAt?: number | null
}

export type RequirementAnalysisRevision = {
  id: string
  projectId: string
  analysisId: string
  docId: string
  docVersionId: string
  revisionNo: number
  changeReason?: string | null
  summary?: string | null
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  coverageScore?: number | null
  analysis: RequirementAnalysisPayload
  createdBy?: string | null
  createdAt?: number | null
}

export type RequirementTestPointStatus = 'DRAFT' | 'ACCEPTED' | 'REJECTED' | 'CONVERTED'

export type RequirementTestPoint = {
  id: string
  projectId: string
  analysisId: string
  title: string
  description?: string | null
  status: RequirementTestPointStatus
  priority?: string | null
  riskLevel?: string | null
  scenarioType?: string | null
  reason?: string | null
  aiMeta?: Record<string, unknown> | null
  createdAt?: number | null
  updatedAt?: number | null
}

export type GeneratedCaseDraftStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'COMMITTED'

export type GeneratedCaseDraft = {
  id: string
  projectId: string
  analysisId: string
  testPointId?: string | null
  title: string
  preconditions?: string | null
  steps?: string | null
  expectedResults?: string | null
  priority?: string | null
  status: GeneratedCaseDraftStatus
  createdAt?: number | null
  updatedAt?: number | null
}

export type RequirementCaseLink = {
  id: string
  projectId: string
  docId: string
  docVersionId: string
  analysisId: string
  testPointId?: string | null
  caseDraftId?: string | null
  testcaseId?: string | null
  testcaseTitle?: string | null
  linkType?: string | null
  confidence?: number | null
  createdAt?: number | null
}

export type RequirementDocListResult = {
  items: RequirementDoc[]
  total: number
  page: number
  pageSize: number
}

export type RequirementDocListQuery = {
  page?: number
  pageSize?: number
  status?: string
  q?: string
}

export type RequirementDocUpsertPayload = {
  title: string
  status: RequirementDocStatus
  tags: string[]
  sourceType: RequirementSourceType
}

function normalizeDocList(data: unknown, page: number, pageSize: number): RequirementDocListResult {
  if (Array.isArray(data)) {
    return { items: data as RequirementDoc[], total: data.length, page, pageSize }
  }
  const payload = (data || {}) as { items?: RequirementDoc[]; total?: number; page?: number; pageSize?: number }
  return {
    items: Array.isArray(payload.items) ? payload.items : [],
    total: Number(payload.total || 0),
    page: Number(payload.page || page),
    pageSize: Number(payload.pageSize || pageSize)
  }
}

export async function fetchRequirementDocs(projectId: string, query: RequirementDocListQuery = {}) {
  const pid = String(projectId || '').trim()
  if (!pid) return { items: [], total: 0, page: 1, pageSize: 20 }
  const page = Math.max(1, Number(query.page || 1))
  const pageSize = Math.max(1, Math.min(200, Number(query.pageSize || 20)))
  const params = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize)
  })
  if (query.status) params.set('status', String(query.status).toUpperCase())
  if (query.q) params.set('q', String(query.q))
  const data = await requestJson<RequirementDoc[] | RequirementDocListResult>(
    `/projects/${encodeURIComponent(pid)}/requirements/docs?${params.toString()}`,
    { method: 'GET', headers: authHeader() }
  )
  return normalizeDocList(data, page, pageSize)
}

export async function createRequirementDoc(projectId: string, payload: RequirementDocUpsertPayload) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  return requestJson<RequirementDoc>(`/projects/${encodeURIComponent(pid)}/requirements/docs`, {
    method: 'POST',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...payload,
      status: payload.status.toUpperCase(),
      sourceType: payload.sourceType.toUpperCase()
    })
  })
}

export async function fetchRequirementDoc(projectId: string, docId: string) {
  const pid = String(projectId || '').trim()
  const did = String(docId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!did) throw new Error('文档 ID 不能为空')
  return requestJson<RequirementDoc>(`/projects/${encodeURIComponent(pid)}/requirements/docs/${encodeURIComponent(did)}`, {
    method: 'GET',
    headers: authHeader()
  })
}

export async function updateRequirementDoc(projectId: string, docId: string, payload: RequirementDocUpsertPayload) {
  const pid = String(projectId || '').trim()
  const did = String(docId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!did) throw new Error('文档 ID 不能为空')
  return requestJson<RequirementDoc>(`/projects/${encodeURIComponent(pid)}/requirements/docs/${encodeURIComponent(did)}`, {
    method: 'PUT',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...payload,
      status: payload.status.toUpperCase(),
      sourceType: payload.sourceType.toUpperCase()
    })
  })
}

export async function deleteRequirementDoc(projectId: string, docId: string) {
  const pid = String(projectId || '').trim()
  const did = String(docId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!did) throw new Error('文档 ID 不能为空')
  return requestJson<Record<string, never>>(`/projects/${encodeURIComponent(pid)}/requirements/docs/${encodeURIComponent(did)}`, {
    method: 'DELETE',
    headers: authHeader()
  })
}

export async function fetchRequirementDocVersions(projectId: string, docId: string) {
  const pid = String(projectId || '').trim()
  const did = String(docId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!did) throw new Error('文档 ID 不能为空')
  const data = await requestJson<RequirementDocVersion[] | { items?: RequirementDocVersion[] }>(
    `/projects/${encodeURIComponent(pid)}/requirements/docs/${encodeURIComponent(did)}/versions`,
    { method: 'GET', headers: authHeader() }
  )
  if (Array.isArray(data)) return data
  return Array.isArray(data?.items) ? data.items : []
}

export async function uploadRequirementDocVersion(
  projectId: string,
  docId: string,
  payload: { file: File; changeSummary?: string; effectiveScope?: string }
) {
  const pid = String(projectId || '').trim()
  const did = String(docId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!did) throw new Error('文档 ID 不能为空')
  const form = new FormData()
  form.append('file', payload.file)
  form.append('changeSummary', String(payload.changeSummary || ''))
  form.append('effectiveScope', String(payload.effectiveScope || ''))
  return requestJson<RequirementDocVersion>(`/projects/${encodeURIComponent(pid)}/requirements/docs/${encodeURIComponent(did)}/versions`, {
    method: 'POST',
    headers: authHeader(),
    body: form
  })
}

export async function importRequirementDocVersionFromUrl(
  projectId: string,
  docId: string,
  payload: { url: string; changeSummary?: string; effectiveScope?: string }
) {
  const pid = String(projectId || '').trim()
  const did = String(docId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!did) throw new Error('文档 ID 不能为空')
  return requestJson<{ id: string; version: number }>(
    `/projects/${encodeURIComponent(pid)}/requirements/docs/${encodeURIComponent(did)}/versions/import-url`,
    {
      method: 'POST',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }
  )
}

export async function parseRequirementDocVersion(projectId: string, docId: string, versionId: string) {
  const pid = String(projectId || '').trim()
  const did = String(docId || '').trim()
  const vid = String(versionId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!did) throw new Error('文档 ID 不能为空')
  if (!vid) throw new Error('版本 ID 不能为空')
  return requestJson<Record<string, unknown>>(
    `/projects/${encodeURIComponent(pid)}/requirements/docs/${encodeURIComponent(did)}/versions/${encodeURIComponent(vid)}/parse`,
    { method: 'POST', headers: authHeader() }
  )
}

export async function fetchRequirementDocParsedText(projectId: string, docId: string, versionId: string) {
  const pid = String(projectId || '').trim()
  const did = String(docId || '').trim()
  const vid = String(versionId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!did) throw new Error('文档 ID 不能为空')
  if (!vid) throw new Error('版本 ID 不能为空')
  const data = await requestJson<string | { parsedText?: string; text?: string }>(
    `/projects/${encodeURIComponent(pid)}/requirements/docs/${encodeURIComponent(did)}/versions/${encodeURIComponent(vid)}/parsed-text`,
    { method: 'GET', headers: authHeader() }
  )
  if (typeof data === 'string') return data
  return String(data?.parsedText || data?.text || '')
}

export async function generateRequirementAnalysis(projectId: string, docId: string, versionId: string, instruction = '') {
  const pid = String(projectId || '').trim()
  const did = String(docId || '').trim()
  const vid = String(versionId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!did) throw new Error('文档 ID 不能为空')
  if (!vid) throw new Error('版本 ID 不能为空')
  return requestJson<RequirementAnalysis>(
    `/projects/${encodeURIComponent(pid)}/requirements/docs/${encodeURIComponent(did)}/versions/${encodeURIComponent(vid)}/analyze`,
    {
      method: 'POST',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ instruction })
    }
  )
}

export async function fetchRequirementAnalyses(projectId: string, query: { docId?: string; versionId?: string } = {}) {
  const pid = String(projectId || '').trim()
  if (!pid) return []
  const params = new URLSearchParams()
  if (query.docId) params.set('docId', query.docId)
  if (query.versionId) params.set('versionId', query.versionId)
  const suffix = params.toString() ? `?${params.toString()}` : ''
  return requestJson<RequirementAnalysis[]>(`/projects/${encodeURIComponent(pid)}/requirements/analyses${suffix}`, {
    method: 'GET',
    headers: authHeader()
  })
}

export async function fetchRequirementAnalysis(projectId: string, analysisId: string) {
  const pid = String(projectId || '').trim()
  const aid = String(analysisId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!aid) throw new Error('分析 ID 不能为空')
  return requestJson<RequirementAnalysis>(`/projects/${encodeURIComponent(pid)}/requirements/analyses/${encodeURIComponent(aid)}`, {
    method: 'GET',
    headers: authHeader()
  })
}

export async function updateRequirementAnalysis(projectId: string, analysisId: string, payload: Partial<RequirementAnalysis>) {
  const pid = String(projectId || '').trim()
  const aid = String(analysisId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!aid) throw new Error('分析 ID 不能为空')
  return requestJson<RequirementAnalysis>(`/projects/${encodeURIComponent(pid)}/requirements/analyses/${encodeURIComponent(aid)}`, {
    method: 'PUT',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export async function fetchRequirementAnalysisRevisions(projectId: string, analysisId: string) {
  const pid = String(projectId || '').trim()
  const aid = String(analysisId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!aid) throw new Error('分析 ID 不能为空')
  return requestJson<RequirementAnalysisRevision[]>(
    `/projects/${encodeURIComponent(pid)}/requirements/analyses/${encodeURIComponent(aid)}/revisions`,
    {
      method: 'GET',
      headers: authHeader()
    }
  )
}

export async function rollbackRequirementAnalysisRevision(projectId: string, analysisId: string, revisionId: string) {
  const pid = String(projectId || '').trim()
  const aid = String(analysisId || '').trim()
  const rid = String(revisionId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!aid) throw new Error('分析 ID 不能为空')
  if (!rid) throw new Error('修订 ID 不能为空')
  return requestJson<RequirementAnalysis>(`/projects/${encodeURIComponent(pid)}/requirements/analyses/${encodeURIComponent(aid)}/rollback`, {
    method: 'POST',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ revisionId: rid })
  })
}

export async function rollbackRequirementDocVersion(
  projectId: string,
  docId: string,
  versionId: string
) {
  const pid = String(projectId || '').trim()
  const did = String(docId || '').trim()
  const vid = String(versionId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!did) throw new Error('文档 ID 不能为空')
  if (!vid) throw new Error('版本 ID 不能为空')
  return requestJson<{ id: string; currentVersionId: string }>(
    `/projects/${encodeURIComponent(pid)}/requirements/docs/${encodeURIComponent(did)}/rollback`,
    {
      method: 'POST',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ versionId: vid }),
    }
  )
}

function normalizeTestPoint(data: unknown): RequirementTestPoint {
  const row = (data || {}) as Record<string, unknown>
  return {
    id: String(row.id || ''),
    projectId: String(row.projectId || row.project_id || ''),
    analysisId: String(row.analysisId || row.analysis_id || ''),
    title: String(row.title || row.name || ''),
    description: row.description == null ? null : String(row.description),
    status: String(row.status || 'DRAFT').toUpperCase() as RequirementTestPointStatus,
    priority: row.priority == null ? null : String(row.priority),
    riskLevel: row.riskLevel == null ? (row.risk_level == null ? (row.risk == null ? null : String(row.risk)) : String(row.risk_level)) : String(row.riskLevel),
    scenarioType: row.scenarioType == null ? (row.scenario_type == null ? (row.scenario == null ? null : String(row.scenario)) : String(row.scenario_type)) : String(row.scenarioType),
    reason: row.reason == null ? null : String(row.reason),
    aiMeta: row.aiMeta && typeof row.aiMeta === 'object' ? row.aiMeta as Record<string, unknown> : (row.ai_meta && typeof row.ai_meta === 'object' ? row.ai_meta as Record<string, unknown> : null),
    createdAt: row.createdAt == null ? (row.created_at == null ? null : Number(row.created_at)) : Number(row.createdAt),
    updatedAt: row.updatedAt == null ? (row.updated_at == null ? null : Number(row.updated_at)) : Number(row.updatedAt)
  }
}

function normalizeListText(value: unknown) {
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object') {
          const row = item as Record<string, unknown>
          return String(row.step || row.title || row.description || JSON.stringify(row))
        }
        return String(item ?? '')
      })
      .filter(Boolean)
      .map((item, index) => `${index + 1}. ${item}`)
      .join('\n')
  }
  return value == null ? null : String(value)
}

function normalizeCaseDraft(data: unknown): GeneratedCaseDraft {
  const row = (data || {}) as Record<string, unknown>
  return {
    id: String(row.id || ''),
    projectId: String(row.projectId || row.project_id || ''),
    analysisId: String(row.analysisId || row.analysis_id || ''),
    testPointId: row.testPointId == null ? (row.test_point_id == null ? null : String(row.test_point_id)) : String(row.testPointId),
    title: String(row.title || row.name || ''),
    preconditions: row.preconditions == null ? null : String(row.preconditions),
    steps: normalizeListText(row.steps),
    expectedResults: normalizeListText(row.expectedResults == null ? row.expected_results : row.expectedResults),
    priority: row.priority == null ? null : String(row.priority),
    status: String(row.status || 'PENDING').toUpperCase() as GeneratedCaseDraftStatus,
    createdAt: row.createdAt == null ? (row.created_at == null ? null : Number(row.created_at)) : Number(row.createdAt),
    updatedAt: row.updatedAt == null ? (row.updated_at == null ? null : Number(row.updated_at)) : Number(row.updatedAt)
  }
}

function normalizeCaseLink(data: unknown): RequirementCaseLink {
  const row = (data || {}) as Record<string, unknown>
  return {
    id: String(row.id || ''),
    projectId: String(row.projectId || row.project_id || ''),
    docId: String(row.docId || row.doc_id || ''),
    docVersionId: String(row.docVersionId || row.doc_version_id || ''),
    analysisId: String(row.analysisId || row.analysis_id || ''),
    testPointId: row.testPointId == null ? (row.test_point_id == null ? null : String(row.test_point_id)) : String(row.testPointId),
    caseDraftId: row.caseDraftId == null ? (row.case_draft_id == null ? null : String(row.case_draft_id)) : String(row.caseDraftId),
    testcaseId: row.testcaseId == null ? (row.testcase_id == null ? null : String(row.testcase_id)) : String(row.testcaseId),
    testcaseTitle: row.testcaseTitle == null ? (row.testcase_title == null ? null : String(row.testcase_title)) : String(row.testcaseTitle),
    linkType: row.linkType == null ? (row.link_type == null ? null : String(row.link_type)) : String(row.linkType),
    confidence: row.confidence == null ? null : Number(row.confidence),
    createdAt: row.createdAt == null ? (row.created_at == null ? null : Number(row.created_at)) : Number(row.createdAt)
  }
}

export async function syncRequirementTestPoints(projectId: string, analysisId: string) {
  const pid = String(projectId || '').trim()
  const aid = String(analysisId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!aid) throw new Error('分析 ID 不能为空')
  const data = await requestJson<RequirementTestPoint[] | { items?: RequirementTestPoint[] }>(
    `/projects/${encodeURIComponent(pid)}/requirements/analyses/${encodeURIComponent(aid)}/sync-test-points`,
    { method: 'POST', headers: authHeader() }
  )
  const rows = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []
  return rows.map(normalizeTestPoint)
}

export async function fetchRequirementTestPoints(projectId: string, analysisId: string) {
  const pid = String(projectId || '').trim()
  const aid = String(analysisId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!aid) throw new Error('分析 ID 不能为空')
  const data = await requestJson<RequirementTestPoint[] | { items?: RequirementTestPoint[] }>(
    `/projects/${encodeURIComponent(pid)}/requirements/analyses/${encodeURIComponent(aid)}/test-points`,
    { method: 'GET', headers: authHeader() }
  )
  const rows = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []
  return rows.map(normalizeTestPoint)
}

export async function updateRequirementTestPoint(projectId: string, testPointId: string, payload: { status: RequirementTestPointStatus; reason?: string }) {
  const pid = String(projectId || '').trim()
  const tid = String(testPointId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!tid) throw new Error('测试点 ID 不能为空')
  const data = await requestJson<RequirementTestPoint>(
    `/projects/${encodeURIComponent(pid)}/requirements/test-points/${encodeURIComponent(tid)}`,
    {
      method: 'PUT',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: payload.status })
    }
  )
  return normalizeTestPoint(data)
}

export async function generateRequirementCaseDrafts(projectId: string, analysisId: string) {
  const pid = String(projectId || '').trim()
  const aid = String(analysisId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!aid) throw new Error('分析 ID 不能为空')
  const data = await requestJson<GeneratedCaseDraft[] | { items?: GeneratedCaseDraft[] }>(
    `/projects/${encodeURIComponent(pid)}/requirements/analyses/${encodeURIComponent(aid)}/generate-case-drafts`,
    {
      method: 'POST',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'ACCEPTED_ONLY', testPointIds: [], forceRegenerate: false })
    }
  )
  const rows = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []
  return rows.map(normalizeCaseDraft)
}

export async function fetchRequirementCaseDrafts(projectId: string, analysisId: string) {
  const pid = String(projectId || '').trim()
  const aid = String(analysisId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!aid) throw new Error('分析 ID 不能为空')
  const data = await requestJson<GeneratedCaseDraft[] | { items?: GeneratedCaseDraft[] }>(
    `/projects/${encodeURIComponent(pid)}/requirements/analyses/${encodeURIComponent(aid)}/case-drafts`,
    { method: 'GET', headers: authHeader() }
  )
  const rows = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []
  return rows.map(normalizeCaseDraft)
}

export async function fetchRequirementCaseLinks(projectId: string, analysisId: string) {
  const pid = String(projectId || '').trim()
  const aid = String(analysisId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!aid) throw new Error('分析 ID 不能为空')
  const data = await requestJson<RequirementCaseLink[] | { items?: RequirementCaseLink[] }>(
    `/projects/${encodeURIComponent(pid)}/requirements/analyses/${encodeURIComponent(aid)}/case-links`,
    { method: 'GET', headers: authHeader() }
  )
  const rows = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []
  return rows.map(normalizeCaseLink)
}

export async function bulkApproveRequirementCaseDrafts(projectId: string, draftIds: string[]) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  const ids = (draftIds || []).map((item) => String(item || '').trim()).filter(Boolean)
  if (ids.length === 0) throw new Error('请先选择需要审核入库的草稿')
  return requestJson<Record<string, unknown>>(`/projects/${encodeURIComponent(pid)}/requirements/case-drafts/bulk-approve`, {
    method: 'POST',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ draftIds: ids })
  })
}
