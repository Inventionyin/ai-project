import { authHeader, requestJson } from '@/lib/api/client'

export type NotificationRule = {
  id: string
  projectId: string
  channel: string
  target: string
  enabled: boolean
  rule: Record<string, unknown>
  createdAt?: number | null
  updatedAt?: number | null
}

export type PromptTemplateItem = {
  id: string
  projectId: string
  scene: string
  name: string
  version: string
  content: string
  variablesJson?: Record<string, unknown>
  isActive: boolean
  createdBy?: string | null
  createdAt?: number | null
  updatedAt?: number | null
}

export type NotificationUpsertPayload = {
  channel: string
  target: string
  enabled: boolean
  rule: Record<string, unknown>
}

export type NotificationDelivery = {
  id: string
  status: string
  notificationId: string
  runId: string
  attempts: number
  statusCode?: number | null
  durationMs?: number | null
  error?: string | null
  lastStatusCode?: number | null
  lastDurationMs?: number | null
  lastError?: string | null
  createdAt?: number | string | null
}

export type NotificationDeliveryListQuery = {
  status?: string
  runId?: string
  page?: number
  pageSize?: number
}

export type NotificationDeliveryListResult = {
  items: NotificationDelivery[]
  total: number
  page: number
  pageSize: number
}

export type PromptTemplateGovernanceItem = {
  scene: string
  name: string
  activeVersion: string
  latestVersion: string
  versionCount: number
}

export type StrategyCenterDeliveryStat = {
  sent: number
  failed: number
  queued: number
  lastDeliveryAt: number | string | null
  lastStatus: string | null
}

export type StrategyCenterFilterReasonStat = {
  scopeReason: number
  eventFiltered: number
  unsupportedProvider: number
  templateNotFound: number
}

export type StrategyCenterSimulationScopeReasonItem = {
  reason: string
  count: number
}

export type StrategyCenterSimulationStats = {
  sampleCount: number
  matchedCount: number
  scopeReasonTop: StrategyCenterSimulationScopeReasonItem[]
}

export type StrategyCenterRuleItem = {
  notificationId: string
  channel: string
  target: string
  enabled: boolean
  events: string[]
  strategySummary: string
  deliveryStats: StrategyCenterDeliveryStat
  filterReasonStats: StrategyCenterFilterReasonStat
  simulationStats?: StrategyCenterSimulationStats
  templateStrategySummary: Record<string, unknown>
  rolloutScopeSummary: Record<string, unknown>
  autoRollbackSummary: Record<string, unknown>
}

export type StrategySimulationRunContext = {
  envId?: string
  triggerType?: string
  metaTags?: string[]
  layerValue?: string
  weekday?: number
  hour?: number
  timezoneOffsetMinutes?: number
  seed?: number | string
}

export type StrategySimulationRequest = {
  notificationId: string
  runContext?: StrategySimulationRunContext
}

export type StrategySimulationConflictCandidate = {
  id: string
  priority: number | null
  weight: number | null
  rawText?: string
}

export type StrategySimulationScopeDecision = {
  selectedWindowId: string
  matchedWindowCount: number | null
  reason: string
}

export type StrategySimulationResult = {
  matched: boolean
  scopeReason: string
  scopeDecision: StrategySimulationScopeDecision
  selectedWindowId: string
  matchedWindowCount: number | null
  reason: string
  resolvedBatchPercent: number | null
  resolvedPriority: number | null
  resolvedLayer: string
  resolvedTimeWindow: string
  explanations: string[]
  conflictCandidates: StrategySimulationConflictCandidate[]
  runContext?: string
}

export type StrategySimulationBatchRequest = {
  notificationId: string
  runContexts: StrategySimulationRunContext[]
}

export type IntegrationDiagnosticsSummaryStatus = 'BLOCKED' | 'WARN' | 'READY'

export type IntegrationDiagnosticsSummary = {
  status: IntegrationDiagnosticsSummaryStatus
  total: number
  blocking: number
  warnings: number
  ready: number
  failedDeliveries: number
}

export type IntegrationDiagnosticsCheckLevel = 'BLOCKER' | 'WARNING' | 'READY'

export type IntegrationDiagnosticsCheck = {
  id: string
  level: IntegrationDiagnosticsCheckLevel
  scope: string
  title: string
  detail: string
  recommendation: string
  notificationId?: string | null
}

export type IntegrationDiagnosticsRecentFailure = {
  id: string
  notificationId: string
  channel: string
  target: string
  provider: string
  status: string
  attempts: number
  lastStatusCode?: number | null
  lastError?: string | null
  updatedAt?: number | string | null
}

