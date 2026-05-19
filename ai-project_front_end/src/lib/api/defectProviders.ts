import { authHeader, requestJson } from './client'

export interface DefectProviderConfigDetail {
  id: string
  projectId: string
  provider: string
  name: string
  baseUrl: string
  enabled: boolean
  syncStatus: string
  lastSyncAt: number | null
  lastError: string | null
}

export interface DefectProviderCreatePayload {
  provider: string
  name: string
  baseUrl: string
  apiToken?: string
  username?: string
  projectKey?: string
}

export async function listDefectProviders(projectId: string): Promise<DefectProviderConfigDetail[]> {
  return requestJson<DefectProviderConfigDetail[]>(
    `/api/v1/projects/${projectId}/defect-providers?projectId=${projectId}`,
    { headers: { ...authHeader() } }
  )
}

export async function createDefectProvider(
  projectId: string,
  payload: DefectProviderCreatePayload
): Promise<DefectProviderConfigDetail> {
  return requestJson<DefectProviderConfigDetail>(
    `/api/v1/projects/${projectId}/defect-providers?projectId=${projectId}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: JSON.stringify(payload)
    }
  )
}

export async function deleteDefectProvider(projectId: string, configId: string): Promise<void> {
  await requestJson<unknown>(
    `/api/v1/projects/${projectId}/defect-providers/${configId}?projectId=${projectId}`,
    { method: 'DELETE', headers: { ...authHeader() } }
  )
}
