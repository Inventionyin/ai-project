import { authHeader, requestJson } from '@/lib/api/client'

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

export type ApiRequestCreateRequest = {
  groupId?: string | null
  name: string
  method: string
  url: string
  headers?: Record<string, unknown>
  auth?: Record<string, unknown>
  body?: Record<string, unknown>
  asserts?: Record<string, unknown>
}

export type RunApiRequestPayload = {
  envId?: string | null
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
    headers: authHeader()
  })
  if (Array.isArray(data)) return data
  return Array.isArray(data?.items) ? data.items : []
}

export async function fetchCollectionDetail(collectionId: string) {
  const id = String(collectionId || '').trim()
  if (!id) throw new Error('集合 ID 不能为空')
  return requestJson<CollectionDetail>(`/api/collections/${encodeURIComponent(id)}`, {
    method: 'GET',
    headers: authHeader()
  })
}

export async function createCollection(payload: { projectId: string; name: string; variables?: Record<string, unknown> }) {
  return requestJson<CollectionDetail>('/api/collections', {
    method: 'POST',
    headers: {
      ...authHeader(),
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
      ...authHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
}

export async function createCollectionRequest(collectionId: string, payload: ApiRequestCreateRequest) {
  const id = String(collectionId || '').trim()
  if (!id) throw new Error('集合 ID 不能为空')
  return requestJson<CollectionRequest>(`/api/collections/${encodeURIComponent(id)}/requests`, {
    method: 'POST',
    headers: {
      ...authHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
}

export async function fetchCollectionRequestDetail(collectionId: string, requestId: string) {
  const cid = String(collectionId || '').trim()
  const rid = String(requestId || '').trim()
  if (!cid) throw new Error('集合 ID 不能为空')
  if (!rid) throw new Error('请求 ID 不能为空')
  return requestJson<CollectionRequest>(`/api/collections/${encodeURIComponent(cid)}/requests/${encodeURIComponent(rid)}`, {
    method: 'GET',
    headers: authHeader()
  })
}

export async function updateCollectionRequest(collectionId: string, requestId: string, payload: ApiRequestCreateRequest) {
  const cid = String(collectionId || '').trim()
  const rid = String(requestId || '').trim()
  if (!cid) throw new Error('集合 ID 不能为空')
  if (!rid) throw new Error('请求 ID 不能为空')
  return requestJson<CollectionRequest>(`/api/collections/${encodeURIComponent(cid)}/requests/${encodeURIComponent(rid)}`, {
    method: 'PUT',
    headers: {
      ...authHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
}

export async function runCollectionRequest(collectionId: string, requestId: string, payload: RunApiRequestPayload = {}) {
  const cid = String(collectionId || '').trim()
  const rid = String(requestId || '').trim()
  if (!cid) throw new Error('集合 ID 不能为空')
  if (!rid) throw new Error('请求 ID 不能为空')
  return requestJson<Record<string, unknown>>(`/api/collections/${encodeURIComponent(cid)}/requests/${encodeURIComponent(rid)}/run`, {
    method: 'POST',
    headers: {
      ...authHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ envId: payload.envId ?? null })
  })
}

export async function exportCollection(collectionId: string, format: 'postman' | 'swagger' | 'curl' = 'postman') {
  const cid = String(collectionId || '').trim()
  if (!cid) throw new Error('集合 ID 不能为空')
  const query = new URLSearchParams({ format })
  return requestJson<{ format: string; content: string }>(
    `/api/collections/${encodeURIComponent(cid)}/export?${query.toString()}`,
    {
      method: 'GET',
      headers: authHeader()
    }
  )
}

export async function importCollection(payload: { projectId: string; format: 'postman' | 'swagger'; content: string }) {
  return requestJson<CollectionDetail>('/api/collections/import', {
    method: 'POST',
    headers: {
      ...authHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
}