export type IntegrationDiagnosticsProviderReadiness = {
  provider: string
  ready: boolean
  reason: string
  notificationCount: number
}

export type IntegrationDiagnostics = {
  summary: IntegrationDiagnosticsSummary
  checks: IntegrationDiagnosticsCheck[]
  recentFailures: IntegrationDiagnosticsRecentFailure[]
  providerReadiness: IntegrationDiagnosticsProviderReadiness[]
}

function normalizeList<T>(data: T[] | { items?: T[] }) {
  if (Array.isArray(data)) return data
  return Array.isArray(data?.items) ? data.items : []
}

function normalizeDeliveryList(
  data:
    | NotificationDelivery[]
    | {
        items?: NotificationDelivery[]
        total?: number
        page?: number
        pageSize?: number
      },
  fallback: Required<Pick<NotificationDeliveryListQuery, 'page' | 'pageSize'>>
): NotificationDeliveryListResult {
  if (Array.isArray(data)) {
    const items = data.map((item) => normalizeDeliveryItem(item))
    return {
      items,
      total: items.length,
      page: fallback.page,
      pageSize: fallback.pageSize
    }
  }
  const items = (Array.isArray(data?.items) ? data.items : []).map((item) => normalizeDeliveryItem(item))
  return {
    items,
    total: typeof data?.total === 'number' && Number.isFinite(data.total) ? data.total : items.length,
    page: typeof data?.page === 'number' && Number.isFinite(data.page) ? data.page : fallback.page,
    pageSize: typeof data?.pageSize === 'number' && Number.isFinite(data.pageSize) ? data.pageSize : fallback.pageSize
  }
}

function normalizeDiagnosticsStatus(value: unknown): IntegrationDiagnosticsSummaryStatus {
  const text = String(value ?? '')
    .trim()
    .toUpperCase()
  if (text === 'BLOCKED' || text === 'WARN' || text === 'READY') return text
  return 'READY'
}

function normalizeDiagnosticsCheckLevel(value: unknown): IntegrationDiagnosticsCheckLevel {
  const text = String(value ?? '')
    .trim()
    .toUpperCase()
  if (text === 'BLOCKER' || text === 'WARNING' || text === 'READY') return text
  return 'READY'
}

function normalizeDiagnosticsBool(value: unknown) {
  if (typeof value === 'boolean') return value
  const text = String(value ?? '')
    .trim()
    .toLowerCase()
  if (text === 'true' || text === '1' || text === 'yes') return true
  if (text === 'false' || text === '0' || text === 'no') return false
  return Boolean(value)
}

function normalizeDiagnosticsText(value: unknown) {
  return String(value ?? '').trim()
}

