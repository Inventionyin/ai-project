import { authHeader, requestJson } from './client'

export interface CiTokenPolicy {
  allowedRunnerTypes: string[]
  allowedTestCaseIds: string[]
  maxTestCaseCount: number | null
}

export interface CiTokenStatus {
  projectId: string
  enabled: boolean
  hint: string | null
  rotatedAt: number | null
  lastUsedAt: number | null
  rotatedBy: string | null
  policy: CiTokenPolicy
}

export interface CiTokenRotateResult extends CiTokenStatus {
  token: string
}

export function getCiTokenStatus(projectId: string): Promise<CiTokenStatus> {
  return requestJson<CiTokenStatus>(`/api/runs/ci-token/status?projectId=${encodeURIComponent(projectId)}`, {
    method: 'GET',
    headers: authHeader(),
  })
}

export function rotateCiToken(projectId: string, policy?: CiTokenPolicy): Promise<CiTokenRotateResult> {
  return requestJson<CiTokenRotateResult>('/api/runs/ci-token/rotate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ projectId, ...(policy ? { policy } : {}) }),
  })
}

export function updateCiTokenPolicy(projectId: string, policy: CiTokenPolicy): Promise<CiTokenStatus> {
  return requestJson<CiTokenStatus>('/api/runs/ci-token/policy', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ projectId, policy }),
  })
}

export function revokeCiToken(projectId: string): Promise<CiTokenStatus> {
  return requestJson<CiTokenStatus>('/api/runs/ci-token', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ projectId }),
  })
}
