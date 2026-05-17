import { authHeader, requestJson } from '@/lib/api/client'

export type AiJobRecord = {
  id: string
  projectId: string
  jobType: string
  status: string
  triggerSource: string
  summary?: string | null
  createdBy?: string | null
  createdAt: number
}

export type AuditLogRecord = {
  id: string
  projectId?: string | null
  module?: string | null
  action: string
  resourceType: string
  resourceId: string
  summary?: string | null
  detail: Record<string, unknown>
  userId?: string | null
  createdAt: number
}

type RecordFilters = {
  page?: number
  pageSize?: number
  status?: string
  type?: string
}

function buildQuery(filters: RecordFilters = {}) {
  const page = Math.max(1, Number(filters.page || 1))
  const pageSize = Math.max(1, Math.min(200, Number(filters.pageSize || 20)))
  const params = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize)
  })
  if (filters.status) params.set('status', String(filters.status).trim())
  if (filters.type) params.set('type', String(filters.type).trim())
  return params.toString()
}

function normalizeList<T>(data: T[] | { items?: T[] }) {
  if (Array.isArray(data)) return data
  return Array.isArray(data?.items) ? data.items : []
}

export async function fetchAiJobs(projectId: string, filters: RecordFilters = {}) {
  const pid = String(projectId || '').trim()
  if (!pid) return []
  const query = buildQuery(filters)
  const data = await requestJson<AiJobRecord[] | { items?: AiJobRecord[] }>(
    `/api/projects/${encodeURIComponent(pid)}/platform/ai-jobs?${query}`,
    { method: 'GET', headers: authHeader() }
  )
  return normalizeList(data)
}

export async function fetchAuditLogs(projectId: string, filters: RecordFilters = {}) {
  const pid = String(projectId || '').trim()
  if (!pid) return []
  const query = buildQuery(filters)
  const data = await requestJson<AuditLogRecord[] | { items?: AuditLogRecord[] }>(
    `/api/projects/${encodeURIComponent(pid)}/platform/audit-logs?${query}`,
    { method: 'GET', headers: authHeader() }
  )
  return normalizeList(data)
}
