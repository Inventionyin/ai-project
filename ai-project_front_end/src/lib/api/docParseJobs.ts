import { requestJson, authHeader } from './client'

export interface DocParseJob {
  id: string
  projectId: string
  docId: string
  docVersionId: string
  status: string
  attempts: number
  maxRetries: number
  errorMessage: string | null
  result: Record<string, unknown> | null
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

export async function createDocParseJob(projectId: string, docId: string, docVersionId: string): Promise<DocParseJob> {
  return requestJson<DocParseJob>(`/api/projects/${encodeURIComponent(projectId)}/doc-parse-jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ docId, docVersionId }),
  })
}

export async function listDocParseJobs(projectId: string, page = 1, pageSize = 20, status?: string): Promise<PageData<DocParseJob>> {
  const params = new URLSearchParams({ page: String(page), pageSize: String(pageSize) })
  if (status) params.set('status', status)
  return requestJson<PageData<DocParseJob>>(`/api/projects/${encodeURIComponent(projectId)}/doc-parse-jobs?${params}`, {
    method: 'GET',
    headers: authHeader(),
  })
}

export async function getDocParseJob(projectId: string, jobId: string): Promise<DocParseJob> {
  return requestJson<DocParseJob>(`/api/projects/${encodeURIComponent(projectId)}/doc-parse-jobs/${encodeURIComponent(jobId)}`, {
    method: 'GET',
    headers: authHeader(),
  })
}

export async function retryDocParseJob(projectId: string, jobId: string): Promise<DocParseJob> {
  return requestJson<DocParseJob>(`/api/projects/${encodeURIComponent(projectId)}/doc-parse-jobs/${encodeURIComponent(jobId)}/retry`, {
    method: 'POST',
    headers: authHeader(),
  })
}
