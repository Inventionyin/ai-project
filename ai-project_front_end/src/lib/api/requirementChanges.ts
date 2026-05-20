import { authHeader, requestJson } from '@/lib/api/client'

export type RequirementChangeItem = {
  id: string
  changeType: string
  title: string
  description?: string | null
  impactLevel: string
  sourcePath?: string | null
}

export type RequirementChangeSetDetail = {
  id: string
  projectId: string
  docId: string
  baselineVersionId: string
  targetVersionId: string
  summary?: string | null
  status: string
  items: RequirementChangeItem[]
  createdBy?: string | null
  createdAt?: number | null
  updatedAt?: number | null
}

export type RequirementRegressionCase = {
  id: string
  testcaseId: string
  testcaseTitle?: string | null
  priority: string
  reason?: string | null
  sourcePaths: string[]
}

export type RequirementRegressionSetDetail = {
  id: string
  projectId: string
  changeSetId: string
  summary?: string | null
  status: string
  cases: RequirementRegressionCase[]
  createdBy?: string | null
  createdAt?: number | null
  updatedAt?: number | null
}

export type RequirementChangeSetCreatePayload = {
  baselineVersionId: string
  targetVersionId: string
}

function requireId(value: string, message: string) {
  const normalized = String(value || '').trim()
  if (!normalized) throw new Error(message)
  return normalized
}

function normalizeChangeSetList(data: unknown): RequirementChangeSetDetail[] {
  if (Array.isArray(data)) return data as RequirementChangeSetDetail[]
  const payload = (data || {}) as { items?: RequirementChangeSetDetail[] }
  return Array.isArray(payload.items) ? payload.items : []
}

export async function fetchRequirementChangeSets(projectId: string, docId: string) {
  const pid = requireId(projectId, '项目 ID 不能为空')
  const did = requireId(docId, '文档 ID 不能为空')
  const data = await requestJson<RequirementChangeSetDetail[] | { items?: RequirementChangeSetDetail[] }>(
    `/projects/${encodeURIComponent(pid)}/requirements/docs/${encodeURIComponent(did)}/change-sets`,
    { method: 'GET', headers: authHeader() }
  )
  return normalizeChangeSetList(data)
}

export async function createRequirementChangeSet(projectId: string, docId: string, payload: RequirementChangeSetCreatePayload) {
  const pid = requireId(projectId, '项目 ID 不能为空')
  const did = requireId(docId, '文档 ID 不能为空')
  const baselineVersionId = requireId(payload.baselineVersionId, '基线版本不能为空')
  const targetVersionId = requireId(payload.targetVersionId, '目标版本不能为空')
  if (baselineVersionId === targetVersionId) throw new Error('基线版本和目标版本不能相同')
  return requestJson<RequirementChangeSetDetail>(`/projects/${encodeURIComponent(pid)}/requirements/docs/${encodeURIComponent(did)}/change-sets`, {
    method: 'POST',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ baselineVersionId, targetVersionId })
  })
}

export async function fetchRequirementChangeSetDetail(projectId: string, changeSetId: string) {
  const pid = requireId(projectId, '项目 ID 不能为空')
  const cid = requireId(changeSetId, '变更分析 ID 不能为空')
  return requestJson<RequirementChangeSetDetail>(
    `/projects/${encodeURIComponent(pid)}/requirements/change-sets/${encodeURIComponent(cid)}`,
    { method: 'GET', headers: authHeader() }
  )
}

export async function generateRequirementRegressionSet(projectId: string, changeSetId: string) {
  const pid = requireId(projectId, '项目 ID 不能为空')
  const cid = requireId(changeSetId, '变更分析 ID 不能为空')
  return requestJson<RequirementRegressionSetDetail>(
    `/projects/${encodeURIComponent(pid)}/requirements/change-sets/${encodeURIComponent(cid)}/regression-set`,
    { method: 'POST', headers: authHeader() }
  )
}

export async function fetchRequirementRegressionSetByChangeSet(projectId: string, changeSetId: string) {
  const pid = requireId(projectId, '项目 ID 不能为空')
  const cid = requireId(changeSetId, '变更分析 ID 不能为空')
  return requestJson<RequirementRegressionSetDetail | null>(
    `/projects/${encodeURIComponent(pid)}/requirements/change-sets/${encodeURIComponent(cid)}/regression-set`,
    { method: 'GET', headers: authHeader() }
  )
}

export async function fetchRequirementRegressionSet(projectId: string, regressionSetId: string) {
  const pid = requireId(projectId, '项目 ID 不能为空')
  const rid = requireId(regressionSetId, '回归集 ID 不能为空')
  return requestJson<RequirementRegressionSetDetail>(
    `/projects/${encodeURIComponent(pid)}/requirements/regression-sets/${encodeURIComponent(rid)}`,
    { method: 'GET', headers: authHeader() }
  )
}
