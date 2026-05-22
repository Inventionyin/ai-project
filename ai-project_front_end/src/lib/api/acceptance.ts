import { authHeader, requestJson } from '@/lib/api/client'

export type AcceptanceStatus = 'ready' | 'warn' | 'blocked'

export type AcceptanceCheck = {
  key: string
  name: string
  status: AcceptanceStatus
  detail: string
  recommendation: string
}

export type AcceptanceExternalSystem = {
  key: string
  name: string
  status: AcceptanceStatus
  detail: string
  configured: boolean
  missingFields: string[]
}

export type AcceptanceMetric = {
  key: string
  label: string
  value: string
}

export type AcceptanceSummary = {
  overallStatus: AcceptanceStatus
  score: number | null
  generatedAt: number | null
  checks: AcceptanceCheck[]
  externalSystems: AcceptanceExternalSystem[]
  metrics: AcceptanceMetric[]
  nextActions: string[]
}

export type AcceptanceReport = {
  markdown: string
}

function normalizeStatus(input: unknown): AcceptanceStatus {
  const raw = String(input ?? '').trim().toLowerCase()
  if (raw === 'blocked' || raw === 'error' || raw === 'critical' || raw === 'fail' || raw === 'failed') return 'blocked'
  if (raw === 'warn' || raw === 'warning' || raw === 'degraded' || raw === 'risk') return 'warn'
  return 'ready'
}

function normalizeTimestamp(input: unknown): number | null {
  if (typeof input === 'number' && Number.isFinite(input) && input > 0) {
    return input > 10_000_000_000 ? Math.floor(input / 1000) : Math.floor(input)
  }
  if (typeof input === 'string' && input.trim()) {
    const asNum = Number(input)
    if (Number.isFinite(asNum) && asNum > 0) return asNum > 10_000_000_000 ? Math.floor(asNum / 1000) : Math.floor(asNum)
    const parsed = Date.parse(input)
    if (Number.isFinite(parsed) && parsed > 0) return Math.floor(parsed / 1000)
  }
  return null
}

function normalizeText(input: unknown, fallback = '-'): string {
  const text = String(input ?? '').trim()
  return text || fallback
}

function normalizeScore(input: unknown): number | null {
  const score = Number(input)
  if (!Number.isFinite(score)) return null
  return Math.max(0, Math.min(100, score))
}

function normalizeCheck(input: unknown, index: number): AcceptanceCheck {
  const row = (input ?? {}) as Record<string, unknown>
  const key = normalizeText(row.key ?? row.id, `check_${index + 1}`)
  return {
    key,
    name: normalizeText(row.name ?? row.label, key),
    status: normalizeStatus(row.status ?? row.level),
    detail: normalizeText(row.detail ?? row.message ?? row.description),
    recommendation: normalizeText(row.recommendation, ''),
  }
}

function normalizeExternalSystem(input: unknown, index: number): AcceptanceExternalSystem {
  const row = (input ?? {}) as Record<string, unknown>
  const key = normalizeText(row.key ?? row.id ?? row.provider, `system_${index + 1}`)
  const missingFields = Array.isArray(row.missingFields)
    ? row.missingFields.map((item) => normalizeText(item, '')).filter(Boolean)
    : []
  return {
    key,
    name: normalizeText(row.name ?? row.label ?? row.provider, key),
    status: normalizeStatus(row.status ?? row.level),
    detail: normalizeText(row.detail ?? row.message ?? row.description),
    configured: Boolean(row.configured),
    missingFields,
  }
}

function normalizeMetrics(input: unknown): AcceptanceMetric[] {
  if (Array.isArray(input)) {
    return input.map((item, index) => {
      const row = (item ?? {}) as Record<string, unknown>
      const key = normalizeText(row.key ?? row.id, `metric_${index + 1}`)
      return {
        key,
        label: normalizeText(row.label ?? row.name, key),
        value: normalizeText(row.value ?? row.metric),
      }
    })
  }
  if (typeof input === 'object' && input !== null) {
    return Object.entries(input as Record<string, unknown>).map(([key, value]) => ({
      key,
      label: key,
      value: normalizeText(value),
    }))
  }
  return []
}

function normalizeNextActions(input: unknown): string[] {
  if (!Array.isArray(input)) return []
  return input.map((item) => normalizeText(item, '')).filter(Boolean)
}

export async function getAcceptanceSummary(projectId: string): Promise<AcceptanceSummary> {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('projectId 不能为空')
  const data = await requestJson<unknown>(
    `/api/projects/${encodeURIComponent(pid)}/acceptance/summary`,
    { method: 'GET', headers: authHeader() }
  )
  const raw = (data ?? {}) as Record<string, unknown>
  return {
    overallStatus: normalizeStatus(raw.overallStatus ?? raw.status),
    score: normalizeScore(raw.score),
    generatedAt: normalizeTimestamp(raw.generatedAt ?? raw.updatedAt ?? raw.timestamp),
    checks: (Array.isArray(raw.checks) ? raw.checks : []).map((item, index) => normalizeCheck(item, index)),
    externalSystems: (Array.isArray(raw.externalSystems) ? raw.externalSystems : []).map((item, index) =>
      normalizeExternalSystem(item, index)
    ),
    metrics: normalizeMetrics(raw.metrics),
    nextActions: normalizeNextActions(raw.nextActions),
  }
}

export async function getAcceptanceReport(projectId: string): Promise<AcceptanceReport> {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('projectId 不能为空')
  const data = await requestJson<unknown>(
    `/api/projects/${encodeURIComponent(pid)}/acceptance/report`,
    { method: 'GET', headers: authHeader() }
  )
  const raw = (data ?? {}) as Record<string, unknown>
  return {
    markdown: normalizeText(raw.markdown ?? raw.content, ''),
  }
}
