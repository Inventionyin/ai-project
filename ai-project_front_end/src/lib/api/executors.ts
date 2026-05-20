import { requestJson, authHeader } from './client'

export interface Executor {
  id: string
  projectId: string
  name: string
  executorType: string
  description: string | null
  config: Record<string, unknown> | null
  enabled: boolean
  version: string | null
  createdBy: string | null
  createdAt: number
  updatedAt: number
}

export interface PageData<T> {
  page: number
  pageSize: number
  total: number
  items: T[]
}

export async function createExecutor(projectId: string, data: {
  name: string; executorType: string; description?: string;
  config?: Record<string, unknown>; version?: string;
}): Promise<Executor> {
  return requestJson<Executor>(`/api/projects/${projectId}/executors`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(data),
  })
}

export async function listExecutors(projectId: string, page = 1, pageSize = 20): Promise<PageData<Executor>> {
  return requestJson<PageData<Executor>>(`/api/projects/${projectId}/executors?page=${page}&pageSize=${pageSize}`, {
    method: 'GET',
    headers: authHeader(),
  })
}

export async function getExecutor(projectId: string, executorId: string): Promise<Executor> {
  return requestJson<Executor>(`/api/projects/${projectId}/executors/${executorId}`, {
    method: 'GET',
    headers: authHeader(),
  })
}

export async function updateExecutor(projectId: string, executorId: string, data: Partial<Executor>): Promise<Executor> {
  return requestJson<Executor>(`/api/projects/${projectId}/executors/${executorId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(data),
  })
}

export async function deleteExecutor(projectId: string, executorId: string): Promise<void> {
  await requestJson<void>(`/api/projects/${projectId}/executors/${executorId}`, {
    method: 'DELETE',
    headers: authHeader(),
  })
}
