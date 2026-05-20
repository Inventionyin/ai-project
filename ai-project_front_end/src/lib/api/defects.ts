import { authHeader, requestJson } from '@/lib/api/client'

export type DefectStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED'

export type DefectListItem = {
  id: string
  projectId: string
  title: string
  status: DefectStatus | string
  assigneeId?: string | null
  assigneeName?: string | null
  runId?: string | null
  caseRunId?: string | null
  testcaseId?: string | null
  updatedAt?: number | null
  createdAt?: number | null
}

export type DefectEvent = {
  id?: string
  type?: string
  operatorId?: string | null
  operatorName?: string | null
  content?: string | null
  createdAt?: number | null
}

export type DefectDetailData = DefectListItem & {
  description?: string | null
  timeline?: DefectEvent[]
  events?: DefectEvent[]
}

export type DefectListFilters = {
  projectId: string
  page?: number
  pageSize?: number
  status?: string
  q?: string
  runId?: string
  caseRunId?: string
  testcaseId?: string
}

export type DefectCreatePayload = {
  projectId: string
  title: string
  description?: string
  severity?: string
  assigneeId?: string | null
  runId?: string | null
  caseRunId?: string | null
  testcaseId?: string | null
  errorMessage?: string | null
}

function normalizePage<T>(data: T[] | { total?: number; items?: T[] }) {
  if (Array.isArray(data)) return { total: data.length, items: data }
  return {
    total: Number(data?.total || 0),
    items: Array.isArray(data?.items) ? data.items : []
  }
}

export async function listDefects(filters: DefectListFilters) {
  const pid = String(filters.projectId || '').trim()
  if (!pid) return { total: 0, items: [] as DefectListItem[] }
  const page = Math.max(1, Number(filters.page || 1))
  const pageSize = Math.max(1, Math.min(200, Number(filters.pageSize || 20)))
  const query = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize)
  })
  if (filters.status) query.set('status', String(filters.status).trim())
  if (filters.q) query.set('q', String(filters.q).trim())
  if (filters.runId) query.set('runId', String(filters.runId).trim())
  if (filters.caseRunId) query.set('caseRunId', String(filters.caseRunId).trim())
  if (filters.testcaseId) query.set('testcaseId', String(filters.testcaseId).trim())
  const data = await requestJson<DefectListItem[] | { total?: number; items?: DefectListItem[] }>(
    `/api/projects/${encodeURIComponent(pid)}/defects?${query.toString()}`,
    { method: 'GET', headers: authHeader() }
  )
  return normalizePage(data)
}

export async function createDefect(payload: DefectCreatePayload) {
  const pid = String(payload.projectId || '').trim()
  if (!pid) throw new Error('projectId 不能为空')
  const title = String(payload.title || '').trim()
  if (!title) throw new Error('title 不能为空')
  const severityRaw = String(payload.severity || 'P2').trim().toUpperCase()
  const severity = ['P0', 'P1', 'P2', 'P3'].includes(severityRaw) ? severityRaw : 'P2'

  const descriptionParts: string[] = []
  const plainDesc = String(payload.description || '').trim()
  if (plainDesc) descriptionParts.push(plainDesc)

  const runId = String(payload.runId || '').trim()
  const caseRunId = String(payload.caseRunId || '').trim()
  const testcaseId = String(payload.testcaseId || '').trim()
  const errorMessage = String(payload.errorMessage || '').trim()
  const contextParts = [runId ? `runId=${runId}` : '', caseRunId ? `caseRunId=${caseRunId}` : '', testcaseId ? `testcaseId=${testcaseId}` : '', errorMessage ? `errorMessage=${errorMessage}` : ''].filter(Boolean)
  if (contextParts.length) {
    descriptionParts.push(`[Context] ${contextParts.join(' | ')}`)
  }

  return requestJson<DefectDetailData>(`/api/projects/${encodeURIComponent(pid)}/defects`, {
    method: 'POST',
    headers: {
      ...authHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      title,
      description: descriptionParts.join('\n') || undefined,
      severity
    })
  })
}

export async function getDefectDetail(projectId: string, defectId: string) {
  const pid = String(projectId || '').trim()
  const did = String(defectId || '').trim()
  if (!pid) throw new Error('projectId 不能为空')
  if (!did) throw new Error('defectId 不能为空')
  return requestJson<DefectDetailData>(`/api/projects/${encodeURIComponent(pid)}/defects/${encodeURIComponent(did)}`, {
    method: 'GET',
    headers: authHeader()
  })
}

export async function assignDefect(projectId: string, defectId: string, assigneeId: string) {
  const pid = String(projectId || '').trim()
  const did = String(defectId || '').trim()
  const aid = String(assigneeId || '').trim()
  if (!pid) throw new Error('projectId 不能为空')
  if (!did) throw new Error('defectId 不能为空')
  if (!aid) throw new Error('assigneeId 不能为空')
  return requestJson<DefectDetailData>(`/api/projects/${encodeURIComponent(pid)}/defects/${encodeURIComponent(did)}/assign`, {
    method: 'POST',
    headers: {
      ...authHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ assigneeId: aid })
  })
}

export async function transitionDefect(projectId: string, defectId: string, toStatus: string, comment?: string) {
  const pid = String(projectId || '').trim()
  const did = String(defectId || '').trim()
  const status = String(toStatus || '').trim()
  if (!pid) throw new Error('projectId 不能为空')
  if (!did) throw new Error('defectId 不能为空')
  if (!status) throw new Error('toStatus 不能为空')
  return requestJson<DefectDetailData>(`/api/projects/${encodeURIComponent(pid)}/defects/${encodeURIComponent(did)}/transition`, {
    method: 'POST',
    headers: {
      ...authHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ toStatus: status, note: comment ? String(comment) : '' })
  })
}
