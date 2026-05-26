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

export type PostmanCloudCollection = {
  id?: string | null
  uid: string
  name: string
  updatedAt?: string | null
}

export type ApiAssetBinding = {
  id: string
  projectId: string
  testcaseId: string
  name: string
  linkType: 'API_TARGET' | 'REQUEST' | 'COLLECTION'
  datasetId?: string | null
  apiTargetId?: string | null
  requestId?: string | null
  collectionId?: string | null
  sourceType: 'MANUAL' | 'AI' | 'IMPORT'
  assertSummary: string
  lastRunStatus?: string | null
  lastRunAt?: number | null
  params?: Record<string, unknown> | null
  priority?: number | null
  enabled?: boolean
  version: number
  updatedAt: number
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

export type ApiRequestRunResult = {
  collectionId: string
  requestId: string
  envId?: string | null
  ok: boolean
  status?: number | null
  elapsedMs: number
  error?: string | null
  response?: {
    headers?: Record<string, string>
    body?: string
  }
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
  return requestJson<ApiRequestRunResult>(`/api/collections/${encodeURIComponent(cid)}/requests/${encodeURIComponent(rid)}/run`, {
    method: 'POST',
    headers: {
      ...authHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ envId: payload.envId ?? null })
  })
}

export async function fetchRequestBindings(projectId: string, requestId: string) {
  const pid = String(projectId || '').trim()
  const rid = String(requestId || '').trim()
  if (!pid || !rid) return []
  const data = await requestJson<ApiAssetBinding[] | { items?: ApiAssetBinding[] }>(
    `/api/projects/${encodeURIComponent(pid)}/requests/${encodeURIComponent(rid)}/bindings`,
    { method: 'GET', headers: authHeader() }
  )
  if (Array.isArray(data)) return data
  return Array.isArray(data?.items) ? data.items : []
}

export async function fetchCollectionBindings(projectId: string, collectionId: string) {
  const pid = String(projectId || '').trim()
  const cid = String(collectionId || '').trim()
  if (!pid || !cid) return []
  const data = await requestJson<ApiAssetBinding[] | { items?: ApiAssetBinding[] }>(
    `/api/projects/${encodeURIComponent(pid)}/collections/${encodeURIComponent(cid)}/bindings`,
    { method: 'GET', headers: authHeader() }
  )
  if (Array.isArray(data)) return data
  return Array.isArray(data?.items) ? data.items : []
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

export async function fetchPostmanCloudCollections(payload: { projectId: string; apiKey?: string; workspaceId?: string }) {
  return requestJson<{ items: PostmanCloudCollection[] }>('/api/collections/postman/cloud/list', {
    method: 'POST',
    headers: {
      ...authHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      projectId: payload.projectId,
      apiKey: payload.apiKey?.trim() || undefined,
      workspaceId: payload.workspaceId?.trim() || undefined
    })
  })
}

export async function syncPostmanCloudCollection(payload: { projectId: string; collectionUid: string; apiKey?: string; workspaceId?: string }) {
  return requestJson<{ postmanUid: string; collection: CollectionDetail }>('/api/collections/postman/cloud/sync', {
    method: 'POST',
    headers: {
      ...authHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      projectId: payload.projectId,
      collectionUid: payload.collectionUid,
      apiKey: payload.apiKey?.trim() || undefined,
      workspaceId: payload.workspaceId?.trim() || undefined
    })
  })
}
