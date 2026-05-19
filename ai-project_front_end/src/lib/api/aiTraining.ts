import { authHeader, requestJson } from './client'

export interface AiTrainingJobListItem {
  id: string
  projectId: string
  name: string
  description: string
  trainingType: string
  baseModel: string
  status: string
  progress: number
  metrics: Record<string, unknown>
  modelRef: string | null
  errorMessage: string | null
  createdBy: string | null
  createdAt: number | null
  updatedAt: number | null
}

export interface AiTrainingJobDetail extends AiTrainingJobListItem {
  datasetConfig: Record<string, unknown>
  hyperparams: Record<string, unknown>
}

export interface AiTrainingJobProgress {
  status: string
  progress: number
  metrics: Record<string, unknown>
  modelRef: string | null
  errorMessage: string | null
}

export interface AiTrainingDatasetListItem {
  id: string
  projectId: string
  name: string
  sourceType: string
  recordCount: number
  sampleJson: Record<string, unknown>
  configJson: Record<string, unknown>
  createdAt: number | null
  updatedAt: number | null
}

export interface PageData<T> {
  page: number
  pageSize: number
  total: number
  items: T[]
}

export interface AiTrainingJobCreatePayload {
  name: string
  description?: string
  trainingType?: string
  baseModel?: string
  datasetConfig?: Record<string, unknown>
  hyperparams?: Record<string, unknown>
}

export interface AiTrainingJobUpdatePayload {
  name?: string
  description?: string
  trainingType?: string
  baseModel?: string
  datasetConfig?: Record<string, unknown>
  hyperparams?: Record<string, unknown>
}

export interface AiTrainingDatasetCreatePayload {
  name: string
  sourceType?: string
  config?: Record<string, unknown>
}

const BASE = '/api/v1/projects'

// ---------- Training Jobs ----------

export async function listTrainingJobs(
  projectId: string,
  params?: { page?: number; pageSize?: number; status?: string }
): Promise<PageData<AiTrainingJobListItem>> {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.pageSize) qs.set('pageSize', String(params.pageSize))
  if (params?.status) qs.set('status', params.status)
  const q = qs.toString()
  return requestJson<PageData<AiTrainingJobListItem>>(
    `${BASE}/${projectId}/ai-training/jobs?${q}`,
    { headers: { ...authHeader() } }
  )
}

export async function getTrainingJob(
  projectId: string,
  jobId: string
): Promise<AiTrainingJobDetail> {
  return requestJson<AiTrainingJobDetail>(
    `${BASE}/${projectId}/ai-training/jobs/${jobId}`,
    { headers: { ...authHeader() } }
  )
}

export async function createTrainingJob(
  projectId: string,
  payload: AiTrainingJobCreatePayload
): Promise<AiTrainingJobDetail> {
  return requestJson<AiTrainingJobDetail>(
    `${BASE}/${projectId}/ai-training/jobs`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: JSON.stringify(payload)
    }
  )
}

export async function updateTrainingJob(
  projectId: string,
  jobId: string,
  payload: AiTrainingJobUpdatePayload
): Promise<AiTrainingJobDetail> {
  return requestJson<AiTrainingJobDetail>(
    `${BASE}/${projectId}/ai-training/jobs/${jobId}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: JSON.stringify(payload)
    }
  )
}

export async function deleteTrainingJob(
  projectId: string,
  jobId: string
): Promise<void> {
  await requestJson<unknown>(
    `${BASE}/${projectId}/ai-training/jobs/${jobId}`,
    { method: 'DELETE', headers: { ...authHeader() } }
  )
}

export async function prepareDataset(
  projectId: string,
  jobId: string
): Promise<AiTrainingJobDetail> {
  return requestJson<AiTrainingJobDetail>(
    `${BASE}/${projectId}/ai-training/jobs/${jobId}/prepare`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeader() }
    }
  )
}

export async function startTraining(
  projectId: string,
  jobId: string
): Promise<AiTrainingJobDetail> {
  return requestJson<AiTrainingJobDetail>(
    `${BASE}/${projectId}/ai-training/jobs/${jobId}/start`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeader() }
    }
  )
}

export async function getTrainingProgress(
  projectId: string,
  jobId: string
): Promise<AiTrainingJobProgress> {
  return requestJson<AiTrainingJobProgress>(
    `${BASE}/${projectId}/ai-training/jobs/${jobId}/progress`,
    { headers: { ...authHeader() } }
  )
}

// ---------- Datasets ----------

export async function listDatasets(
  projectId: string,
  params?: { page?: number; pageSize?: number }
): Promise<PageData<AiTrainingDatasetListItem>> {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.pageSize) qs.set('pageSize', String(params.pageSize))
  const q = qs.toString()
  return requestJson<PageData<AiTrainingDatasetListItem>>(
    `${BASE}/${projectId}/ai-training/datasets?${q}`,
    { headers: { ...authHeader() } }
  )
}

export async function createDataset(
  projectId: string,
  payload: AiTrainingDatasetCreatePayload
): Promise<AiTrainingDatasetListItem> {
  return requestJson<AiTrainingDatasetListItem>(
    `${BASE}/${projectId}/ai-training/datasets`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: JSON.stringify(payload)
    }
  )
}
