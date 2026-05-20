import { authHeader, requestJson } from '@/lib/api/client'

export type KnowledgeRetrospectiveStatus = 'DRAFT' | 'REVIEWING' | 'PUBLISHED' | 'ARCHIVED'
export type KnowledgeRetrospectiveSourceType = 'PRD' | 'SPEC' | 'PROTOTYPE' | 'DEFECT' | 'OTHER'

export type KnowledgeRetrospective = {
  id: string
  projectId: string
  title: string
  sourceType: KnowledgeRetrospectiveSourceType | string
  status: KnowledgeRetrospectiveStatus | string
  problemSummary?: string | null
  rootCause?: string | null
  decision?: string | null
  actionItems?: string | null
  createdAt?: number | null
  updatedAt?: number | null
}

export type KnowledgeRetrospectiveListQuery = {
  page?: number
  pageSize?: number
  sourceType?: string
  status?: string
}

export type KnowledgeRetrospectiveListResult = {
  items: KnowledgeRetrospective[]
  total: number
  page: number
  pageSize: number
}

export type KnowledgeRetrospectiveCreatePayload = {
  title: string
  sourceType: KnowledgeRetrospectiveSourceType | string
  problemSummary: string
  rootCause: string
  decision: string
  actionItems: string
}

export type KnowledgeRetrospectiveUpdatePayload = {
  problemSummary?: string
  rootCause?: string
  decision?: string
  actionItems?: string
  status?: KnowledgeRetrospectiveStatus | string
}

export type KnowledgeRecommendation = {
  id: string
  content: string
  score?: number | null
  type: string
  status: string
}

export type KnowledgeRecommendationStatus = 'PENDING' | 'ADOPTED' | 'REJECTED' | string

export type KnowledgeRecommendationEvaluateResult = {
  targetType: string
  targetId: string
  recommendations: KnowledgeRecommendation[]
}

function requireId(value: string, message: string) {
  const normalized = String(value || '').trim()
  if (!normalized) throw new Error(message)
  return normalized
}

export async function evaluateKnowledgeRecommendations(projectId: string, targetType: string, targetId: string, topK = 5) {
  const pid = requireId(projectId, '项目 ID 不能为空')
  const normalizedTargetType = requireId(targetType, '目标类型不能为空').toUpperCase()
  const normalizedTargetId = requireId(targetId, '目标 ID 不能为空')
  const normalizedTopK = Math.max(1, Math.min(100, Number(topK || 5)))
  return requestJson<KnowledgeRecommendationEvaluateResult>(`/projects/${encodeURIComponent(pid)}/knowledge/recommendations/evaluate`, {
    method: 'POST',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({
      targetType: normalizedTargetType,
      targetId: normalizedTargetId,
      topK: normalizedTopK
    })
  })
}

export async function updateKnowledgeRecommendationStatus(
  projectId: string,
  recommendationId: string,
  status: KnowledgeRecommendationStatus
) {
  const pid = requireId(projectId, '项目 ID 不能为空')
  const rid = requireId(recommendationId, '推荐 ID 不能为空')
  const normalizedStatus = requireId(status, '推荐状态不能为空').toUpperCase()
  return requestJson<KnowledgeRecommendation>(`/projects/${encodeURIComponent(pid)}/knowledge/recommendations/${encodeURIComponent(rid)}/status`, {
    method: 'PUT',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: normalizedStatus })
  })
}

export async function createRunRetrospectiveDraft(projectId: string, runId: string) {
  const pid = requireId(projectId, '项目 ID 不能为空')
  const rid = requireId(runId, '运行 ID 不能为空')
  return requestJson<KnowledgeRetrospective>(`/projects/${encodeURIComponent(pid)}/knowledge/retrospectives/draft-from-run`, {
    method: 'POST',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ runId: rid })
  })
}

function normalizeList(data: unknown, page: number, pageSize: number): KnowledgeRetrospectiveListResult {
  if (Array.isArray(data)) {
    return { items: data as KnowledgeRetrospective[], total: data.length, page, pageSize }
  }
  const payload = (data || {}) as { items?: KnowledgeRetrospective[]; total?: number; page?: number; pageSize?: number }
  return {
    items: Array.isArray(payload.items) ? payload.items : [],
    total: Number(payload.total || 0),
    page: Number(payload.page || page),
    pageSize: Number(payload.pageSize || pageSize)
  }
}

export async function fetchKnowledgeRetrospectives(projectId: string, query: KnowledgeRetrospectiveListQuery = {}) {
  const pid = String(projectId || '').trim()
  if (!pid) return { items: [], total: 0, page: 1, pageSize: 20 }
  const page = Math.max(1, Number(query.page || 1))
  const pageSize = Math.max(1, Math.min(200, Number(query.pageSize || 20)))
  const params = new URLSearchParams({ page: String(page), pageSize: String(pageSize) })
  if (query.sourceType) params.set('sourceType', String(query.sourceType).toUpperCase())
  if (query.status) params.set('status', String(query.status).toUpperCase())
  const data = await requestJson<KnowledgeRetrospective[] | KnowledgeRetrospectiveListResult>(
    `/projects/${encodeURIComponent(pid)}/knowledge/retrospectives?${params.toString()}`,
    { method: 'GET', headers: authHeader() }
  )
  return normalizeList(data, page, pageSize)
}

export async function createKnowledgeRetrospective(projectId: string, payload: KnowledgeRetrospectiveCreatePayload) {
  const pid = requireId(projectId, '项目 ID 不能为空')
  return requestJson<KnowledgeRetrospective>(`/projects/${encodeURIComponent(pid)}/knowledge/retrospectives`, {
    method: 'POST',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...payload,
      sourceType: String(payload.sourceType || 'OTHER').toUpperCase()
    })
  })
}

export async function fetchKnowledgeRetrospectiveDetail(projectId: string, retrospectiveId: string) {
  const pid = requireId(projectId, '项目 ID 不能为空')
  const rid = requireId(retrospectiveId, '复盘 ID 不能为空')
  return requestJson<KnowledgeRetrospective>(
    `/projects/${encodeURIComponent(pid)}/knowledge/retrospectives/${encodeURIComponent(rid)}`,
    { method: 'GET', headers: authHeader() }
  )
}

export async function updateKnowledgeRetrospective(projectId: string, retrospectiveId: string, payload: KnowledgeRetrospectiveUpdatePayload) {
  const pid = requireId(projectId, '项目 ID 不能为空')
  const rid = requireId(retrospectiveId, '复盘 ID 不能为空')
  return requestJson<KnowledgeRetrospective>(
    `/projects/${encodeURIComponent(pid)}/knowledge/retrospectives/${encodeURIComponent(rid)}`,
    {
      method: 'PUT',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...payload,
        status: payload.status ? String(payload.status).toUpperCase() : undefined
      })
    }
  )
}
