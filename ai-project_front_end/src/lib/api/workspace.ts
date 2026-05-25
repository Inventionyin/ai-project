import { authHeader, requestJson } from '@/lib/api/client'

export type WorkspaceSummary = {
  assets: {
    requirementDocs: number
    testcases: number
    formalCases: number
    testPoints: number
    apiCollections: number
    apiRequests: number
    suites: number
  }
  automation: {
    runs: number
    executedCaseRuns: number
    passRate: number
    latestRunAt: number | null
  }
  risks: {
    defects: number
    p0Open: number
    riskHints: number
  }
  capabilities: {
    role: 'admin' | 'owner' | 'editor' | 'viewer'
    assets: boolean
    ai: boolean
    automation: boolean
    settings: boolean
    ops: boolean
  }
}

export async function fetchWorkspaceSummary(projectId: string) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('projectId 不能为空')
  return requestJson<WorkspaceSummary>(`/api/projects/${encodeURIComponent(pid)}/workspace/summary`, {
    method: 'GET',
    headers: authHeader()
  })
}
