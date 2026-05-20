import { authHeader, requestJson } from '@/lib/api/client'

export type IntegrationIssueProvider = 'JIRA' | 'ZENTAO' | 'GENERIC'

export type CreateIntegrationIssuePayload = {
  provider: IntegrationIssueProvider
  runId: string
  title: string
  description: string
  url?: string
  projectKey?: string
  issueType?: string
  config?: Record<string, unknown>
  credentials?: Record<string, unknown>
}

export type IntegrationIssueItem = {
  id: string
  projectId: string
  provider: IntegrationIssueProvider
  runId?: string | null
  title?: string | null
  description?: string | null
  url?: string | null
  projectKey?: string | null
  issueType?: string | null
  config?: Record<string, unknown> | null
  credentials?: Record<string, unknown> | null
  createdAt?: number | null
  updatedAt?: number | null
}

export async function createIntegrationIssue(projectId: string, payload: CreateIntegrationIssuePayload) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  return requestJson<IntegrationIssueItem>(`/api/projects/${encodeURIComponent(pid)}/integrations/issues`, {
    method: 'POST',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}
