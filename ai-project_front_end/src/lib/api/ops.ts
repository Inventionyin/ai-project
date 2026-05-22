import { authHeader, requestJson } from '@/lib/api/client'

export type OpsHealthLevel = 'blocked' | 'warn' | 'ready'

export type OpsHealthCheck = {
  key: string
  name: string
  status: OpsHealthLevel
  metric: string
  detail: string
  recommendation: string
}

export type OpsHealthSummary = {
  overallStatus: OpsHealthLevel
  generatedAt: number | null
  checks: OpsHealthCheck[]
}

function normalizeStatus(input: unknown): OpsHealthLevel {
  const raw = String(input ?? '').trim().toLowerCase()
  if (raw === 'blocked' || raw === 'error' || raw === 'critical' || raw === 'down') return 'blocked'
  if (raw === 'warn' || raw === 'warning' || raw === 'degraded') return 'warn'
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

function normalizeCheck(input: unknown, idx: number): OpsHealthCheck {
  const row = (input ?? {}) as Record<string, unknown>
  const key = String(row.key ?? row.id ?? `check_${idx + 1}`).trim() || `check_${idx + 1}`
  const name = String(row.name ?? row.label ?? key).trim() || key
  const metricRaw = row.metric ?? row.value ?? '-'
  const metric =
    typeof metricRaw === 'object' && metricRaw !== null
      ? JSON.stringify(metricRaw)
      : String(metricRaw).trim() || '-'
  const detail = String(row.detail ?? row.message ?? row.description ?? '-').trim() || '-'
  const recommendation = String(row.recommendation ?? row.action ?? row.suggestion ?? '-').trim() || '-'
  return {
    key,
    name,
    status: normalizeStatus(row.status ?? row.level),
    metric,
    detail,
    recommendation,
  }
}

export async function getOpsHealthSummary(): Promise<OpsHealthSummary> {
  const payload = await requestJson<unknown>('/api/ops/health/summary', {
    method: 'GET',
    headers: authHeader(),
  })

  const raw = (payload ?? {}) as Record<string, unknown>
  const listRaw = Array.isArray(raw.checks) ? raw.checks : Array.isArray((raw.items as unknown[] | undefined)) ? (raw.items as unknown[]) : []

  return {
    overallStatus: normalizeStatus(raw.overallStatus ?? raw.status),
    generatedAt: normalizeTimestamp(raw.generatedAt ?? raw.timestamp ?? raw.updatedAt),
    checks: listRaw.map((item, index) => normalizeCheck(item, index)),
  }
}