function normalizeDiagnosticsInt(value: unknown) {
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function normalizeDiagnosticsSummary(value: unknown): IntegrationDiagnosticsSummary {
  const summary = value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
  return {
    status: normalizeDiagnosticsStatus(summary.status),
    total: normalizeDiagnosticsInt(summary.total),
    blocking: normalizeDiagnosticsInt(summary.blocking),
    warnings: normalizeDiagnosticsInt(summary.warnings),
    ready: normalizeDiagnosticsInt(summary.ready),
    failedDeliveries: normalizeDiagnosticsInt(summary.failedDeliveries ?? summary.failed_deliveries)
  }
}

function normalizeDiagnosticsChecks(value: unknown): IntegrationDiagnosticsCheck[] {
  if (!Array.isArray(value)) return []
  return value.map((item, index) => {
    const record = item && typeof item === 'object' && !Array.isArray(item) ? (item as Record<string, unknown>) : {}
    const notificationIdText = normalizeDiagnosticsText(record.notificationId ?? record.notification_id)
    return {
      id: normalizeDiagnosticsText(record.id) || `check-${index + 1}`,
      level: normalizeDiagnosticsCheckLevel(record.level),
      scope: normalizeDiagnosticsText(record.scope),
      title: normalizeDiagnosticsText(record.title),
      detail: normalizeDiagnosticsText(record.detail),
      recommendation: normalizeDiagnosticsText(record.recommendation),
      notificationId: notificationIdText || null
    }
  })
}

function normalizeDiagnosticsRecentFailures(value: unknown): IntegrationDiagnosticsRecentFailure[] {
  if (!Array.isArray(value)) return []
  return value.map((item, index) => {
    const record = item && typeof item === 'object' && !Array.isArray(item) ? (item as Record<string, unknown>) : {}
    return {
      id: normalizeDiagnosticsText(record.id) || `failure-${index + 1}`,
      notificationId: normalizeDiagnosticsText(record.notificationId ?? record.notification_id),
      channel: normalizeDiagnosticsText(record.channel),
      target: normalizeDiagnosticsText(record.target),
      provider: normalizeDiagnosticsText(record.provider),
      status: normalizeDiagnosticsText(record.status),
      attempts: normalizeDiagnosticsInt(record.attempts),
      lastStatusCode: normalizeNumericField(record.lastStatusCode as number | string | null | undefined),
      lastError: normalizeErrorField(record.lastError as string | null | undefined),
      updatedAt: (record.updatedAt ?? record.updated_at ?? null) as number | string | null
    }
  })
}

function normalizeDiagnosticsProviderReadiness(value: unknown): IntegrationDiagnosticsProviderReadiness[] {
  if (!Array.isArray(value)) return []
  return value.map((item) => {
    const record = item && typeof item === 'object' && !Array.isArray(item) ? (item as Record<string, unknown>) : {}
    return {
      provider: normalizeDiagnosticsText(record.provider),
      ready: normalizeDiagnosticsBool(record.ready),
      reason: normalizeDiagnosticsText(record.reason),
      notificationCount: normalizeDiagnosticsInt(record.notificationCount ?? record.notification_count)
    }
  })
}

function normalizeDiagnostics(payload: unknown): IntegrationDiagnostics {
  const data = payload && typeof payload === 'object' && !Array.isArray(payload) ? (payload as Record<string, unknown>) : {}
  return {
    summary: normalizeDiagnosticsSummary(data.summary),
    checks: normalizeDiagnosticsChecks(data.checks),
    recentFailures: normalizeDiagnosticsRecentFailures(data.recentFailures ?? data.recent_failures),
    providerReadiness: normalizeDiagnosticsProviderReadiness(data.providerReadiness ?? data.provider_readiness)
  }
}

function normalizeDeliveryStatus(status: string) {
  const normalized = String(status || '').trim().toUpperCase()
  if (normalized === 'PENDING') return 'QUEUED'
  if (normalized === 'SUCCESS') return 'SENT'
  return normalized
}

function normalizeNumericField(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined || value === '') return null
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function normalizeErrorField(value: string | null | undefined): string | null {
  if (value === null || value === undefined) return null
  const text = String(value)
  return text || null
}

function normalizeDeliveryItem(item: NotificationDelivery): NotificationDelivery {
  const normalizedStatus = normalizeDeliveryStatus(item.status)
  const normalizedStatusCode = normalizeNumericField(item.statusCode ?? (item.lastStatusCode as number | string | null | undefined))
  const normalizedDurationMs = normalizeNumericField(item.durationMs ?? (item.lastDurationMs as number | string | null | undefined))
  const normalizedError = normalizeErrorField(item.error ?? item.lastError)
  return {
    ...item,
    status: normalizedStatus,
    statusCode: normalizedStatusCode,
    durationMs: normalizedDurationMs,
    error: normalizedError,
    lastStatusCode: normalizeNumericField(item.lastStatusCode ?? item.statusCode),
    lastDurationMs: normalizeNumericField(item.lastDurationMs ?? item.durationMs),
    lastError: normalizeErrorField(item.lastError ?? item.error)
  }
}

function normalizeGovernanceItem(item: Record<string, unknown>): PromptTemplateGovernanceItem {
  const scene = String(item.scene ?? item.templateScene ?? item.template_scene ?? '').trim()
  const name = String(item.name ?? item.templateName ?? item.template_name ?? '').trim()
  const activeVersion = String(item.activeVersion ?? item.active_version ?? item.currentVersion ?? '').trim()
  const latestVersion = String(item.latestVersion ?? item.latest_version ?? '').trim()
  const rawVersionCount = item.versionCount ?? item.version_count ?? item.totalVersions ?? item.total_versions
  const parsedVersionCount = typeof rawVersionCount === 'number' ? rawVersionCount : Number(rawVersionCount)
  return {
    scene,
    name,
    activeVersion,
    latestVersion,
    versionCount: Number.isFinite(parsedVersionCount) ? parsedVersionCount : 0
  }
}

function normalizeGovernanceList(
  data:
    | PromptTemplateGovernanceItem[]
    | { items?: PromptTemplateGovernanceItem[] }
    | { records?: PromptTemplateGovernanceItem[] }
): PromptTemplateGovernanceItem[] {
  if (Array.isArray(data)) {
    return data.map((item) => normalizeGovernanceItem(item as unknown as Record<string, unknown>))
  }
  const objectData = data as Record<string, unknown>
  const itemsCandidate = Array.isArray(objectData.items)
    ? objectData.items
    : Array.isArray(objectData.records)
      ? objectData.records
      : []
  const items = itemsCandidate as PromptTemplateGovernanceItem[]
  return items.map((item) => normalizeGovernanceItem(item as unknown as Record<string, unknown>))
}

function buildStrategySummary(
  templateSummary: Record<string, unknown>,
  rolloutSummary: Record<string, unknown>,
  autoRollbackSummary: Record<string, unknown>
) {
  const mode = String(templateSummary.mode ?? 'ACTIVE').trim().toUpperCase() || 'ACTIVE'
  const templateName = String(templateSummary.templateName ?? '').trim()
  const templateVersion = String(templateSummary.templateVersion ?? '').trim()
  const canaryVersion = String(templateSummary.templateCanaryVersion ?? '').trim()
  const canaryPercent = Number(templateSummary.templateCanaryPercent)
  const templateParts: string[] = [mode]
  if (templateName) {
    if (templateVersion) templateParts.push(`${templateName}@${templateVersion}`)
    else templateParts.push(templateName)
  }
  if (canaryVersion) {
    const percentText = Number.isFinite(canaryPercent) && canaryPercent > 0 ? `${canaryPercent}%` : ''
    templateParts.push(percentText ? `${canaryVersion}(${percentText})` : canaryVersion)
  }

  const envIdsCount = Number(rolloutSummary.envIdsCount ?? 0)
  const metaTagsCount = Number(rolloutSummary.metaTagsCount ?? 0)
  const batchPercent = Number(rolloutSummary.batchPercent)
  const priority = Number(rolloutSummary.priority)
  const layerKey = String(rolloutSummary.layerKey ?? '').trim()
  const layerValuesCount = Number(rolloutSummary.layerValuesCount ?? 0)
  const timeWindow =
    rolloutSummary.timeWindow && typeof rolloutSummary.timeWindow === 'object'
      ? (rolloutSummary.timeWindow as Record<string, unknown>)
      : {}
  const timeWindowsRaw = rolloutSummary.timeWindows
  const timeWindows = Array.isArray(timeWindowsRaw) ? timeWindowsRaw : []
  const timeWindowsSummary =
    timeWindowsRaw && typeof timeWindowsRaw === 'object' && !Array.isArray(timeWindowsRaw)
      ? (timeWindowsRaw as Record<string, unknown>)
      : {}
  const triggerTypes = Array.isArray(rolloutSummary.triggerTypes)
    ? rolloutSummary.triggerTypes.map((item) => String(item || '').trim()).filter(Boolean)
    : []
  const weekdays = Array.isArray(timeWindow.weekdays)
    ? timeWindow.weekdays
        .map((item) => (typeof item === 'number' ? item : Number(item)))
        .filter((item) => Number.isInteger(item) && item >= 1 && item <= 7)
    : []
  const startHour = Number(timeWindow.startHour)
  const endHour = Number(timeWindow.endHour)
  const timezoneOffsetMinutes = Number(timeWindow.timezoneOffsetMinutes)
  const rolloutParts: string[] = []
  if (Number.isFinite(envIdsCount) && envIdsCount > 0) rolloutParts.push(`env:${envIdsCount}`)
  if (triggerTypes.length > 0) rolloutParts.push(`trigger:${triggerTypes.join('/')}`)
  if (Number.isFinite(metaTagsCount) && metaTagsCount > 0) rolloutParts.push(`tag:${metaTagsCount}`)
  if (Number.isFinite(batchPercent) && batchPercent > 0) rolloutParts.push(`batch:${batchPercent}%`)
  if (Number.isFinite(priority) && priority > 0) rolloutParts.push(`priority:${priority}`)
  if (layerKey && Number.isFinite(layerValuesCount) && layerValuesCount > 0) {
    rolloutParts.push(`layer:${layerKey}(${layerValuesCount})`)
  }
  if (weekdays.length > 0) rolloutParts.push(`wd:${weekdays.join('/')}`)
  if (Number.isFinite(startHour) && Number.isFinite(endHour)) rolloutParts.push(`h:${startHour}-${endHour}`)
  if (Number.isFinite(timezoneOffsetMinutes)) rolloutParts.push(`tz:${timezoneOffsetMinutes}`)
  const summaryTimeWindowsTotal = Number(timeWindowsSummary.total)
  const summaryTimeWindowsEnabled = Number(timeWindowsSummary.enabled)
  const summaryTimeWindowsStrategy = String(timeWindowsSummary.conflictStrategy ?? '').trim()
  const totalTimeWindows =
    timeWindows.length > 0
      ? timeWindows.length
      : Number.isFinite(summaryTimeWindowsTotal) && summaryTimeWindowsTotal > 0
        ? summaryTimeWindowsTotal
        : 0
  if (totalTimeWindows > 0) {
    rolloutParts.push(`tw:${totalTimeWindows}`)
  }
  if (timeWindows.length > 0) {
    const firstWindow = (timeWindows[0] && typeof timeWindows[0] === 'object' ? timeWindows[0] : {}) as Record<string, unknown>
    const firstId = String(firstWindow.id ?? '').trim()
    const firstPriority = Number(firstWindow.priority)
    const firstWeight = Number(firstWindow.weight)
    const firstBatchPercent = Number(firstWindow.batchPercent)
    const firstEnabledRaw = firstWindow.enabled
    const firstEnabled =
      firstEnabledRaw === undefined || firstEnabledRaw === null || String(firstEnabledRaw).trim() === ''
        ? true
        : Boolean(firstEnabledRaw)
    if (firstId) rolloutParts.push(`tw0:${firstId}`)
    rolloutParts.push(`tw0e:${firstEnabled ? '1' : '0'}`)
    if (Number.isFinite(firstPriority) && firstPriority > 0) rolloutParts.push(`tw0p:${firstPriority}`)
    if (Number.isFinite(firstWeight) && firstWeight > 0) rolloutParts.push(`tw0w:${firstWeight}`)
    if (Number.isFinite(firstBatchPercent) && firstBatchPercent > 0) rolloutParts.push(`tw0b:${firstBatchPercent}%`)
  }
  if (Number.isFinite(summaryTimeWindowsEnabled) && summaryTimeWindowsEnabled >= 0) {
    rolloutParts.push(`twe:${summaryTimeWindowsEnabled}`)
  }
  if (summaryTimeWindowsStrategy) {
    rolloutParts.push(`twc:${summaryTimeWindowsStrategy}`)
  }
  const rolloutText = rolloutParts.length > 0 ? rolloutParts.join(', ') : 'off'

  const rollbackEnabled = Boolean(autoRollbackSummary.enabled)
  const rollbackThreshold = Number(autoRollbackSummary.failureThreshold)
  const rollbackWindow = Number(autoRollbackSummary.windowMinutes)
  const rollbackParts: string[] = [rollbackEnabled ? 'on' : 'off']
  if (rollbackEnabled) {
    if (Number.isFinite(rollbackThreshold) && rollbackThreshold > 0) rollbackParts.push(`th=${rollbackThreshold}`)
    if (Number.isFinite(rollbackWindow) && rollbackWindow > 0) rollbackParts.push(`win=${rollbackWindow}m`)
  }
  return `模板:${templateParts.join(' ')} | 灰度:${rolloutText} | 回滚:${rollbackParts.join(' ')}`
}

function normalizeStrategyCenterRow(item: Record<string, unknown>): StrategyCenterRuleItem {
  const toObject = (value: unknown): Record<string, unknown> => {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return {}
    return value as Record<string, unknown>
  }
  const stat = toObject(item.deliveryStats ?? item.deliveryStat ?? item.stats)
  const filterStat = toObject(item.filterReasonStats ?? item.filterReasonStat ?? item.filterStats)
  const simulationStat = toObject(item.simulationStats ?? item.simulation_stats)
  const templateStrategySummary = toObject(item.templateStrategySummary ?? item.template_strategy_summary)
  const rolloutScopeSummary = toObject(item.rolloutScopeSummary ?? item.rollout_scope_summary)
  const autoRollbackSummary = toObject(item.autoRollbackSummary ?? item.auto_rollback_summary)
  const toNumber = (value: unknown) => {
    const parsed = typeof value === 'number' ? value : Number(value)
    return Number.isFinite(parsed) ? parsed : 0
  }
  const toStringValue = (value: unknown) => String(value ?? '').trim()
  const toBooleanValue = (value: unknown) => {
    if (typeof value === 'boolean') return value
    const normalized = String(value ?? '').trim().toLowerCase()
    if (!normalized) return false
    if (normalized === 'true' || normalized === '1' || normalized === 'yes') return true
    if (normalized === 'false' || normalized === '0' || normalized === 'no') return false
    return Boolean(value)
  }
  const simulationScopeReasonTopRaw = Array.isArray(simulationStat.scopeReasonTop)
    ? simulationStat.scopeReasonTop
    : Array.isArray(simulationStat.scope_reason_top)
      ? simulationStat.scope_reason_top
      : []
  const simulationScopeReasonTop = simulationScopeReasonTopRaw
    .map((entry) => {
      const record = toObject(entry)
      const reason = toStringValue(record.reason ?? record.scopeReason ?? record.scope_reason)
      const count = toNumber(record.count)
      if (!reason) return null
      return { reason, count }
    })
    .filter((entry): entry is StrategyCenterSimulationScopeReasonItem => Boolean(entry))
  const sampleCount = toNumber(simulationStat.sampleCount ?? simulationStat.sample_count)
  const matchedCount = toNumber(simulationStat.matchedCount ?? simulationStat.matched_count)
  const simulationStats =
    sampleCount > 0 || matchedCount > 0 || simulationScopeReasonTop.length > 0
      ? {
          sampleCount,
          matchedCount,
          scopeReasonTop: simulationScopeReasonTop
        }
      : undefined
  const events = Array.isArray(item.events) ? item.events.map((event) => toStringValue(event)).filter(Boolean) : []
  const fallbackSummary = buildStrategySummary(templateStrategySummary, rolloutScopeSummary, autoRollbackSummary)
  const strategySummary = toStringValue(item.strategySummary ?? item.strategy_summary ?? item.summary ?? fallbackSummary)
  return {
    notificationId: toStringValue(item.notificationId ?? item.notification_id ?? item.id),
    channel: toStringValue(item.channel),
    target: toStringValue(item.target),
    enabled: toBooleanValue(item.enabled),
    events,
    strategySummary,
    deliveryStats: {
      sent: toNumber(stat.sent ?? stat.delivered ?? stat.successCount ?? stat.success_count),
      failed: toNumber(stat.failed ?? stat.failedCount ?? stat.failed_count),
      queued: toNumber(stat.queued ?? stat.pending ?? stat.queuedCount ?? stat.queued_count),
      lastDeliveryAt: (stat.lastDeliveryAt ?? stat.lastDeliveredAt ?? stat.last_delivered_at ?? stat.lastSentAt ?? null) as
        | number
        | string
        | null,
      lastStatus: toStringValue(stat.lastStatus ?? stat.last_status) || null
    },
    filterReasonStats: {
      scopeReason: toNumber(filterStat.scopeReason ?? filterStat.scope_reason),
      eventFiltered: toNumber(filterStat.eventFiltered ?? filterStat.event_filtered),
      unsupportedProvider: toNumber(filterStat.unsupportedProvider ?? filterStat.unsupported_provider),
      templateNotFound: toNumber(filterStat.templateNotFound ?? filterStat.template_not_found)
    },
    simulationStats,
    templateStrategySummary,
    rolloutScopeSummary,
    autoRollbackSummary
  }
}

function normalizeStrategyCenterList(
  data:
    | StrategyCenterRuleItem[]
    | { items?: StrategyCenterRuleItem[] }
    | { records?: StrategyCenterRuleItem[] }
): StrategyCenterRuleItem[] {
  if (Array.isArray(data)) return data.map((item) => normalizeStrategyCenterRow(item as unknown as Record<string, unknown>))
  const objectData = data as Record<string, unknown>
  const list = Array.isArray(objectData.items)
    ? objectData.items
    : Array.isArray(objectData.records)
      ? objectData.records
      : []
  return (list as StrategyCenterRuleItem[]).map((item) => normalizeStrategyCenterRow(item as unknown as Record<string, unknown>))
}

function normalizeStrategySimulationResult(payload: unknown, runContext?: unknown): StrategySimulationResult {
  const data = payload && typeof payload === 'object' && !Array.isArray(payload) ? (payload as Record<string, unknown>) : {}
  const decision =
    data.scopeDecision && typeof data.scopeDecision === 'object' && !Array.isArray(data.scopeDecision)
      ? (data.scopeDecision as Record<string, unknown>)
      : {}
  const toStringValue = (value: unknown) => String(value ?? '').trim()
  const toNumberOrNull = (value: unknown) => {
    if (value === null || value === undefined || value === '') return null
    const parsed = typeof value === 'number' ? value : Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  const toDisplayText = (value: unknown) => {
    if (value === null || value === undefined || value === '') return ''
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value)
    try {
      return JSON.stringify(value)
    } catch {
      return String(value)
    }
  }
  const toStringList = (value: unknown): string[] => {
    if (!Array.isArray(value)) return []
    return value
      .map((item) => toDisplayText(item).trim())
      .filter(Boolean)
  }
  const toConflictCandidateList = (value: unknown): StrategySimulationConflictCandidate[] => {
    if (!Array.isArray(value)) return []
    return value
      .map((item) => {
        if (item && typeof item === 'object' && !Array.isArray(item)) {
          const record = item as Record<string, unknown>
          return {
            id: toStringValue(record.id ?? record.windowId ?? record.candidateId),
            priority: toNumberOrNull(record.priority ?? record.resolvedPriority),
            weight: toNumberOrNull(record.weight ?? record.batchPercent),
            rawText: toDisplayText(item)
          }
        }
        const rawText = toDisplayText(item).trim()
        return {
          id: '',
          priority: null,
          weight: null,
          rawText
        }
      })
      .filter((candidate) => candidate.id || candidate.priority !== null || candidate.weight !== null || candidate.rawText)
  }
  const matchedRaw = data.matched
  const matched = typeof matchedRaw === 'boolean' ? matchedRaw : String(matchedRaw ?? '').trim().toLowerCase() === 'true'
  const explanations = toStringList(data.explanations)
  const conflictCandidates = toConflictCandidateList(data.conflictCandidates)
  const selectedWindowId = toStringValue(decision.selectedWindowId ?? data.selectedWindowId)
  const matchedWindowCount = toNumberOrNull(decision.matchedWindowCount ?? data.matchedWindowCount)
  const reason = toStringValue(decision.reason ?? data.reason)
  const scopeDecision: StrategySimulationScopeDecision = {
    selectedWindowId,
    matchedWindowCount,
    reason
  }
  return {
    matched,
    scopeReason: toStringValue(data.scopeReason),
    scopeDecision,
    selectedWindowId,
    matchedWindowCount,
    reason,
    resolvedBatchPercent: toNumberOrNull(data.resolvedBatchPercent),
    resolvedPriority: toNumberOrNull(data.resolvedPriority),
    resolvedLayer: toDisplayText(data.resolvedLayer),
    resolvedTimeWindow: toDisplayText(data.resolvedTimeWindow),
    explanations,
    conflictCandidates,
    runContext: toDisplayText(runContext)
  }
}

export async function listNotifications(projectId: string) {
  const pid = String(projectId || '').trim()
  if (!pid) return []
  const data = await requestJson<NotificationRule[] | { items?: NotificationRule[] }>(
    `/api/projects/${encodeURIComponent(pid)}/integrations/notifications`,
    { method: 'GET', headers: authHeader() }
  )
  return normalizeList(data)
}

export async function createNotification(projectId: string, payload: NotificationUpsertPayload) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  return requestJson<NotificationRule>(`/api/projects/${encodeURIComponent(pid)}/integrations/notifications`, {
    method: 'POST',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export async function updateNotification(projectId: string, notificationId: string, payload: NotificationUpsertPayload) {
  const pid = String(projectId || '').trim()
  const nid = String(notificationId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!nid) throw new Error('通知规则 ID 不能为空')
  return requestJson<NotificationRule>(`/api/projects/${encodeURIComponent(pid)}/integrations/notifications/${encodeURIComponent(nid)}`, {
    method: 'PUT',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export async function deleteNotification(projectId: string, notificationId: string) {
  const pid = String(projectId || '').trim()
  const nid = String(notificationId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!nid) throw new Error('通知规则 ID 不能为空')
  return requestJson<Record<string, never>>(`/api/projects/${encodeURIComponent(pid)}/integrations/notifications/${encodeURIComponent(nid)}`, {
    method: 'DELETE',
    headers: authHeader()
  })
}

export async function listNotificationDeliveries(projectId: string, query: NotificationDeliveryListQuery = {}) {
  const pid = String(projectId || '').trim()
  if (!pid) {
    return { items: [], total: 0, page: 1, pageSize: 20 } as NotificationDeliveryListResult
  }
  const page = Number.isFinite(Number(query.page)) && Number(query.page) > 0 ? Number(query.page) : 1
  const pageSize = Number.isFinite(Number(query.pageSize)) && Number(query.pageSize) > 0 ? Number(query.pageSize) : 20
  const params = new URLSearchParams()
  const status = normalizeDeliveryStatus(String(query.status || '').trim())
  const runId = String(query.runId || '').trim()
  if (status) params.set('status', status)
  if (runId) params.set('runId', runId)
  params.set('page', String(page))
  params.set('pageSize', String(pageSize))

  const data = await requestJson<
    | NotificationDelivery[]
    | {
        items?: NotificationDelivery[]
        total?: number
        page?: number
        pageSize?: number
      }
  >(`/api/projects/${encodeURIComponent(pid)}/integrations/notifications/deliveries?${params.toString()}`, {
    method: 'GET',
    headers: authHeader()
  })

  return normalizeDeliveryList(data, { page, pageSize })
}

export async function retryNotificationDelivery(projectId: string, deliveryId: string) {
  const pid = String(projectId || '').trim()
  const did = String(deliveryId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!did) throw new Error('投递 ID 不能为空')
  return requestJson<Record<string, unknown>>(
    `/api/projects/${encodeURIComponent(pid)}/integrations/notifications/deliveries/${encodeURIComponent(did)}/retry`,
    {
      method: 'POST',
      headers: authHeader()
    }
  )
}

export async function listNotificationPromptTemplates(projectId: string) {
  const pid = String(projectId || '').trim()
  if (!pid) return [] as PromptTemplateItem[]
  const params = new URLSearchParams()
  params.set('scene', 'NOTIFICATION_WEBHOOK')
  const data = await requestJson<PromptTemplateItem[]>(
    `/api/projects/${encodeURIComponent(pid)}/prompt-templates?${params.toString()}`,
    { method: 'GET', headers: authHeader() }
  )
  return Array.isArray(data) ? data : []
}

export async function listPromptTemplateGovernance(projectId: string) {
  const pid = String(projectId || '').trim()
  if (!pid) return [] as PromptTemplateGovernanceItem[]
  const data = await requestJson<
    | PromptTemplateGovernanceItem[]
    | { items?: PromptTemplateGovernanceItem[] }
    | { records?: PromptTemplateGovernanceItem[] }
  >(`/api/projects/${encodeURIComponent(pid)}/prompt-templates/governance`, {
    method: 'GET',
    headers: authHeader()
  })
  return normalizeGovernanceList(data)
}

export async function listStrategyCenter(projectId: string) {
  const pid = String(projectId || '').trim()
  if (!pid) return [] as StrategyCenterRuleItem[]
  const data = await requestJson<
    | StrategyCenterRuleItem[]
    | { items?: StrategyCenterRuleItem[] }
    | { records?: StrategyCenterRuleItem[] }
  >(`/api/projects/${encodeURIComponent(pid)}/integrations/notifications/strategy-center`, {
    method: 'GET',
    headers: authHeader()
  })
  return normalizeStrategyCenterList(data)
}

export async function simulateStrategyCenterRule(projectId: string, payload: StrategySimulationRequest) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  const notificationId = String(payload?.notificationId || '').trim()
  if (!notificationId) throw new Error('notificationId 不能为空')
  const data = await requestJson<unknown>(
    `/api/projects/${encodeURIComponent(pid)}/integrations/notifications/strategy-center/simulate`,
    {
      method: 'POST',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        notificationId,
        runContext: payload?.runContext ?? {}
      })
    }
  )
  return normalizeStrategySimulationResult(data)
}

export async function simulateStrategyCenterRuleBatch(projectId: string, payload: StrategySimulationBatchRequest) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  const notificationId = String(payload?.notificationId || '').trim()
  if (!notificationId) throw new Error('notificationId 不能为空')
  if (!Array.isArray(payload?.runContexts) || payload.runContexts.length === 0) {
    throw new Error('runContexts 不能为空')
  }
  const data = await requestJson<unknown>(
    `/api/projects/${encodeURIComponent(pid)}/integrations/notifications/strategy-center/simulate-batch`,
    {
      method: 'POST',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        notificationId,
        runContexts: payload.runContexts
      })
    }
  )
  if (Array.isArray(data)) return data.map((item) => normalizeStrategySimulationResult(item))
  if (data && typeof data === 'object') {
    const objectData = data as Record<string, unknown>
    if (Array.isArray(objectData.items)) {
      return objectData.items.map((item) => {
        if (item && typeof item === 'object' && !Array.isArray(item)) {
          const record = item as Record<string, unknown>
          return normalizeStrategySimulationResult(record.result ?? record, record.runContext)
        }
        return normalizeStrategySimulationResult(item)
      })
    }
    if (Array.isArray(objectData.results)) return objectData.results.map((item) => normalizeStrategySimulationResult(item))
  }
  return []
}

export async function rollbackPromptTemplate(projectId: string, payload: { scene: string; name: string; targetVersion: string }) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  const scene = String(payload?.scene || '').trim()
  const name = String(payload?.name || '').trim()
  const targetVersion = String(payload?.targetVersion || '').trim()
  if (!scene) throw new Error('scene 不能为空')
  if (!name) throw new Error('name 不能为空')
  if (!targetVersion) throw new Error('targetVersion 不能为空')
  return requestJson<Record<string, unknown>>(`/api/projects/${encodeURIComponent(pid)}/prompt-templates/rollback`, {
    method: 'POST',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ scene, name, targetVersion })
  })
}

export async function getNotificationDiagnostics(projectId: string) {
  const pid = String(projectId || '').trim()
  if (!pid) return normalizeDiagnostics({})
  const data = await requestJson<unknown>(`/api/projects/${encodeURIComponent(pid)}/integrations/notifications/diagnostics`, {
    method: 'GET',
    headers: authHeader()
  })
  return normalizeDiagnostics(data)
}
