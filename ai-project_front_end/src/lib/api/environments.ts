type ApiResponse<T> = {
  code?: number
  message?: string
  data?: T
  requestId?: string
}

import { createApiError, handleAuthExpired, isAuthExpiredResponse } from '@/lib/api/client'

export type HealthCheckConfig = {
  url: string
  timeoutMs: number
  expectedStatus: number
}

export type EnvironmentPublic = {
  id: string
  projectId: string
  name: string
  baseUrl: string
  variables: Record<string, string>
  secretKeys: string[]
  healthCheck: HealthCheckConfig | null
  createdAt?: number | null
  updatedAt?: number | null
}

export type EnvironmentUpsertPayload = {
  name: string
  baseUrl: string
  variables: Record<string, string>
  secrets: Record<string, string>
  healthCheck: HealthCheckConfig | null
}

const resolveApiBaseUrl = () => {
  const envBase = String(import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!envBase) return ''
  return envBase.endsWith('/') ? envBase.slice(0, -1) : envBase
}

const resolveAuthHeader = () => {
  const accessToken = localStorage.getItem('accessToken')
  if (!accessToken) throw new Error('登录状态已失效，请重新登录')
  return `Bearer ${accessToken}`
}

async function requestJson<T>(path: string, init: RequestInit) {
  const res = await fetch(`${resolveApiBaseUrl()}${path}`, init)
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

export async function listEnvironments(projectId: string) {
  const pid = String(projectId || '').trim()
  if (!pid) return []
  return requestJson<EnvironmentPublic[]>(`/api/projects/${encodeURIComponent(pid)}/environments`, {
    method: 'GET',
    headers: { Authorization: resolveAuthHeader() }
  })
}

export async function createEnvironment(projectId: string, payload: EnvironmentUpsertPayload) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  return requestJson<EnvironmentPublic>(`/api/projects/${encodeURIComponent(pid)}/environments`, {
    method: 'POST',
    headers: {
      Authorization: resolveAuthHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
}

export async function updateEnvironment(projectId: string, envId: string, payload: EnvironmentUpsertPayload) {
  const pid = String(projectId || '').trim()
  const id = String(envId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!id) throw new Error('环境 ID 不能为空')
  return requestJson<EnvironmentPublic>(`/api/projects/${encodeURIComponent(pid)}/environments/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: {
      Authorization: resolveAuthHeader(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
}

export async function deleteEnvironment(projectId: string, envId: string) {
  const pid = String(projectId || '').trim()
  const id = String(envId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!id) throw new Error('环境 ID 不能为空')
  return requestJson<Record<string, never>>(`/api/projects/${encodeURIComponent(pid)}/environments/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    headers: { Authorization: resolveAuthHeader() }
  })
}
