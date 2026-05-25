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
  executeRequest?: boolean
  timeoutSeconds?: number
}

export type IntegrationIssueItem = {
  id: string
  provider: IntegrationIssueProvider
  runId: string
  caseRunId?: string | null
  issueKey?: string | null
  url?: string | null
  createdAt?: number | null
}

export type ListIntegrationIssuesParams = {
  runId?: string
  caseRunId?: string
  provider?: IntegrationIssueProvider
}

function normalizeIssue(item: unknown): IntegrationIssueItem {
  const raw = (item && typeof item === 'object' ? item : {}) as Record<string, unknown>
  const provider = String(raw.provider || 'GENERIC').toUpperCase()
  return {
    id: String(raw.id || ''),
    provider: provider === 'JIRA' || provider === 'ZENTAO' ? provider : 'GENERIC',
    runId: String(raw.runId || raw.run_id || ''),
    caseRunId: raw.caseRunId == null ? null : String(raw.caseRunId || ''),
    issueKey: raw.issueKey == null ? null : String(raw.issueKey || ''),
    url: raw.url == null ? null : String(raw.url || ''),
    createdAt: raw.createdAt == null ? null : Number(raw.createdAt || 0)
  }
}

export async function createIntegrationIssue(projectId: string, payload: CreateIntegrationIssuePayload) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  const created = await requestJson<unknown>(`/api/projects/${encodeURIComponent(pid)}/integrations/issues`, {
    method: 'POST',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  return normalizeIssue(created)
}

export async function listIntegrationIssues(projectId: string, params: ListIntegrationIssuesParams = {}) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  const query = new URLSearchParams()
  const runId = String(params.runId || '').trim()
  const caseRunId = String(params.caseRunId || '').trim()
  const provider = String(params.provider || '').trim()
  if (runId) query.set('runId', runId)
  if (caseRunId) query.set('caseRunId', caseRunId)
  if (provider) query.set('provider', provider)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  const items = await requestJson<unknown>(`/api/projects/${encodeURIComponent(pid)}/integrations/issues${suffix}`, {
    method: 'GET',
    headers: authHeader()
  })
  return Array.isArray(items) ? items.map(normalizeIssue).filter((item) => item.id) : []
}
