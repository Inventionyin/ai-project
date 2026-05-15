import { authHeader, requestJson } from '@/lib/api/client'

export type WorkerStatus = 'ONLINE' | 'OFFLINE'
export type WorkerCapability = 'API' | 'UI' | 'PERF'

export type WorkerAdminListItem = {
  id: string
  name: string
  status: WorkerStatus
  slots: number
  capabilities: WorkerCapability[]
  lastSeenAt?: number | null
  version?: string | null
  updatedAt: number
}

type WorkerFilters = {
  page?: number
  pageSize?: number
  status?: WorkerStatus | ''
}

function buildQuery(filters: WorkerFilters = {}) {
  const page = Math.max(1, Number(filters.page || 1))
  const pageSize = Math.max(1, Math.min(200, Number(filters.pageSize || 20)))
  const params = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize)
  })
  if (filters.status) params.set('status', filters.status)
  return params.toString()
}

function normalizePage<T>(data: T[] | { total?: number; items?: T[] }) {
  if (Array.isArray(data)) {
    return { total: data.length, items: data }
  }
  return {
    total: Number(data?.total || 0),
    items: Array.isArray(data?.items) ? data.items : []
  }
}

export async function fetchWorkers(filters: WorkerFilters = {}) {
  const query = buildQuery(filters)
  const data = await requestJson<WorkerAdminListItem[] | { total?: number; items?: WorkerAdminListItem[] }>(
    `/api/workers?${query}`,
    { method: 'GET', headers: authHeader() }
  )
  return normalizePage(data)
}
