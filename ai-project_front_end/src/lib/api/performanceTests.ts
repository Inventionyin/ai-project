import { requestJson, authHeader } from './client'

export interface PerformanceTest {
  id: string
  projectId: string
  name: string
  description: string
  testType: string
  targetUrl: string
  config: Record<string, unknown>
  scriptContent: string
  status: string
  tags: string[]
  createdBy: string | null
  createdAt: number
  updatedAt: number
}

export interface PerformanceTestRun {
  id: string
  testId: string
  status: string
  startedAt: string | null
  finishedAt: string | null
  durationMs: number | null
  metrics: Record<string, unknown>
  thresholds: { passed: boolean; details: Array<{ metric: string; rules: string[]; value: number; passed: boolean }> }
  reportPath: string | null
  errorMessage: string | null
  createdAt: number
  updatedAt: number
}

export interface TrendDataPoint {
  runId: string
  createdAt: number
  reqPerSec: number | null
  avgLatency: number | null
  p95: number | null
  p99: number | null
  errorRate: number | null
  durationMs: number | null
}

export interface PageData<T> {
  page: number
  pageSize: number
  total: number
  items: T[]
}

export async function createPerformanceTest(projectId: string, data: {
  name: string; testType?: string; description?: string;
  targetUrl?: string; config?: Record<string, unknown>;
  scriptContent?: string; tags?: string[];
}): Promise<PerformanceTest> {
  return requestJson<PerformanceTest>(`/api/projects/${projectId}/performance-tests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(data),
  })
}

export async function listPerformanceTests(projectId: string, page = 1, pageSize = 20): Promise<PageData<PerformanceTest>> {
  return requestJson<PageData<PerformanceTest>>(`/api/projects/${projectId}/performance-tests?page=${page}&pageSize=${pageSize}`, {
    method: 'GET',
    headers: authHeader(),
  })
}

export async function getPerformanceTest(projectId: string, testId: string): Promise<PerformanceTest> {
  return requestJson<PerformanceTest>(`/api/projects/${projectId}/performance-tests/${testId}`, {
    method: 'GET',
    headers: authHeader(),
  })
}

export async function updatePerformanceTest(projectId: string, testId: string, data: Partial<PerformanceTest>): Promise<PerformanceTest> {
  return requestJson<PerformanceTest>(`/api/projects/${projectId}/performance-tests/${testId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(data),
  })
}

export async function deletePerformanceTest(projectId: string, testId: string): Promise<void> {
  await requestJson<void>(`/api/projects/${projectId}/performance-tests/${testId}`, {
    method: 'DELETE',
    headers: authHeader(),
  })
}

export async function runPerformanceTest(projectId: string, testId: string): Promise<PerformanceTestRun> {
  return requestJson<PerformanceTestRun>(`/api/projects/${projectId}/performance-tests/${testId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({}),
  })
}

export async function listPerformanceTestRuns(projectId: string, testId: string, page = 1, pageSize = 20): Promise<PageData<PerformanceTestRun>> {
  return requestJson<PageData<PerformanceTestRun>>(`/api/projects/${projectId}/performance-tests/${testId}/runs?page=${page}&pageSize=${pageSize}`, {
    method: 'GET',
    headers: authHeader(),
  })
}

export async function getPerformanceTestTrend(projectId: string, testId: string): Promise<TrendDataPoint[]> {
  return requestJson<TrendDataPoint[]>(`/api/projects/${projectId}/performance-tests/${testId}/trend`, {
    method: 'GET',
    headers: authHeader(),
  })
}

export async function generateK6Script(projectId: string, data: {
  testType?: string; targetUrl: string; config?: Record<string, unknown>;
}): Promise<{ script: string }> {
  return requestJson<{ script: string }>(`/api/projects/${projectId}/performance-tests/generate-k6`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(data),
  })
}
