<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  createNotification,
  deleteNotification,
  getExternalIntegrationDiagnostics,
  getNotificationDiagnostics,
  listNotifications,
  listStrategyCenter,
  listPromptTemplateGovernance,
  listNotificationPromptTemplates,
  listNotificationDeliveries,
  simulateStrategyCenterRule,
  simulateStrategyCenterRuleBatch,
  rollbackPromptTemplate,
  retryNotificationDelivery,
  updateNotification,
  type NotificationDelivery,
  type PromptTemplateGovernanceItem,
  type PromptTemplateItem,
  type NotificationRule,
  type NotificationUpsertPayload,
  type IntegrationDiagnostics,
  type IntegrationDiagnosticsCheck,
  type IntegrationDiagnosticsProviderReadiness,
  type IntegrationDiagnosticsRecentFailure,
  type ExternalIntegrationDiagnostics,
  type ExternalIntegrationDiagnosticItem,
  type StrategyCenterRuleItem,
  type StrategySimulationResult
} from '@/lib/api/integrations'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || '').trim())

const loading = ref(false)
const saving = ref(false)
const deliveryLoading = ref(false)
const deliveryRetryingId = ref('')
const errorMessage = ref('')
const saveError = ref('')
const successMessage = ref('')
const deliveryErrorMessage = ref('')
const deliverySuccessMessage = ref('')
const templateLoadError = ref('')
const governanceLoading = ref(false)
const governanceErrorMessage = ref('')
const governanceSuccessMessage = ref('')
const governanceRollingKey = ref('')
const strategyCenterLoading = ref(false)
const strategyCenterErrorMessage = ref('')
const diagnosticsLoading = ref(false)
const diagnosticsErrorMessage = ref('')
const diagnostics = ref<IntegrationDiagnostics>({
  summary: { status: 'READY', total: 0, blocking: 0, warnings: 0, ready: 0, failedDeliveries: 0 },
  checks: [],
  recentFailures: [],
  providerReadiness: []
})
const externalDiagnostics = ref<ExternalIntegrationDiagnostics>({
  generatedAt: null,
  summary: { status: 'READY', totalChecks: 0, blocking: 0, warnings: 0, ready: 0 },
  checks: [],
  issueLinks: [],
  nextActions: []
})
const strategySimulationLoading = ref(false)
const strategySimulationErrorMessage = ref('')
const strategySimulationResult = ref<StrategySimulationResult | null>(null)
const strategySimulationBatchText = ref('')
const strategySimulationBatchResults = ref<StrategySimulationResult[]>([])
const strategySimulationBatchReasonFilter = ref('ALL')
const strategySimulationBatchExpandedKeys = ref<Record<number, boolean>>({})
const strategySimulationBatchSummary = computed(() => {
  const rows = strategySimulationBatchResults.value
  const total = rows.length
  let matched = 0
  const reasonCounter = new Map<string, number>()
  for (const row of rows) {
    if (row.matched) matched += 1
    const reason = String(row.scopeReason || '').trim() || 'unknown'
    reasonCounter.set(reason, (reasonCounter.get(reason) || 0) + 1)
  }
  const unmatched = total - matched
  const hitRate = total > 0 ? Math.round((matched / total) * 100) : 0
  const reasonBreakdown = Array.from(reasonCounter.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([reason, count]) => `${reason}:${count}`)
    .join(' | ')
  return {
    total,
    matched,
    unmatched,
    hitRateText: `${hitRate}%`,
    reasonBreakdown
  }
})
const strategySimulationBatchReasonOptions = computed(() => {
  const reasonCounter = new Map<string, number>()
  for (const row of strategySimulationBatchResults.value) {
    const reason = String(row.scopeReason || '').trim() || 'unknown'
    reasonCounter.set(reason, (reasonCounter.get(reason) || 0) + 1)
  }
  return Array.from(reasonCounter.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([reason, count]) => ({ reason, count }))
})
const filteredStrategySimulationBatchRows = computed(() => {
  const selected = strategySimulationBatchReasonFilter.value
  return strategySimulationBatchResults.value
    .map((row, index) => ({ row, index }))
    .filter(({ row }) => {
      if (selected === 'ALL') return true
      const reason = String(row.scopeReason || '').trim() || 'unknown'
      return reason === selected
    })
})

const rules = ref<NotificationRule[]>([])
const promptTemplates = ref<PromptTemplateItem[]>([])
const governanceRows = ref<PromptTemplateGovernanceItem[]>([])
const strategyCenterRows = ref<StrategyCenterRuleItem[]>([])
const strategyCenterChannelFilter = ref('ALL')
const strategyCenterTopScopeReasonFilter = ref('ALL')
const strategyCenterKeyword = ref('')
const strategyCenterSortBy = ref<'DEFAULT' | 'HIT_RATE_DESC' | 'SAMPLE_COUNT_DESC'>('DEFAULT')
const strategyCenterFilterSnapshotStorageKey = 'weitesting.strategyCenter.filters.v1'
const strategyCenterFilterSnapshotsStorageKey = 'weitesting.strategyCenter.filters.snapshots.v2'
const strategyCenterCsvColumns = [
  'notificationId',
  'channel',
  'target',
  'enabled',
  'sampleCount',
  'matchedCount',
  'hitRate',
  'topScopeReason'
] as const
type StrategyCenterCsvColumn = (typeof strategyCenterCsvColumns)[number]
const selectedStrategyCenterCsvColumns = ref<StrategyCenterCsvColumn[]>([...strategyCenterCsvColumns])
const strategyCenterFilterSnapshots = ref<StrategyCenterFilterSnapshotRecord[]>([])
const strategyCenterCsvSelectorOpen = ref(false)
const selectedStrategyCenterSnapshotId = ref('')
const rollbackDrafts = ref<Record<string, string>>({})
const selectedId = ref('')
const mode = ref<'create' | 'edit'>('create')
const form = ref({
  channel: '',
  target: '',
  enabled: true,
  ruleJson: '{}'
})
const channelOptions = ['WEBHOOK', 'EMAIL', 'IM'] as const
type ChannelOption = (typeof channelOptions)[number]
const defaultProviderByChannel: Record<ChannelOption, string> = {
  WEBHOOK: 'WEBHOOK',
  EMAIL: 'EMAIL',
  IM: 'IM'
}
const defaultTemplateSceneByChannel: Record<ChannelOption, string> = {
  WEBHOOK: 'NOTIFICATION_WEBHOOK',
  EMAIL: 'NOTIFICATION_EMAIL',
  IM: 'NOTIFICATION_IM'
}
const templateSceneOptions = ['NOTIFICATION_WEBHOOK', 'NOTIFICATION_EMAIL', 'NOTIFICATION_IM'] as const
const providerOptions = ['WEBHOOK', 'EMAIL', 'IM', 'DINGTALK'] as const

const eventOptions = ['RUN_PASSED', 'RUN_FAILED', 'RUN_CANCELED', 'RUN_FINISHED'] as const
type EventOption = (typeof eventOptions)[number]
const templateReferenceModes = ['INLINE', 'ACTIVE', 'PINNED_VERSION'] as const
type TemplateReferenceMode = (typeof templateReferenceModes)[number]
const templateStrategies = ['ACTIVE', 'CANARY'] as const
type TemplateStrategy = (typeof templateStrategies)[number]
const rolloutTriggerTypeOptions = ['MANUAL', 'CRON', 'CI', 'WEBHOOK'] as const
type RolloutTriggerType = (typeof rolloutTriggerTypeOptions)[number]
const rolloutTimeWindowWeekdayOptions = [
  { value: 1, label: 'Mon' },
  { value: 2, label: 'Tue' },
  { value: 3, label: 'Wed' },
  { value: 4, label: 'Thu' },
  { value: 5, label: 'Fri' },
  { value: 6, label: 'Sat' },
  { value: 7, label: 'Sun' }
] as const
type RolloutTimeWindowItem = {
  id: string
  enabled: boolean
  priority: number | null
  weight: number | null
  batchPercent: number | null
  timezoneOffsetMinutes: number | null
  weekdays: number[]
  startHour: number | null
  endHour: number | null
}

function normalizeRolloutTimeWindowItem(raw: unknown, fallbackId: string): RolloutTimeWindowItem {
  const item = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {}
  const id = String(item.id ?? '').trim() || fallbackId
  const enabledRaw = item.enabled
  const enabled =
    enabledRaw === undefined || enabledRaw === null || String(enabledRaw).trim() === ''
      ? true
      : Boolean(enabledRaw)
  const toNumberOrNull = (value: unknown) => {
    if (value === null || value === undefined || String(value).trim() === '') return null
    const parsed = typeof value === 'number' ? value : Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  const weekdays = Array.isArray(item.weekdays)
    ? item.weekdays
        .map((weekday) => (typeof weekday === 'number' ? weekday : Number(weekday)))
        .filter((weekday) => Number.isInteger(weekday) && weekday >= 1 && weekday <= 7)
    : []
  return {
    id,
    enabled,
    priority: toNumberOrNull(item.priority),
    weight: toNumberOrNull(item.weight),
    batchPercent: toNumberOrNull(item.batchPercent),
    timezoneOffsetMinutes: toNumberOrNull(item.timezoneOffsetMinutes),
    weekdays,
    startHour: toNumberOrNull(item.startHour),
    endHour: toNumberOrNull(item.endHour)
  }
}

function createDefaultRolloutTimeWindowItem(index: number): RolloutTimeWindowItem {
  return {
    id: `window-${index + 1}`,
    enabled: true,
    priority: null,
    weight: null,
    batchPercent: null,
    timezoneOffsetMinutes: null,
    weekdays: [],
    startHour: null,
    endHour: null
  }
}

const structuredRule = ref({
  events: [] as EventOption[],
  timeoutSec: 5,
  maxRetries: 3,
  provider: 'WEBHOOK',
  webhookUrl: '',
  keyword: '',
  templateScene: 'NOTIFICATION_WEBHOOK',
  template: '',
  templateName: '',
  templateVersion: '',
  templateStrategy: 'ACTIVE' as TemplateStrategy,
  templateCanaryVersion: '',
  templateCanaryPercent: 10,
  rolloutScopeEnvIds: [] as string[],
  rolloutScopeTriggerTypes: [] as RolloutTriggerType[],
  rolloutScopeMetaTags: [] as string[],
  rolloutScopeBatchPercent: null as number | null,
  rolloutScopePriority: null as number | null,
  rolloutScopeLayerKey: '',
  rolloutScopeLayerValues: [] as string[],
  rolloutScopeTimeZoneOffsetMinutes: null as number | null,
  rolloutScopeWeekdays: [] as number[],
  rolloutScopeStartHour: null as number | null,
  rolloutScopeEndHour: null as number | null,
  rolloutScopeTimeWindows: [] as RolloutTimeWindowItem[],
  autoRollbackEnabled: false,
  autoRollbackFailureThreshold: 5,
  autoRollbackWindowMinutes: 15
})
const templateReferenceMode = ref<TemplateReferenceMode>('INLINE')
const strategySimulatorForm = ref({
  notificationId: '',
  envId: '',
  triggerType: '',
  metaTagsText: '',
  layerValue: '',
  weekday: '',
  hour: '',
  timezoneOffsetMinutes: '',
  seed: ''
})

function strategyCenterTopScopeReason(row: StrategyCenterRuleItem) {
  const topItems = Array.isArray(row.simulationStats?.scopeReasonTop) ? row.simulationStats?.scopeReasonTop : []
  const reason = String(topItems?.[0]?.reason ?? '').trim()
  return reason || '-'
}

const strategyCenterChannelOptions = computed(() => {
  const set = new Set<string>()
  for (const row of strategyCenterRows.value) {
    const channel = String(row.channel || '').trim()
    if (channel) set.add(channel)
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b))
})

const strategyCenterTopScopeReasonOptions = computed(() => {
  const set = new Set<string>()
  for (const row of strategyCenterRows.value) {
    const reason = strategyCenterTopScopeReason(row)
    if (reason !== '-') set.add(reason)
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b))
})

const filteredStrategyCenterRows = computed(() => {
  const channel = strategyCenterChannelFilter.value
  const topScopeReason = strategyCenterTopScopeReasonFilter.value
  const keyword = String(strategyCenterKeyword.value || '').trim().toLowerCase()
  return strategyCenterRows.value.filter((row) => {
    if (channel !== 'ALL' && String(row.channel || '') !== channel) return false
    if (topScopeReason !== 'ALL' && strategyCenterTopScopeReason(row) !== topScopeReason) return false
    if (!keyword) return true
    const notificationId = String(row.notificationId || '').toLowerCase()
    const target = String(row.target || '').toLowerCase()
    return notificationId.includes(keyword) || target.includes(keyword)
  })
})

function strategyCenterSampleCount(row: StrategyCenterRuleItem) {
  const sample = Number(row.simulationStats?.sampleCount)
  if (!Number.isFinite(sample) || sample <= 0) return 0
  return sample
}

function strategyCenterHitRate(row: StrategyCenterRuleItem) {
  const sample = strategyCenterSampleCount(row)
  if (sample <= 0) return -1
  const matched = Number(row.simulationStats?.matchedCount)
  if (!Number.isFinite(matched)) return -1
  return matched / sample
}

const sortedStrategyCenterRows = computed(() => {
  const sortBy = strategyCenterSortBy.value
  const rows = filteredStrategyCenterRows.value.slice()
  if (sortBy === 'DEFAULT') return rows
  if (sortBy === 'HIT_RATE_DESC') {
    rows.sort((a, b) => {
      const rateDiff = strategyCenterHitRate(b) - strategyCenterHitRate(a)
      if (rateDiff !== 0) return rateDiff
      return strategyCenterSampleCount(b) - strategyCenterSampleCount(a)
    })
    return rows
  }
  rows.sort((a, b) => strategyCenterSampleCount(b) - strategyCenterSampleCount(a))
  return rows
})

const strategyCenterSummary = computed(() => {
  const rows = sortedStrategyCenterRows.value
  const total = rows.length
  let enabled = 0
  let withSimulationStats = 0
  for (const row of rows) {
    if (row.enabled) enabled += 1
    if (row.simulationStats) withSimulationStats += 1
  }
  return { total, enabled, withSimulationStats }
})

let syncingFromStructured = false
let syncingFromJson = false

function resetStructuredRule() {
  structuredRule.value = {
    events: [],
    timeoutSec: 5,
    maxRetries: 3,
    provider: 'WEBHOOK',
    webhookUrl: '',
    keyword: '',
    templateScene: 'NOTIFICATION_WEBHOOK',
    template: '',
    templateName: '',
    templateVersion: '',
    templateStrategy: 'ACTIVE',
    templateCanaryVersion: '',
    templateCanaryPercent: 10,
    rolloutScopeEnvIds: [],
    rolloutScopeTriggerTypes: [],
    rolloutScopeMetaTags: [],
    rolloutScopeBatchPercent: null,
    rolloutScopePriority: null,
    rolloutScopeLayerKey: '',
    rolloutScopeLayerValues: [],
    rolloutScopeTimeZoneOffsetMinutes: null,
    rolloutScopeWeekdays: [],
    rolloutScopeStartHour: null,
    rolloutScopeEndHour: null,
    rolloutScopeTimeWindows: [],
    autoRollbackEnabled: false,
    autoRollbackFailureThreshold: 5,
    autoRollbackWindowMinutes: 15
  }
  templateReferenceMode.value = 'INLINE'
}

function parseCommaSeparatedText(raw: unknown) {
  return String(raw || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function parseCommaSeparatedTextCaseInsensitiveUnique(raw: unknown) {
  const items = parseCommaSeparatedText(raw)
  const deduped: string[] = []
  const seen = new Set<string>()
  for (const item of items) {
    const key = item.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    deduped.push(item)
  }
  return deduped
}

function addRolloutTimeWindow() {
  structuredRule.value.rolloutScopeTimeWindows.push(
    createDefaultRolloutTimeWindowItem(structuredRule.value.rolloutScopeTimeWindows.length)
  )
}

function removeRolloutTimeWindow(index: number) {
  if (index < 0 || index >= structuredRule.value.rolloutScopeTimeWindows.length) return
  structuredRule.value.rolloutScopeTimeWindows.splice(index, 1)
}

function normalizeTemplateSceneByChannel(channel: string, rawScene: unknown) {
  const normalizedChannel = String(channel || '').trim().toUpperCase() as ChannelOption
  const defaultScene = defaultTemplateSceneByChannel[normalizedChannel] || 'NOTIFICATION_WEBHOOK'
  const scene = String(rawScene || '')
    .trim()
    .toUpperCase()
  if (!scene) return defaultScene
  if (templateSceneOptions.includes(scene as (typeof templateSceneOptions)[number])) return scene
  if (scene === 'WEBHOOK') return 'NOTIFICATION_WEBHOOK'
  if (scene === 'EMAIL') return 'NOTIFICATION_EMAIL'
  if (scene === 'IM') return 'NOTIFICATION_IM'
  return scene
}

function inferTemplateReferenceMode(rule: Record<string, unknown>): TemplateReferenceMode {
  const template = typeof rule.template === 'string' ? rule.template.trim() : ''
  const templateName = typeof rule.templateName === 'string' ? rule.templateName.trim() : ''
  const templateVersion = typeof rule.templateVersion === 'string' ? rule.templateVersion.trim() : ''
  if (templateName && templateVersion) return 'PINNED_VERSION'
  if (templateName || templateVersion) return 'ACTIVE'
  if (template) return 'INLINE'
  return 'INLINE'
}

function updateStructuredFromRule(rule: Record<string, unknown>) {
  const events = Array.isArray(rule.events)
    ? rule.events.filter((item): item is EventOption => typeof item === 'string' && eventOptions.includes(item as EventOption))
    : []
  const timeoutSec = typeof rule.timeoutSec === 'number' ? rule.timeoutSec : Number(rule.timeoutSec)
  const maxRetries = typeof rule.maxRetries === 'number' ? rule.maxRetries : Number(rule.maxRetries)
  const provider = typeof rule.provider === 'string' && rule.provider.trim() ? rule.provider.trim() : 'WEBHOOK'
  const webhookUrl = typeof rule.webhookUrl === 'string'
    ? rule.webhookUrl
    : rule.dingTalk && typeof rule.dingTalk === 'object' && typeof (rule.dingTalk as Record<string, unknown>).webhookUrl === 'string'
      ? ((rule.dingTalk as Record<string, unknown>).webhookUrl as string)
      : ''
  const keyword = typeof rule.keyword === 'string'
    ? rule.keyword
    : rule.dingTalk && typeof rule.dingTalk === 'object' && typeof (rule.dingTalk as Record<string, unknown>).keyword === 'string'
      ? ((rule.dingTalk as Record<string, unknown>).keyword as string)
      : ''
  const templateScene = normalizeTemplateSceneByChannel(form.value.channel, rule.templateScene)
  const template = typeof rule.template === 'string' ? rule.template : ''
  const templateName = typeof rule.templateName === 'string' ? rule.templateName : ''
  const templateVersion = typeof rule.templateVersion === 'string' ? rule.templateVersion : ''
  const templateStrategy =
    typeof rule.templateStrategy === 'string' && templateStrategies.includes(rule.templateStrategy as TemplateStrategy)
      ? (rule.templateStrategy as TemplateStrategy)
      : 'ACTIVE'
  const templateCanaryVersion = typeof rule.templateCanaryVersion === 'string' ? rule.templateCanaryVersion : ''
  const templateCanaryPercent =
    typeof rule.templateCanaryPercent === 'number' ? rule.templateCanaryPercent : Number(rule.templateCanaryPercent)
  const rolloutScope = rule.rolloutScope && typeof rule.rolloutScope === 'object' ? (rule.rolloutScope as Record<string, unknown>) : null
  const rolloutScopeEnvIds = Array.isArray(rolloutScope?.envIds)
    ? rolloutScope.envIds
        .filter((item): item is string => typeof item === 'string')
        .map((item) => item.trim())
        .filter(Boolean)
    : []
  const rolloutScopeTriggerTypes = Array.isArray(rolloutScope?.triggerTypes)
    ? rolloutScope.triggerTypes.filter(
        (item): item is RolloutTriggerType =>
          typeof item === 'string' && rolloutTriggerTypeOptions.includes(item as RolloutTriggerType)
      )
    : []
  const rolloutScopeMetaTags = Array.isArray(rolloutScope?.metaTags)
    ? rolloutScope.metaTags
        .filter((item): item is string => typeof item === 'string')
        .map((item) => item.trim())
        .filter(Boolean)
    : []
  const rolloutScopeBatchPercent =
    typeof rolloutScope?.batchPercent === 'number' ? rolloutScope.batchPercent : Number(rolloutScope?.batchPercent)
  const rolloutScopePriority =
    typeof rolloutScope?.priority === 'number' ? rolloutScope.priority : Number(rolloutScope?.priority)
  const rolloutScopeLayerKey = typeof rolloutScope?.layerKey === 'string' ? rolloutScope.layerKey.trim() : ''
  const rolloutScopeLayerValues = Array.isArray(rolloutScope?.layerValues)
    ? rolloutScope.layerValues
        .filter((item): item is string => typeof item === 'string')
        .map((item) => item.trim())
        .filter(Boolean)
    : []
  const timeWindow = rolloutScope?.timeWindow && typeof rolloutScope.timeWindow === 'object'
    ? (rolloutScope.timeWindow as Record<string, unknown>)
    : null
  const timeWindows = Array.isArray(rolloutScope?.timeWindows) ? rolloutScope.timeWindows : []
  const rolloutScopeTimeZoneOffsetMinutes =
    typeof timeWindow?.timezoneOffsetMinutes === 'number'
      ? timeWindow.timezoneOffsetMinutes
      : Number(timeWindow?.timezoneOffsetMinutes)
  const rolloutScopeWeekdays = Array.isArray(timeWindow?.weekdays)
    ? timeWindow.weekdays
        .filter((item): item is number => typeof item === 'number' && Number.isInteger(item) && item >= 1 && item <= 7)
    : []
  const rolloutScopeStartHour =
    typeof timeWindow?.startHour === 'number' ? timeWindow.startHour : Number(timeWindow?.startHour)
  const rolloutScopeEndHour =
    typeof timeWindow?.endHour === 'number' ? timeWindow.endHour : Number(timeWindow?.endHour)
  const rolloutScopeTimeWindows =
    timeWindows.length > 0
      ? timeWindows.map((item, index) => normalizeRolloutTimeWindowItem(item, `window-${index + 1}`))
      : timeWindow
        ? [normalizeRolloutTimeWindowItem(timeWindow, 'window-1')]
        : []
  const autoRollbackEnabled = Boolean(rule.autoRollbackEnabled)
  const autoRollbackFailureThreshold =
    typeof rule.autoRollbackFailureThreshold === 'number'
      ? rule.autoRollbackFailureThreshold
      : Number(rule.autoRollbackFailureThreshold)
  const autoRollbackWindowMinutes =
    typeof rule.autoRollbackWindowMinutes === 'number'
      ? rule.autoRollbackWindowMinutes
      : Number(rule.autoRollbackWindowMinutes)
  structuredRule.value = {
    events,
    timeoutSec: Number.isFinite(timeoutSec) ? timeoutSec : 5,
    maxRetries: Number.isFinite(maxRetries) ? maxRetries : 3,
    provider,
    webhookUrl,
    keyword,
    templateScene,
    template,
    templateName,
    templateVersion,
    templateStrategy,
    templateCanaryVersion,
    templateCanaryPercent: Number.isFinite(templateCanaryPercent) ? templateCanaryPercent : 10,
    rolloutScopeEnvIds,
    rolloutScopeTriggerTypes,
    rolloutScopeMetaTags,
    rolloutScopeBatchPercent: Number.isFinite(rolloutScopeBatchPercent) ? rolloutScopeBatchPercent : null,
    rolloutScopePriority: Number.isFinite(rolloutScopePriority) ? rolloutScopePriority : null,
    rolloutScopeLayerKey,
    rolloutScopeLayerValues,
    rolloutScopeTimeZoneOffsetMinutes: Number.isFinite(rolloutScopeTimeZoneOffsetMinutes) ? rolloutScopeTimeZoneOffsetMinutes : null,
    rolloutScopeWeekdays,
    rolloutScopeStartHour: Number.isFinite(rolloutScopeStartHour) ? rolloutScopeStartHour : null,
    rolloutScopeEndHour: Number.isFinite(rolloutScopeEndHour) ? rolloutScopeEndHour : null,
    rolloutScopeTimeWindows,
    autoRollbackEnabled,
    autoRollbackFailureThreshold: Number.isFinite(autoRollbackFailureThreshold) ? autoRollbackFailureThreshold : 5,
    autoRollbackWindowMinutes: Number.isFinite(autoRollbackWindowMinutes) ? autoRollbackWindowMinutes : 15
  }
  templateReferenceMode.value = inferTemplateReferenceMode(rule)
}

function buildRuleFromStructured() {
  const timeoutSec = Number(structuredRule.value.timeoutSec)
  const maxRetries = Number(structuredRule.value.maxRetries)
  const provider = structuredRule.value.provider.trim() || 'WEBHOOK'
  const webhookUrl = structuredRule.value.webhookUrl.trim()
  const keyword = structuredRule.value.keyword.trim()
  const templateScene = normalizeTemplateSceneByChannel(form.value.channel, structuredRule.value.templateScene)
  const template = structuredRule.value.template.trim()
  const templateName = structuredRule.value.templateName.trim()
  const templateVersion = structuredRule.value.templateVersion.trim()
  const templateStrategy = structuredRule.value.templateStrategy
  const templateCanaryVersion = structuredRule.value.templateCanaryVersion.trim()
  const templateCanaryPercent = Number(structuredRule.value.templateCanaryPercent)
  const rolloutScopeEnvIds = structuredRule.value.rolloutScopeEnvIds
    .map((item) => String(item || '').trim())
    .filter(Boolean)
  const rolloutScopeTriggerTypes = structuredRule.value.rolloutScopeTriggerTypes.filter((item) =>
    rolloutTriggerTypeOptions.includes(item)
  )
  const rolloutScopeMetaTags = structuredRule.value.rolloutScopeMetaTags
    .map((item) => String(item || '').trim())
    .filter(Boolean)
  const rolloutScopeBatchPercentRaw = structuredRule.value.rolloutScopeBatchPercent
  const rolloutScopePriorityRaw = structuredRule.value.rolloutScopePriority
  const rolloutScopeLayerKey = String(structuredRule.value.rolloutScopeLayerKey || '').trim()
  const rolloutScopeLayerValues = structuredRule.value.rolloutScopeLayerValues
    .map((item) => String(item || '').trim())
    .filter(Boolean)
  const rolloutScopeTimeZoneOffsetMinutesRaw = structuredRule.value.rolloutScopeTimeZoneOffsetMinutes
  const rolloutScopeWeekdays = structuredRule.value.rolloutScopeWeekdays.filter(
    (item) => Number.isInteger(item) && item >= 1 && item <= 7
  )
  const rolloutScopeStartHourRaw = structuredRule.value.rolloutScopeStartHour
  const rolloutScopeEndHourRaw = structuredRule.value.rolloutScopeEndHour
  const rolloutScopeTimeWindows = structuredRule.value.rolloutScopeTimeWindows
    .map((item, index) => normalizeRolloutTimeWindowItem(item, `window-${index + 1}`))
    .filter((item) => {
      const hasPriority = item.priority !== null && Number.isFinite(Number(item.priority))
      const hasWeight = item.weight !== null && Number.isFinite(Number(item.weight))
      const hasBatchPercent = item.batchPercent !== null && Number.isFinite(Number(item.batchPercent))
      const hasTz = item.timezoneOffsetMinutes !== null && Number.isFinite(Number(item.timezoneOffsetMinutes))
      const hasWeekdays = item.weekdays.length > 0
      const hasStart = item.startHour !== null && Number.isFinite(Number(item.startHour))
      const hasEnd = item.endHour !== null && Number.isFinite(Number(item.endHour))
      return Boolean(item.id || hasPriority || hasWeight || hasBatchPercent || hasTz || hasWeekdays || hasStart || hasEnd || !item.enabled)
    })
  const hasRolloutScopeBatchPercent =
    rolloutScopeBatchPercentRaw !== null &&
    String(rolloutScopeBatchPercentRaw).trim() !== ''
  const hasRolloutScopePriority =
    rolloutScopePriorityRaw !== null &&
    String(rolloutScopePriorityRaw).trim() !== ''
  const hasRolloutScopeLayerKey = Boolean(rolloutScopeLayerKey)
  const hasRolloutScopeLayerValues = rolloutScopeLayerValues.length > 0
  const hasRolloutScopeTimeZoneOffset =
    rolloutScopeTimeZoneOffsetMinutesRaw !== null &&
    String(rolloutScopeTimeZoneOffsetMinutesRaw).trim() !== ''
  const hasRolloutScopeStartHour =
    rolloutScopeStartHourRaw !== null &&
    String(rolloutScopeStartHourRaw).trim() !== ''
  const hasRolloutScopeEndHour =
    rolloutScopeEndHourRaw !== null &&
    String(rolloutScopeEndHourRaw).trim() !== ''
  const rolloutScopeBatchPercent = hasRolloutScopeBatchPercent ? Number(rolloutScopeBatchPercentRaw) : Number.NaN
  const rolloutScopePriority = hasRolloutScopePriority ? Number(rolloutScopePriorityRaw) : Number.NaN
  const rolloutScopeTimeZoneOffsetMinutes = hasRolloutScopeTimeZoneOffset ? Number(rolloutScopeTimeZoneOffsetMinutesRaw) : Number.NaN
  const rolloutScopeStartHour = hasRolloutScopeStartHour ? Number(rolloutScopeStartHourRaw) : Number.NaN
  const rolloutScopeEndHour = hasRolloutScopeEndHour ? Number(rolloutScopeEndHourRaw) : Number.NaN
  const hasLegacyTimeWindow =
    hasRolloutScopeTimeZoneOffset || rolloutScopeWeekdays.length > 0 || hasRolloutScopeStartHour || hasRolloutScopeEndHour
  const autoRollbackFailureThreshold = Number(structuredRule.value.autoRollbackFailureThreshold)
  const autoRollbackWindowMinutes = Number(structuredRule.value.autoRollbackWindowMinutes)
  const mode = templateReferenceMode.value
  const rule: Record<string, unknown> = {
    timeoutSec: Number.isFinite(timeoutSec) ? timeoutSec : 5,
    maxRetries: Number.isFinite(maxRetries) ? maxRetries : 3,
    provider,
    templateScene
  }
  if (provider === 'DINGTALK') {
    if (webhookUrl) rule.webhookUrl = webhookUrl
    if (keyword) rule.keyword = keyword
  }
  if (structuredRule.value.events.length > 0) rule.events = [...structuredRule.value.events]
  if (mode === 'INLINE') {
    if (template) rule.template = template
  } else if (mode === 'ACTIVE') {
    if (templateName) rule.templateName = templateName
  } else if (mode === 'PINNED_VERSION') {
    if (templateName) rule.templateName = templateName
    if (templateVersion) rule.templateVersion = templateVersion
  }
  if (mode === 'ACTIVE' || mode === 'PINNED_VERSION') {
    rule.templateStrategy = templateStrategy
    if (templateStrategy === 'CANARY') {
      if (templateCanaryVersion) rule.templateCanaryVersion = templateCanaryVersion
      if (Number.isFinite(templateCanaryPercent)) rule.templateCanaryPercent = templateCanaryPercent
    }
  }
  if (
    rolloutScopeEnvIds.length > 0 ||
    rolloutScopeTriggerTypes.length > 0 ||
    rolloutScopeMetaTags.length > 0 ||
    hasRolloutScopeBatchPercent ||
    hasRolloutScopePriority ||
    hasRolloutScopeLayerKey ||
    hasRolloutScopeLayerValues ||
    rolloutScopeTimeWindows.length > 0 ||
    hasRolloutScopeTimeZoneOffset ||
    rolloutScopeWeekdays.length > 0 ||
    hasRolloutScopeStartHour ||
    hasRolloutScopeEndHour
  ) {
    const rolloutScope: Record<string, unknown> = {}
    if (rolloutScopeEnvIds.length > 0) rolloutScope.envIds = rolloutScopeEnvIds
    if (rolloutScopeTriggerTypes.length > 0) rolloutScope.triggerTypes = rolloutScopeTriggerTypes
    if (rolloutScopeMetaTags.length > 0) rolloutScope.metaTags = rolloutScopeMetaTags
    if (hasRolloutScopeBatchPercent && Number.isFinite(rolloutScopeBatchPercent)) {
      rolloutScope.batchPercent = rolloutScopeBatchPercent
    }
    if (hasRolloutScopePriority && Number.isFinite(rolloutScopePriority)) {
      rolloutScope.priority = rolloutScopePriority
    }
    if (hasRolloutScopeLayerKey) rolloutScope.layerKey = rolloutScopeLayerKey
    if (hasRolloutScopeLayerValues) rolloutScope.layerValues = rolloutScopeLayerValues
    if (
      rolloutScopeTimeWindows.length > 0
    ) {
      rolloutScope.timeWindows = rolloutScopeTimeWindows.map((item) => {
        const timeWindowItem: Record<string, unknown> = {
          id: item.id,
          enabled: Boolean(item.enabled)
        }
        if (item.priority !== null && Number.isFinite(Number(item.priority))) timeWindowItem.priority = Number(item.priority)
        if (item.weight !== null && Number.isFinite(Number(item.weight))) timeWindowItem.weight = Number(item.weight)
        if (item.batchPercent !== null && Number.isFinite(Number(item.batchPercent))) timeWindowItem.batchPercent = Number(item.batchPercent)
        if (item.timezoneOffsetMinutes !== null && Number.isFinite(Number(item.timezoneOffsetMinutes))) {
          timeWindowItem.timezoneOffsetMinutes = Number(item.timezoneOffsetMinutes)
        }
        if (item.weekdays.length > 0) timeWindowItem.weekdays = item.weekdays
        if (item.startHour !== null && Number.isFinite(Number(item.startHour))) timeWindowItem.startHour = Number(item.startHour)
        if (item.endHour !== null && Number.isFinite(Number(item.endHour))) timeWindowItem.endHour = Number(item.endHour)
        return timeWindowItem
      })
    }
    if (rolloutScopeTimeWindows.length === 0 && hasLegacyTimeWindow) {
      const timeWindow: Record<string, unknown> = {}
      if (hasRolloutScopeTimeZoneOffset && Number.isFinite(rolloutScopeTimeZoneOffsetMinutes)) {
        timeWindow.timezoneOffsetMinutes = rolloutScopeTimeZoneOffsetMinutes
      }
      if (rolloutScopeWeekdays.length > 0) {
        timeWindow.weekdays = rolloutScopeWeekdays
      }
      if (hasRolloutScopeStartHour && Number.isFinite(rolloutScopeStartHour)) {
        timeWindow.startHour = rolloutScopeStartHour
      }
      if (hasRolloutScopeEndHour && Number.isFinite(rolloutScopeEndHour)) {
        timeWindow.endHour = rolloutScopeEndHour
      }
      rolloutScope.timeWindow = timeWindow
    }
    rule.rolloutScope = rolloutScope
  }
  rule.autoRollbackEnabled = Boolean(structuredRule.value.autoRollbackEnabled)
  if (Number.isFinite(autoRollbackFailureThreshold)) rule.autoRollbackFailureThreshold = autoRollbackFailureThreshold
  if (Number.isFinite(autoRollbackWindowMinutes)) rule.autoRollbackWindowMinutes = autoRollbackWindowMinutes
  return rule
}

const templateReferenceTip = computed(() => {
  if (templateReferenceMode.value === 'INLINE') return '当前使用内联模板内容（template）'
  if (templateReferenceMode.value === 'ACTIVE') {
    const name = structuredRule.value.templateName.trim()
    return name ? `当前使用活动模板引用：${name}` : '当前使用活动模板引用（templateName）'
  }
  const name = structuredRule.value.templateName.trim()
  const version = structuredRule.value.templateVersion.trim()
  if (!name && !version) return ''
  if (name && version) return `当前使用版本模板引用：${name}@${version}`
  return '当前使用版本模板引用'
})

const templateNameOptions = computed(() => {
  const names = new Set<string>()
  for (const item of promptTemplates.value) {
    const name = String(item.name || '').trim()
    if (name) names.add(name)
  }
  return Array.from(names).sort((a, b) => a.localeCompare(b))
})

const hasTemplateOptions = computed(() => templateNameOptions.value.length > 0)

const templateVersionOptions = computed(() => {
  const selectedName = structuredRule.value.templateName.trim()
  if (!selectedName) return [] as string[]
  const versions = new Set<string>()
  for (const item of promptTemplates.value) {
    const name = String(item.name || '').trim()
    const version = String(item.version || '').trim()
    if (name === selectedName && version) versions.add(version)
  }
  return Array.from(versions).sort((a, b) => a.localeCompare(b))
})

const rolloutScopeEnvIdsText = computed({
  get: () => structuredRule.value.rolloutScopeEnvIds.join(', '),
  set: (value: string) => {
    structuredRule.value.rolloutScopeEnvIds = parseCommaSeparatedText(value)
  }
})

const rolloutScopeMetaTagsText = computed({
  get: () => structuredRule.value.rolloutScopeMetaTags.join(', '),
  set: (value: string) => {
    structuredRule.value.rolloutScopeMetaTags = parseCommaSeparatedText(value)
  }
})

const rolloutScopeLayerValuesText = computed({
  get: () => structuredRule.value.rolloutScopeLayerValues.join(', '),
  set: (value: string) => {
    structuredRule.value.rolloutScopeLayerValues = parseCommaSeparatedTextCaseInsensitiveUnique(value)
  }
})

function resetForm() {
  form.value = { channel: 'WEBHOOK', target: '', enabled: true, ruleJson: '{}' }
  resetStructuredRule()
}

function startCreate() {
  mode.value = 'create'
  selectedId.value = ''
  saveError.value = ''
  successMessage.value = ''
  resetForm()
}

function applyRule(rule: NotificationRule) {
  mode.value = 'edit'
  selectedId.value = rule.id
  form.value = {
    channel: rule.channel || '',
    target: rule.target || '',
    enabled: Boolean(rule.enabled),
    ruleJson: JSON.stringify(rule.rule || {}, null, 2)
  }
  updateStructuredFromRule((rule.rule || {}) as Record<string, unknown>)
}

const selectedRule = computed(() => rules.value.find((item) => item.id === selectedId.value) || null)
const selectedChannel = computed<ChannelOption | ''>(() => {
  const value = String(form.value.channel || '').trim().toUpperCase()
  return channelOptions.includes(value as ChannelOption) ? (value as ChannelOption) : ''
})
const templateSceneDefaultTip = computed(() => {
  const channel = selectedChannel.value
  if (!channel) return '请先选择 channel'
  return `当前 channel 默认 templateScene：${defaultTemplateSceneByChannel[channel]}`
})

const deliveryStatusOptions = [
  { value: 'QUEUED', label: '排队中 (QUEUED)' },
  { value: 'SENT', label: '已发送 (SENT)' },
  { value: 'FAILED', label: '失败 (FAILED)' }
] as const

const deliveryStatusLabels: Record<string, string> = {
  QUEUED: '排队中',
  SENT: '已发送',
  FAILED: '失败'
}
const deliveryQuery = ref({
  status: '',
  runId: '',
  page: 1,
  pageSize: 10
})
const deliveryRows = ref<NotificationDelivery[]>([])
const deliveryTotal = ref(0)

const deliveryTotalPages = computed(() => {
  const size = Number(deliveryQuery.value.pageSize) || 10
  return Math.max(1, Math.ceil((deliveryTotal.value || 0) / size))
})

function parseRuleJson() {
  let value: unknown
  try {
    value = JSON.parse(String(form.value.ruleJson || '').trim() || '{}')
  } catch {
    throw new Error('规则不是合法 JSON')
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('规则必须是 JSON 对象')
  }
  return value as Record<string, unknown>
}

function buildPayload(): NotificationUpsertPayload {
  const provider = structuredRule.value.provider.trim().toUpperCase()
  const channel = provider === 'DINGTALK' ? 'IM' : form.value.channel.trim()
  const target = form.value.target.trim()
  if (!channel) throw new Error('channel 不能为空')
  if (!target) throw new Error('target 不能为空')
  if (templateReferenceMode.value === 'INLINE' && !structuredRule.value.template.trim()) {
    throw new Error('INLINE 模式下 template 不能为空')
  }
  if (templateReferenceMode.value === 'ACTIVE' && !structuredRule.value.templateName.trim()) {
    throw new Error('ACTIVE 模式下 templateName 不能为空')
  }
  if (templateReferenceMode.value === 'PINNED_VERSION') {
    if (!structuredRule.value.templateName.trim()) throw new Error('PINNED_VERSION 模式下 templateName 不能为空')
    if (!structuredRule.value.templateVersion.trim()) throw new Error('PINNED_VERSION 模式下 templateVersion 不能为空')
  }
  if (templateReferenceMode.value === 'ACTIVE' || templateReferenceMode.value === 'PINNED_VERSION') {
    if (structuredRule.value.templateStrategy === 'CANARY') {
      if (!structuredRule.value.templateName.trim()) throw new Error('CANARY 策略下 templateName 不能为空')
      if (structuredRule.value.templateVersion.trim()) throw new Error('CANARY 策略下 templateVersion 不允许设置')
      if (!structuredRule.value.templateCanaryVersion.trim()) throw new Error('CANARY 策略下 templateCanaryVersion 不能为空')
      const canaryPercent = Number(structuredRule.value.templateCanaryPercent)
      if (!Number.isFinite(canaryPercent) || canaryPercent < 1 || canaryPercent > 100) {
        throw new Error('CANARY 策略下 templateCanaryPercent 必须在 1-100 之间')
      }
    }
  }
  if (provider === 'DINGTALK') {
    const webhookUrl = structuredRule.value.webhookUrl.trim()
    if (!webhookUrl) throw new Error('DINGTALK provider 下 webhookUrl 不能为空')
  }
  const autoRollbackFailureThreshold = Number(structuredRule.value.autoRollbackFailureThreshold)
  if (!Number.isFinite(autoRollbackFailureThreshold) || autoRollbackFailureThreshold < 1 || autoRollbackFailureThreshold > 20) {
    throw new Error('autoRollbackFailureThreshold 必须在 1-20 之间')
  }
  const autoRollbackWindowMinutes = Number(structuredRule.value.autoRollbackWindowMinutes)
  if (!Number.isFinite(autoRollbackWindowMinutes) || autoRollbackWindowMinutes < 1 || autoRollbackWindowMinutes > 1440) {
    throw new Error('autoRollbackWindowMinutes 必须在 1-1440 之间')
  }
  const rolloutScopeTriggerTypes = structuredRule.value.rolloutScopeTriggerTypes
  const rolloutScopeBatchPercentRaw = structuredRule.value.rolloutScopeBatchPercent
  const rolloutScopePriorityRaw = structuredRule.value.rolloutScopePriority
  const rolloutScopeLayerKey = String(structuredRule.value.rolloutScopeLayerKey || '').trim()
  const rolloutScopeLayerValues = structuredRule.value.rolloutScopeLayerValues
    .map((item) => String(item || '').trim())
    .filter(Boolean)
  const rolloutScopeTimeZoneOffsetMinutesRaw = structuredRule.value.rolloutScopeTimeZoneOffsetMinutes
  const rolloutScopeWeekdays = structuredRule.value.rolloutScopeWeekdays.filter(
    (item) => Number.isInteger(item) && item >= 1 && item <= 7
  )
  const rolloutScopeStartHourRaw = structuredRule.value.rolloutScopeStartHour
  const rolloutScopeEndHourRaw = structuredRule.value.rolloutScopeEndHour
  const rolloutScopeTimeWindows = structuredRule.value.rolloutScopeTimeWindows.map((item, index) =>
    normalizeRolloutTimeWindowItem(item, `window-${index + 1}`)
  )
  const hasRolloutScopeBatchPercent =
    rolloutScopeBatchPercentRaw !== null &&
    String(rolloutScopeBatchPercentRaw).trim() !== ''
  const hasRolloutScopePriority =
    rolloutScopePriorityRaw !== null &&
    String(rolloutScopePriorityRaw).trim() !== ''
  const hasRolloutScopeLayerKey = Boolean(rolloutScopeLayerKey)
  const hasRolloutScopeLayerValues = rolloutScopeLayerValues.length > 0
  const hasRolloutScopeTimeZoneOffset =
    rolloutScopeTimeZoneOffsetMinutesRaw !== null &&
    String(rolloutScopeTimeZoneOffsetMinutesRaw).trim() !== ''
  const hasRolloutScopeStartHour =
    rolloutScopeStartHourRaw !== null &&
    String(rolloutScopeStartHourRaw).trim() !== ''
  const hasRolloutScopeEndHour =
    rolloutScopeEndHourRaw !== null &&
    String(rolloutScopeEndHourRaw).trim() !== ''
  const hasRolloutScope =
    structuredRule.value.rolloutScopeEnvIds.length > 0 ||
    rolloutScopeTriggerTypes.length > 0 ||
    structuredRule.value.rolloutScopeMetaTags.length > 0 ||
    hasRolloutScopeBatchPercent ||
    hasRolloutScopePriority ||
    hasRolloutScopeLayerKey ||
    hasRolloutScopeLayerValues ||
    rolloutScopeTimeWindows.length > 0 ||
    hasRolloutScopeTimeZoneOffset ||
    rolloutScopeWeekdays.length > 0 ||
    hasRolloutScopeStartHour ||
    hasRolloutScopeEndHour
  if (hasRolloutScope) {
    if (rolloutScopeTriggerTypes.some((item) => !rolloutTriggerTypeOptions.includes(item))) {
      throw new Error('rolloutScope.triggerTypes 仅允许 MANUAL/CRON/CI/WEBHOOK')
    }
    if (hasRolloutScopeBatchPercent) {
      const batchPercent = Number(rolloutScopeBatchPercentRaw)
      if (!Number.isFinite(batchPercent) || batchPercent < 1 || batchPercent > 100) {
        throw new Error('rolloutScope.batchPercent 必须在 1-100 之间')
      }
    }
    if (hasRolloutScopePriority) {
      const priority = Number(rolloutScopePriorityRaw)
      if (!Number.isFinite(priority) || priority < 1 || priority > 1000) {
        throw new Error('rolloutScope.priority 必须在 1-1000 之间')
      }
    }
    if (hasRolloutScopeLayerKey && !/^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(rolloutScopeLayerKey)) {
      throw new Error('rolloutScope.layerKey 需匹配 ^[A-Za-z][A-Za-z0-9_]{0,63}$')
    }
    if (hasRolloutScopeLayerKey && !hasRolloutScopeLayerValues) {
      throw new Error('rolloutScope.layerKey 设置时，rolloutScope.layerValues 不能为空')
    }
    if (!hasRolloutScopeLayerKey && hasRolloutScopeLayerValues) {
      throw new Error('rolloutScope.layerValues 设置时，rolloutScope.layerKey 不能为空')
    }
    if (hasRolloutScopeTimeZoneOffset) {
      const timezoneOffsetMinutes = Number(rolloutScopeTimeZoneOffsetMinutesRaw)
      if (!Number.isFinite(timezoneOffsetMinutes) || timezoneOffsetMinutes < -720 || timezoneOffsetMinutes > 840) {
        throw new Error('rolloutScope.timeWindow.timezoneOffsetMinutes 必须在 -720 到 840 之间')
      }
    }
    if (hasRolloutScopeStartHour !== hasRolloutScopeEndHour) {
      throw new Error('rolloutScope.timeWindow.startHour 与 endHour 必须同时设置')
    }
    if (hasRolloutScopeStartHour) {
      const startHour = Number(rolloutScopeStartHourRaw)
      const endHour = Number(rolloutScopeEndHourRaw)
      if (!Number.isFinite(startHour) || startHour < 0 || startHour > 23) {
        throw new Error('rolloutScope.timeWindow.startHour 必须在 0-23 之间')
      }
      if (!Number.isFinite(endHour) || endHour < 0 || endHour > 23) {
        throw new Error('rolloutScope.timeWindow.endHour 必须在 0-23 之间')
      }
    }
    if (rolloutScopeWeekdays.some((item) => item < 1 || item > 7)) {
      throw new Error('rolloutScope.timeWindow.weekdays 仅允许 1-7')
    }
    for (const [index, windowItem] of rolloutScopeTimeWindows.entries()) {
      const label = `rolloutScope.timeWindows[${index}]`
      if (!windowItem.id.trim()) throw new Error(`${label}.id 不能为空`)
      const hasStart = windowItem.startHour !== null
      const hasEnd = windowItem.endHour !== null
      if (windowItem.priority !== null && (windowItem.priority < 1 || windowItem.priority > 1000)) {
        throw new Error(`${label}.priority 必须在 1-1000 之间`)
      }
      if (windowItem.weight !== null && (windowItem.weight < 1 || windowItem.weight > 100)) {
        throw new Error(`${label}.weight 必须在 1-100 之间`)
      }
      if (windowItem.batchPercent !== null && (windowItem.batchPercent < 1 || windowItem.batchPercent > 100)) {
        throw new Error(`${label}.batchPercent 必须在 1-100 之间`)
      }
      if (
        windowItem.timezoneOffsetMinutes !== null &&
        (windowItem.timezoneOffsetMinutes < -720 || windowItem.timezoneOffsetMinutes > 840)
      ) {
        throw new Error(`${label}.timezoneOffsetMinutes 必须在 -720 到 840 之间`)
      }
      if (hasStart !== hasEnd) throw new Error(`${label}.startHour 与 endHour 必须同时设置`)
      if (hasStart) {
        if (windowItem.startHour! < 0 || windowItem.startHour! > 23) throw new Error(`${label}.startHour 必须在 0-23 之间`)
        if (windowItem.endHour! < 0 || windowItem.endHour! > 23) throw new Error(`${label}.endHour 必须在 0-23 之间`)
      }
      if (windowItem.weekdays.some((item: number) => item < 1 || item > 7)) {
        throw new Error(`${label}.weekdays 仅允许 1-7`)
      }
    }
  }
  const rule = buildRuleFromStructured()
  syncingFromStructured = true
  form.value.ruleJson = JSON.stringify(rule, null, 2)
  syncingFromStructured = false
  return {
    channel,
    target,
    enabled: Boolean(form.value.enabled),
    rule: parseRuleJson()
  }
}

watch(
  () => form.value.channel,
  (value, previous) => {
    const next = String(value || '').trim().toUpperCase()
    const prev = String(previous || '').trim().toUpperCase()
    if (!channelOptions.includes(next as ChannelOption)) return
    const nextChannel = next as ChannelOption
    const prevChannel = channelOptions.includes(prev as ChannelOption) ? (prev as ChannelOption) : null
    const currentProvider = structuredRule.value.provider.trim()
    const currentScene = structuredRule.value.templateScene.trim()
    if (!currentProvider || (prevChannel && currentProvider === defaultProviderByChannel[prevChannel])) {
      structuredRule.value.provider = defaultProviderByChannel[nextChannel]
    }
    if (!currentScene || (prevChannel && currentScene === defaultTemplateSceneByChannel[prevChannel])) {
      structuredRule.value.templateScene = defaultTemplateSceneByChannel[nextChannel]
    }
  }
)

watch(
  templateReferenceMode,
  (mode) => {
    if (mode === 'INLINE') {
      if (structuredRule.value.templateName) structuredRule.value.templateName = ''
      if (structuredRule.value.templateVersion) structuredRule.value.templateVersion = ''
      if (structuredRule.value.templateStrategy !== 'ACTIVE') structuredRule.value.templateStrategy = 'ACTIVE'
      if (structuredRule.value.templateCanaryVersion) structuredRule.value.templateCanaryVersion = ''
      return
    }
    if (mode === 'ACTIVE') {
      if (structuredRule.value.templateVersion) structuredRule.value.templateVersion = ''
      if (!structuredRule.value.templateStrategy) structuredRule.value.templateStrategy = 'ACTIVE'
      if (!structuredRule.value.templateName.trim() && hasTemplateOptions.value) {
        const first = templateNameOptions.value[0]
        if (first) structuredRule.value.templateName = first
      }
      return
    }
    if (!structuredRule.value.templateName.trim() && hasTemplateOptions.value) {
      const first = templateNameOptions.value[0]
      if (first) structuredRule.value.templateName = first
    }
  }
)

watch(
  () => structuredRule.value.templateName,
  (value) => {
    const normalized = String(value || '').trim()
    if (!normalized) {
      if (structuredRule.value.templateVersion) structuredRule.value.templateVersion = ''
      return
    }
    if (templateReferenceMode.value === 'ACTIVE') return
    if (!hasTemplateOptions.value) return
    if (!templateNameOptions.value.includes(normalized)) return
    if (!templateVersionOptions.value.includes(structuredRule.value.templateVersion.trim())) {
      structuredRule.value.templateVersion = ''
    }
  }
)

watch(
  () => structuredRule.value.templateStrategy,
  () => {
    if (structuredRule.value.templateStrategy !== 'CANARY') {
      if (structuredRule.value.templateCanaryVersion) structuredRule.value.templateCanaryVersion = ''
      return
    }
    if (structuredRule.value.templateVersion) structuredRule.value.templateVersion = ''
    if (!structuredRule.value.templateCanaryPercent || Number(structuredRule.value.templateCanaryPercent) <= 0) {
      structuredRule.value.templateCanaryPercent = 10
    }
  }
)

watch(
  structuredRule,
  () => {
    if (syncingFromJson) return
    syncingFromStructured = true
    form.value.ruleJson = JSON.stringify(buildRuleFromStructured(), null, 2)
    syncingFromStructured = false
  },
  { deep: true }
)

watch(
  () => form.value.ruleJson,
  (value) => {
    if (syncingFromStructured) return
    try {
      const parsed = JSON.parse(String(value || '').trim() || '{}')
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return
      syncingFromJson = true
      updateStructuredFromRule(parsed as Record<string, unknown>)
      syncingFromJson = false
    } catch {
      // 保留原有手写 JSON 体验，提交时统一校验
    }
  }
)

async function loadPromptTemplates() {
  if (!projectId.value) return
  templateLoadError.value = ''
  try {
    promptTemplates.value = await listNotificationPromptTemplates(projectId.value)
  } catch (error) {
    promptTemplates.value = []
    templateLoadError.value = error instanceof Error ? error.message : '加载模板失败'
  }
}

function governanceRowKey(row: PromptTemplateGovernanceItem) {
  return `${String(row.scene || '').trim()}::${String(row.name || '').trim()}`
}

async function loadGovernance() {
  if (!projectId.value) return
  governanceLoading.value = true
  governanceErrorMessage.value = ''
  try {
    const rows = await listPromptTemplateGovernance(projectId.value)
    governanceRows.value = rows
    const nextDrafts: Record<string, string> = {}
    for (const row of rows) {
      const key = governanceRowKey(row)
      nextDrafts[key] = rollbackDrafts.value[key] ?? ''
    }
    rollbackDrafts.value = nextDrafts
  } catch (error) {
    governanceRows.value = []
    governanceErrorMessage.value = error instanceof Error ? error.message : '加载模板治理失败'
  } finally {
    governanceLoading.value = false
  }
}

async function loadStrategyCenter() {
  if (!projectId.value) return
  strategyCenterLoading.value = true
  strategyCenterErrorMessage.value = ''
  try {
    strategyCenterRows.value = await listStrategyCenter(projectId.value)
  } catch (error) {
    strategyCenterRows.value = []
    strategyCenterErrorMessage.value = error instanceof Error ? error.message : '加载策略中心失败'
  } finally {
    strategyCenterLoading.value = false
  }
}

async function loadDiagnostics() {
  if (!projectId.value) return
  diagnosticsLoading.value = true
  diagnosticsErrorMessage.value = ''
  try {
    const [notificationDiagnostics, unifiedDiagnostics] = await Promise.all([
      getNotificationDiagnostics(projectId.value),
      getExternalIntegrationDiagnostics(projectId.value)
    ])
    diagnostics.value = notificationDiagnostics
    externalDiagnostics.value = unifiedDiagnostics
  } catch (error) {
    diagnostics.value = {
      summary: { status: 'READY', total: 0, blocking: 0, warnings: 0, ready: 0, failedDeliveries: 0 },
      checks: [],
      recentFailures: [],
      providerReadiness: []
    }
    externalDiagnostics.value = {
      generatedAt: null,
      summary: { status: 'READY', totalChecks: 0, blocking: 0, warnings: 0, ready: 0 },
      checks: [],
      issueLinks: [],
      nextActions: []
    }
    diagnosticsErrorMessage.value = error instanceof Error ? error.message : '加载联调诊断失败'
  } finally {
    diagnosticsLoading.value = false
  }
}

async function loadRules() {
  if (!projectId.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    rules.value = await listNotifications(projectId.value)
    if (!strategySimulatorForm.value.notificationId.trim() && rules.value.length > 0) {
      strategySimulatorForm.value.notificationId = rules.value[0].id
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载集成配置失败'
  } finally {
    loading.value = false
  }
}

function normalizeTimeText(value: NotificationDelivery['createdAt']) {
  if (value === null || value === undefined || value === '') return '-'
  const asNumber = typeof value === 'number' ? value : Number(value)
  const ms = Number.isFinite(asNumber) ? (asNumber > 1_000_000_000_000 ? asNumber : asNumber * 1000) : NaN
  const date = Number.isFinite(ms) ? new Date(ms) : new Date(String(value))
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString()
}

function normalizeDiagnosticsTimeText(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') return '-'
  const asNumber = typeof value === 'number' ? value : Number(value)
  const ms = Number.isFinite(asNumber) ? (asNumber > 1_000_000_000_000 ? asNumber : asNumber * 1000) : NaN
  const date = Number.isFinite(ms) ? new Date(ms) : new Date(String(value))
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString()
}

function diagnosticsStatusTagClass(status: string) {
  const normalized = String(status || '').trim().toUpperCase()
  if (normalized === 'BLOCKED' || normalized === 'BLOCKER') return 'border-[#FB2C36]/30 bg-[#FEF2F2] text-[#B91C1C]'
  if (normalized === 'WARN' || normalized === 'WARNING') return 'border-[#FACC15]/40 bg-[#FFFBEB] text-[#A16207]'
  return 'border-[#00A63E]/30 bg-[#F0FDF4] text-[#166534]'
}

function strategyRolloutWindowText(row: StrategyCenterRuleItem) {
  const rolloutSummary = row.rolloutScopeSummary
  if (!rolloutSummary || typeof rolloutSummary !== 'object' || Array.isArray(rolloutSummary)) return '-'
  const summary = rolloutSummary as Record<string, unknown>
  const rawTimeWindows = summary.timeWindows
  if (Array.isArray(rawTimeWindows)) {
    const total = rawTimeWindows.length
    let enabled = 0
    for (const item of rawTimeWindows) {
      if (!item || typeof item !== 'object' || Array.isArray(item)) continue
      const enabledRaw = (item as Record<string, unknown>).enabled
      if (!enabledRaw || String(enabledRaw).trim() === '' || Boolean(enabledRaw)) enabled += 1
    }
    return total > 0 ? `tw:${total} | enabled:${enabled}` : '-'
  }
  if (!rawTimeWindows || typeof rawTimeWindows !== 'object' || Array.isArray(rawTimeWindows)) return '-'
  const twSummary = rawTimeWindows as Record<string, unknown>
  const total = Number(twSummary.total)
  const enabled = Number(twSummary.enabled)
  const strategy = String(twSummary.conflictStrategy ?? '').trim()
  const parts: string[] = []
  if (Number.isFinite(total) && total > 0) parts.push(`tw:${total}`)
  if (Number.isFinite(enabled) && enabled >= 0) parts.push(`enabled:${enabled}`)
  if (strategy) parts.push(strategy)
  return parts.length > 0 ? parts.join(' | ') : '-'
}

function toNullableNumber(value: string) {
  const text = String(value || '').trim()
  if (!text) return null
  const parsed = Number(text)
  return Number.isFinite(parsed) ? parsed : null
}

function simulationFieldText(value: unknown) {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  return String(value)
}

function simulationListText(value: unknown) {
  if (!Array.isArray(value) || value.length === 0) return '-'
  return value
    .map((item) => {
      if (item && typeof item === 'object' && !Array.isArray(item)) {
        const record = item as Record<string, unknown>
        const id = String(record.id ?? record.windowId ?? record.candidateId ?? '').trim()
        const priority = record.priority ?? record.resolvedPriority
        const weight = record.weight ?? record.batchPercent
        const rawText = String(record.rawText ?? '').trim()
        const parts: string[] = []
        if (id) parts.push(`id:${id}`)
        if (priority !== null && priority !== undefined && String(priority).trim() !== '') parts.push(`p:${priority}`)
        if (weight !== null && weight !== undefined && String(weight).trim() !== '') parts.push(`w:${weight}`)
        if (parts.length > 0) return parts.join(' ')
        if (rawText && rawText !== '[object Object]') return rawText
        try {
          return JSON.stringify(record)
        } catch {
          return String(record)
        }
      }
      return String(item ?? '').trim()
    })
    .filter(Boolean)
    .join(' | ') || '-'
}

function formatSimulationRateText(hit: unknown, sample: unknown) {
  const hitNum = Number(hit)
  const sampleNum = Number(sample)
  if (!Number.isFinite(hitNum) || !Number.isFinite(sampleNum) || sampleNum <= 0) return '-'
  return `${Math.round((hitNum / sampleNum) * 100)}%`
}

function strategyCenterSimulationStatsText(row: StrategyCenterRuleItem) {
  const stats = row.simulationStats
  if (!stats) return '-'
  const sample = Number(stats.sampleCount)
  const hit = Number(stats.matchedCount)
  const topItems = Array.isArray(stats.scopeReasonTop) ? stats.scopeReasonTop : []
  const topReason = topItems
    .slice(0, 3)
    .map((item) => {
      const reason = String(item?.reason ?? '').trim()
      const count = Number(item?.count)
      if (!reason) return ''
      return Number.isFinite(count) ? `${reason}:${count}` : reason
    })
    .filter(Boolean)
    .join(', ')
  const rateText = formatSimulationRateText(hit, sample)
  const sampleText = Number.isFinite(sample) ? String(sample) : '-'
  const hitText = Number.isFinite(hit) ? String(hit) : '-'
  return `样本:${sampleText} / 命中:${hitText} / 命中率:${rateText} / Top:${topReason || '-'}`
}

function toggleBatchSimulationRowExpanded(key: number) {
  strategySimulationBatchExpandedKeys.value[key] = !strategySimulationBatchExpandedKeys.value[key]
}

function isBatchSimulationRowExpanded(key: number) {
  return Boolean(strategySimulationBatchExpandedKeys.value[key])
}

function exportStrategyCenterRows() {
  const payload = {
    filters: {
      channel: strategyCenterChannelFilter.value,
      topScopeReason: strategyCenterTopScopeReasonFilter.value,
      keyword: strategyCenterKeyword.value,
      sortBy: strategyCenterSortBy.value
    },
    rows: sortedStrategyCenterRows.value
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'strategy-center-export.json'
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

type StrategyCenterFilterSnapshot = {
  channel: string
  topScopeReason: string
  keyword: string
  sortBy: 'DEFAULT' | 'HIT_RATE_DESC' | 'SAMPLE_COUNT_DESC'
}

type StrategyCenterFilterSnapshotRecord = StrategyCenterFilterSnapshot & {
  id: string
  createdAt: string
  selectedCsvColumns: StrategyCenterCsvColumn[]
}

function toCsvCell(value: unknown) {
  const text = String(value ?? '')
  const escaped = text.replace(/"/g, '""')
  return `"${escaped}"`
}

function exportStrategyCenterRowsCsv() {
  const headers = selectedStrategyCenterCsvColumns.value.length
    ? selectedStrategyCenterCsvColumns.value
    : [...strategyCenterCsvColumns]
  const lines = [headers.join(',')]
  for (const row of sortedStrategyCenterRows.value) {
    const sampleCount = Number(row.simulationStats?.sampleCount)
    const matchedCount = Number(row.simulationStats?.matchedCount)
    const hitRate = formatSimulationRateText(matchedCount, sampleCount)
    const rowMap: Record<StrategyCenterCsvColumn, string> = {
      notificationId: row.notificationId || '',
      channel: row.channel || '',
      target: row.target || '',
      enabled: row.enabled ? 'true' : 'false',
      sampleCount: Number.isFinite(sampleCount) ? String(sampleCount) : '',
      matchedCount: Number.isFinite(matchedCount) ? String(matchedCount) : '',
      hitRate: hitRate === '-' ? '' : hitRate,
      topScopeReason: strategyCenterTopScopeReason(row) === '-' ? '' : strategyCenterTopScopeReason(row)
    }
    lines.push(headers.map((header) => toCsvCell(rowMap[header])).join(','))
  }
  const csvText = `\uFEFF${lines.join('\n')}`
  const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'strategy-center-export.csv'
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

function saveStrategyCenterFilterSnapshot() {
  const payload: StrategyCenterFilterSnapshotRecord = {
    id: `snapshot-${Date.now()}`,
    createdAt: new Date().toISOString(),
    channel: strategyCenterChannelFilter.value,
    topScopeReason: strategyCenterTopScopeReasonFilter.value,
    keyword: strategyCenterKeyword.value,
    sortBy: strategyCenterSortBy.value,
    selectedCsvColumns: selectedStrategyCenterCsvColumns.value.slice()
  }
  const next = [payload, ...strategyCenterFilterSnapshots.value].slice(0, 3)
  strategyCenterFilterSnapshots.value = next
  selectedStrategyCenterSnapshotId.value = payload.id
  localStorage.setItem(strategyCenterFilterSnapshotStorageKey, JSON.stringify(payload))
  localStorage.setItem(strategyCenterFilterSnapshotsStorageKey, JSON.stringify(next))
}

function restoreStrategyCenterFilterSnapshot() {
  if (selectedStrategyCenterSnapshotId.value) {
    const hasSelected = strategyCenterFilterSnapshots.value.some((item) => item.id === selectedStrategyCenterSnapshotId.value)
    if (hasSelected) {
      applyStrategyCenterFilterSnapshotById(selectedStrategyCenterSnapshotId.value)
      return
    }
  }
  const raw = localStorage.getItem(strategyCenterFilterSnapshotsStorageKey) || localStorage.getItem(strategyCenterFilterSnapshotStorageKey)
  if (!raw) return
  try {
    const parsed = JSON.parse(raw) as Partial<StrategyCenterFilterSnapshotRecord> | Array<Partial<StrategyCenterFilterSnapshotRecord>>
    const snapshot = Array.isArray(parsed) ? parsed[0] : parsed
    if (!snapshot) return
    applyStrategyCenterFilterSnapshot(snapshot)
  } catch {
    strategyCenterChannelFilter.value = 'ALL'
    strategyCenterTopScopeReasonFilter.value = 'ALL'
  }
}

function applyStrategyCenterFilterSnapshot(snapshot: Partial<StrategyCenterFilterSnapshotRecord>) {
  const channel = String(snapshot.channel || 'ALL')
  const topScopeReason = String(snapshot.topScopeReason || 'ALL')
  const keyword = String(snapshot.keyword || '')
  const sortBy = String(snapshot.sortBy || 'DEFAULT')
  strategyCenterChannelFilter.value =
    channel === 'ALL' || strategyCenterChannelOptions.value.includes(channel) ? channel : 'ALL'
  strategyCenterTopScopeReasonFilter.value =
    topScopeReason === 'ALL' || strategyCenterTopScopeReasonOptions.value.includes(topScopeReason)
      ? topScopeReason
      : 'ALL'
  strategyCenterKeyword.value = keyword
  strategyCenterSortBy.value =
    sortBy === 'HIT_RATE_DESC' || sortBy === 'SAMPLE_COUNT_DESC' || sortBy === 'DEFAULT' ? sortBy : 'DEFAULT'
  const selectedColumns = Array.isArray(snapshot.selectedCsvColumns)
    ? snapshot.selectedCsvColumns.filter((item): item is StrategyCenterCsvColumn =>
        strategyCenterCsvColumns.includes(item as StrategyCenterCsvColumn)
      )
    : []
  selectedStrategyCenterCsvColumns.value = selectedColumns.length ? selectedColumns : [...strategyCenterCsvColumns]
}

function loadStrategyCenterFilterSnapshots() {
  const raw = localStorage.getItem(strategyCenterFilterSnapshotsStorageKey)
  if (!raw) {
    strategyCenterFilterSnapshots.value = []
    return
  }
  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      strategyCenterFilterSnapshots.value = []
      return
    }
    const normalized = parsed
      .map((item) => normalizeStrategyCenterFilterSnapshot(item))
      .filter((item): item is StrategyCenterFilterSnapshotRecord => Boolean(item))
      .slice(0, 3)
    strategyCenterFilterSnapshots.value = normalized
    selectedStrategyCenterSnapshotId.value = normalized[0]?.id || ''
    localStorage.setItem(strategyCenterFilterSnapshotsStorageKey, JSON.stringify(normalized))
  } catch {
    strategyCenterFilterSnapshots.value = []
    selectedStrategyCenterSnapshotId.value = ''
  }
}

function normalizeStrategyCenterFilterSnapshot(raw: unknown): StrategyCenterFilterSnapshotRecord | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const item = raw as Record<string, unknown>
  const channel = String(item.channel || 'ALL')
  const topScopeReason = String(item.topScopeReason || 'ALL')
  const keyword = String(item.keyword || '')
  const sortByRaw = String(item.sortBy || 'DEFAULT')
  const sortBy: StrategyCenterFilterSnapshot['sortBy'] =
    sortByRaw === 'HIT_RATE_DESC' || sortByRaw === 'SAMPLE_COUNT_DESC' ? sortByRaw : 'DEFAULT'
  const selectedCsvColumns = Array.isArray(item.selectedCsvColumns)
    ? item.selectedCsvColumns.filter((column): column is StrategyCenterCsvColumn =>
        strategyCenterCsvColumns.includes(column as StrategyCenterCsvColumn)
      )
    : [...strategyCenterCsvColumns]
  return {
    id: String(item.id || `snapshot-${Date.now()}-${Math.random()}`),
    createdAt: String(item.createdAt || ''),
    channel,
    topScopeReason,
    keyword,
    sortBy,
    selectedCsvColumns: selectedCsvColumns.length ? selectedCsvColumns : [...strategyCenterCsvColumns]
  }
}

function applyStrategyCenterFilterSnapshotById(id: string) {
  const selected = strategyCenterFilterSnapshots.value.find((item) => item.id === id)
  if (!selected) return
  applyStrategyCenterFilterSnapshot(selected)
  selectedStrategyCenterSnapshotId.value = selected.id
  localStorage.setItem(strategyCenterFilterSnapshotStorageKey, JSON.stringify(selected))
}

function removeStrategyCenterFilterSnapshotById(id: string) {
  const next = strategyCenterFilterSnapshots.value.filter((item) => item.id !== id)
  strategyCenterFilterSnapshots.value = next
  if (selectedStrategyCenterSnapshotId.value === id) {
    selectedStrategyCenterSnapshotId.value = next[0]?.id || ''
  }
  localStorage.setItem(strategyCenterFilterSnapshotsStorageKey, JSON.stringify(next))
}

function strategyCenterSnapshotTimeText(value: string) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString()
}

function toggleStrategyCenterCsvColumn(column: StrategyCenterCsvColumn) {
  const selectedSet = new Set(selectedStrategyCenterCsvColumns.value)
  if (selectedSet.has(column)) {
    selectedSet.delete(column)
  } else {
    selectedSet.add(column)
  }
  selectedStrategyCenterCsvColumns.value = strategyCenterCsvColumns.filter((item) => selectedSet.has(item))
}

function selectAllStrategyCenterCsvColumns() {
  selectedStrategyCenterCsvColumns.value = [...strategyCenterCsvColumns]
}

function clearStrategyCenterCsvColumns() {
  selectedStrategyCenterCsvColumns.value = []
}

function normalizeConflictCandidateList(value: unknown) {
  if (!Array.isArray(value) || value.length === 0) return []
  return value.map((item, index) => {
    if (item && typeof item === 'object' && !Array.isArray(item)) {
      const record = item as Record<string, unknown>
      const id = String(record.id ?? record.windowId ?? record.candidateId ?? '').trim()
      const priority = record.priority ?? record.resolvedPriority ?? null
      const weight = record.weight ?? record.batchPercent ?? null
      const rawText = String(record.rawText ?? '').trim()
      let text = rawText && rawText !== '[object Object]' ? rawText : ''
      if (!text) {
        try {
          text = JSON.stringify(record)
        } catch {
          text = simulationFieldText(item)
        }
      }
      return { key: `${id || 'candidate'}-${index}`, id, priority, weight, text }
    }
    return {
      key: `candidate-${index}`,
      id: '',
      priority: null as unknown,
      weight: null as unknown,
      text: String(item ?? '').trim() || '-'
    }
  })
}

function simulationScopeDecisionSummary(value: unknown) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return '-'
  const record = value as Record<string, unknown>
  const selectedWindowId = simulationFieldText(record.selectedWindowId)
  const matchedWindowCount = simulationFieldText(record.matchedWindowCount)
  const reason = simulationFieldText(record.reason)
  return `selectedWindowId:${selectedWindowId} / matchedWindowCount:${matchedWindowCount} / reason:${reason}`
}

function parseSimulationBatchRunContexts() {
  const lines = String(strategySimulationBatchText.value || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
  if (lines.length === 0) {
    throw new Error('请至少输入一行 runContext JSON')
  }
  return lines.map((line, index) => {
    try {
      const parsed = JSON.parse(line)
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('必须是 JSON 对象')
      }
      return parsed as Record<string, unknown>
    } catch (error) {
      const reason = error instanceof Error ? error.message : '未知解析错误'
      throw new Error(`第 ${index + 1} 行 JSON 解析失败：${reason}`)
    }
  })
}

async function submitStrategySimulation() {
  if (!projectId.value) return
  const notificationId = String(strategySimulatorForm.value.notificationId || '').trim()
  if (!notificationId) {
    strategySimulationErrorMessage.value = '请选择 notificationId'
    strategySimulationResult.value = null
    return
  }
  strategySimulationLoading.value = true
  strategySimulationErrorMessage.value = ''
  strategySimulationResult.value = null
  try {
    const weekday = toNullableNumber(strategySimulatorForm.value.weekday)
    const hour = toNullableNumber(strategySimulatorForm.value.hour)
    const timezoneOffsetMinutes = toNullableNumber(strategySimulatorForm.value.timezoneOffsetMinutes)
    const seed = toNullableNumber(strategySimulatorForm.value.seed)
    const metaTags = parseCommaSeparatedTextCaseInsensitiveUnique(strategySimulatorForm.value.metaTagsText)
    strategySimulationResult.value = await simulateStrategyCenterRule(projectId.value, {
      notificationId,
      runContext: {
        envId: String(strategySimulatorForm.value.envId || '').trim() || undefined,
        triggerType: String(strategySimulatorForm.value.triggerType || '').trim() || undefined,
        metaTags: metaTags.length > 0 ? metaTags : undefined,
        layerValue: String(strategySimulatorForm.value.layerValue || '').trim() || undefined,
        weekday: weekday ?? undefined,
        hour: hour ?? undefined,
        timezoneOffsetMinutes: timezoneOffsetMinutes ?? undefined,
        seed: seed ?? undefined
      }
    })
  } catch (error) {
    strategySimulationErrorMessage.value = error instanceof Error ? error.message : '策略模拟失败'
  } finally {
    strategySimulationLoading.value = false
  }
}

async function submitStrategySimulationBatch() {
  if (!projectId.value) return
  const notificationId = String(strategySimulatorForm.value.notificationId || '').trim()
  if (!notificationId) {
    strategySimulationErrorMessage.value = '请选择 notificationId'
    strategySimulationBatchResults.value = []
    return
  }
  let runContexts: Record<string, unknown>[] = []
  try {
    runContexts = parseSimulationBatchRunContexts()
  } catch (error) {
    strategySimulationErrorMessage.value = error instanceof Error ? error.message : '批量 runContext 解析失败'
    strategySimulationBatchResults.value = []
    return
  }
  strategySimulationLoading.value = true
  strategySimulationErrorMessage.value = ''
  strategySimulationBatchResults.value = []
  strategySimulationBatchReasonFilter.value = 'ALL'
  strategySimulationBatchExpandedKeys.value = {}
  try {
    strategySimulationBatchResults.value = await simulateStrategyCenterRuleBatch(projectId.value, {
      notificationId,
      runContexts
    })
  } catch (error) {
    strategySimulationErrorMessage.value = error instanceof Error ? error.message : '批量策略模拟失败'
  } finally {
    strategySimulationLoading.value = false
  }
}

async function loadDeliveries() {
  if (!projectId.value) return
  deliveryLoading.value = true
  deliveryErrorMessage.value = ''
  try {
    const data = await listNotificationDeliveries(projectId.value, deliveryQuery.value)
    deliveryRows.value = data.items || []
    deliveryTotal.value = Number(data.total || 0)
    deliveryQuery.value.page = Number(data.page || deliveryQuery.value.page)
    deliveryQuery.value.pageSize = Number(data.pageSize || deliveryQuery.value.pageSize)
  } catch (error) {
    deliveryErrorMessage.value = error instanceof Error ? error.message : '加载投递记录失败'
  } finally {
    deliveryLoading.value = false
  }
}

async function retryDelivery(row: NotificationDelivery) {
  const ok = window.confirm(`确认重试投递 ${row.id} 吗？`)
  if (!ok) return
  deliveryErrorMessage.value = ''
  deliverySuccessMessage.value = ''
  deliveryRetryingId.value = row.id
  try {
    await retryNotificationDelivery(projectId.value, row.id)
    deliverySuccessMessage.value = '重试请求已提交'
    await loadDeliveries()
  } catch (error) {
    deliveryErrorMessage.value = error instanceof Error ? error.message : '重试失败'
  } finally {
    deliveryRetryingId.value = ''
  }
}

async function applyDeliveryFilters() {
  deliveryQuery.value.page = 1
  await loadDeliveries()
}

async function resetDeliveryFilters() {
  deliveryQuery.value.status = ''
  deliveryQuery.value.runId = ''
  deliveryQuery.value.page = 1
  await loadDeliveries()
}

async function goDeliveryPage(page: number) {
  const next = Math.min(Math.max(page, 1), deliveryTotalPages.value)
  if (next === deliveryQuery.value.page) return
  deliveryQuery.value.page = next
  await loadDeliveries()
}

async function changeDeliveryPageSize(size: number) {
  if (!Number.isFinite(size) || size <= 0) return
  deliveryQuery.value.pageSize = size
  deliveryQuery.value.page = 1
  await loadDeliveries()
}

async function onDeliveryPageSizeChange(event: Event) {
  const target = event.target as HTMLSelectElement | null
  if (!target) return
  await changeDeliveryPageSize(Number(target.value))
}

function deliveryStatusText(status: NotificationDelivery['status']) {
  const normalized = String(status || '').trim().toUpperCase()
  if (!normalized) return '-'
  return deliveryStatusLabels[normalized] ?? normalized
}

async function submit() {
  saveError.value = ''
  successMessage.value = ''
  saving.value = true
  try {
    const payload = buildPayload()
    if (mode.value === 'create') {
      const created = await createNotification(projectId.value, payload)
      await loadRules()
      await loadDiagnostics()
      applyRule(created)
      successMessage.value = '规则创建成功'
    } else {
      if (!selectedId.value) throw new Error('请选择要编辑的规则')
      const updated = await updateNotification(projectId.value, selectedId.value, payload)
      await loadRules()
      await loadDiagnostics()
      applyRule(updated)
      successMessage.value = '规则更新成功'
    }
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function submitRollback(row: PromptTemplateGovernanceItem) {
  const key = governanceRowKey(row)
  const targetVersion = String(rollbackDrafts.value[key] || '').trim()
  if (!targetVersion) {
    governanceErrorMessage.value = `请输入 ${row.scene} / ${row.name} 的 targetVersion`
    governanceSuccessMessage.value = ''
    return
  }
  const ok = window.confirm(`确认将 ${row.scene} / ${row.name} 回滚到版本 ${targetVersion} 吗？`)
  if (!ok) return
  governanceErrorMessage.value = ''
  governanceSuccessMessage.value = ''
  governanceRollingKey.value = key
  try {
    await rollbackPromptTemplate(projectId.value, {
      scene: row.scene,
      name: row.name,
      targetVersion
    })
    governanceSuccessMessage.value = `回滚成功：${row.scene} / ${row.name} -> ${targetVersion}`
    await loadGovernance()
  } catch (error) {
    governanceErrorMessage.value = error instanceof Error ? error.message : '回滚失败'
  } finally {
    governanceRollingKey.value = ''
  }
}

async function removeRule(rule: NotificationRule) {
  const ok = window.confirm(`确认删除规则「${rule.channel} -> ${rule.target}」吗？`)
  if (!ok) return
  saveError.value = ''
  successMessage.value = ''
  try {
    await deleteNotification(projectId.value, rule.id)
    if (selectedId.value === rule.id) startCreate()
    await loadRules()
    await loadDiagnostics()
    successMessage.value = '规则删除成功'
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : '删除失败'
  }
}

onMounted(async () => {
  loadStrategyCenterFilterSnapshots()
  startCreate()
  await Promise.all([loadRules(), loadDeliveries(), loadPromptTemplates(), loadGovernance(), loadStrategyCenter(), loadDiagnostics()])
})
</script>

<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-4 md:p-6">
    <div class="grid grid-cols-1 gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
      <section class="rounded-[12px] border border-black/10 bg-white p-4">
        <div class="flex items-center justify-between">
          <h2 class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">集成规则</h2>
          <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px]" @click="startCreate">新建规则</button>
        </div>

        <div v-if="loading" class="mt-4 text-[12px] text-[#717182]">加载中...</div>
        <div v-else-if="errorMessage" class="mt-4 rounded-[8px] border border-[#FB2C36]/30 bg-[#FEF2F2] p-2 text-[12px] text-[#B91C1C]">
          {{ errorMessage }}
        </div>
        <div v-else-if="rules.length === 0" class="mt-4 rounded-[8px] border border-dashed border-black/10 p-4 text-[12px] text-[#717182]">
          暂无规则，请先创建。
        </div>

        <div v-else class="mt-4 space-y-2">
          <div
            v-for="item in rules"
            :key="item.id"
            class="rounded-[8px] border p-3"
            :class="selectedId === item.id ? 'border-[#155DFC] bg-[#EFF6FF]' : 'border-black/10 bg-white'"
          >
            <div class="flex items-start justify-between gap-2">
              <button class="min-w-0 flex-1 text-left" @click="applyRule(item)">
                <div class="truncate text-[13px] font-medium text-[#0A0A0A]">{{ item.channel }} → {{ item.target }}</div>
                <div class="mt-1 text-[12px] text-[#717182]">enabled: {{ item.enabled ? 'true' : 'false' }}</div>
              </button>
              <button class="rounded-[6px] border border-[#FB2C36]/30 px-2 py-1 text-[11px] text-[#B91C1C]" @click="removeRule(item)">删除</button>
            </div>
          </div>
        </div>
      </section>

      <section class="rounded-[12px] border border-black/10 bg-white p-4">
        <h2 class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">
          {{ mode === 'create' ? '新建规则' : `编辑规则 · ${selectedRule?.channel || ''}` }}
        </h2>

        <div class="mt-4 grid grid-cols-1 gap-3">
          <label class="text-[12px] text-[#717182]">
            channel
            <select
              v-model="form.channel"
              class="mt-1 h-9 w-full rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none"
            >
              <option v-for="channel in channelOptions" :key="channel" :value="channel">{{ channel }}</option>
            </select>
          </label>

          <label class="text-[12px] text-[#717182]">
            target
            <input v-model="form.target" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
          </label>

          <label class="flex items-center gap-2 text-[12px] text-[#0A0A0A]">
            <input v-model="form.enabled" type="checkbox" class="h-4 w-4 accent-[#155DFC]" />
            enabled
          </label>

          <label class="text-[12px] text-[#717182]">
            rule (JSON 对象)
            <textarea v-model="form.ruleJson" rows="10" class="mt-1 w-full rounded-[8px] border border-black/10 p-3 text-[12px] text-[#0A0A0A] outline-none" />
          </label>

          <div class="rounded-[8px] border border-black/10 p-3">
            <div class="text-[12px] text-[#0A0A0A]">rule 结构化编辑</div>
            <div class="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
              <div class="md:col-span-2">
                <div class="text-[12px] text-[#717182]">events</div>
                <div class="mt-1 flex flex-wrap gap-3">
                  <label v-for="eventName in eventOptions" :key="eventName" class="flex items-center gap-1 text-[12px] text-[#0A0A0A]">
                    <input v-model="structuredRule.events" type="checkbox" :value="eventName" class="h-4 w-4 accent-[#155DFC]" />
                    {{ eventName }}
                  </label>
                </div>
              </div>

              <label class="text-[12px] text-[#717182]">
                timeoutSec
                <input
                  v-model.number="structuredRule.timeoutSec"
                  type="number"
                  min="0.1"
                  max="30"
                  step="0.1"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                />
              </label>

              <label class="text-[12px] text-[#717182]">
                maxRetries
                <input
                  v-model.number="structuredRule.maxRetries"
                  type="number"
                  min="1"
                  max="5"
                  step="1"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                />
              </label>

              <label class="text-[12px] text-[#717182]">
                provider
                <select
                  v-model="structuredRule.provider"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none"
                >
                  <option v-for="provider in providerOptions" :key="provider" :value="provider">{{ provider }}</option>
                </select>
              </label>

              <label class="text-[12px] text-[#717182]">
                templateScene
                <select
                  v-model="structuredRule.templateScene"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none"
                >
                  <option v-for="scene in templateSceneOptions" :key="scene" :value="scene">{{ scene }}</option>
                </select>
              </label>

              <label v-if="structuredRule.provider === 'DINGTALK'" class="text-[12px] text-[#717182] md:col-span-2">
                webhookUrl
                <input
                  v-model="structuredRule.webhookUrl"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                  placeholder="https://oapi.dingtalk.com/robot/send?access_token=***"
                />
              </label>

              <label v-if="structuredRule.provider === 'DINGTALK'" class="text-[12px] text-[#717182]">
                keyword
                <input
                  v-model="structuredRule.keyword"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                  placeholder="告警"
                />
              </label>

              <label class="text-[12px] text-[#717182] md:col-span-2">
                模板引用模式
                <select
                  v-model="templateReferenceMode"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none"
                >
                  <option value="INLINE">INLINE（内联 template）</option>
                  <option value="ACTIVE">ACTIVE（活动模板 templateName）</option>
                  <option value="PINNED_VERSION">PINNED_VERSION（固定版本 templateName + templateVersion）</option>
                </select>
              </label>

              <label class="text-[12px] text-[#717182] md:col-span-2">
                template
                <textarea
                  v-model="structuredRule.template"
                  rows="4"
                  class="mt-1 w-full rounded-[8px] border border-black/10 p-3 text-[12px] text-[#0A0A0A] outline-none"
                  :disabled="templateReferenceMode !== 'INLINE'"
                />
              </label>

              <label class="text-[12px] text-[#717182]">
                templateName
                <template v-if="hasTemplateOptions">
                  <select
                    v-model="structuredRule.templateName"
                    class="mt-1 h-9 w-full rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none"
                    :disabled="templateReferenceMode === 'INLINE'"
                  >
                    <option value="">请选择</option>
                    <option v-for="name in templateNameOptions" :key="name" :value="name">{{ name }}</option>
                  </select>
                </template>
                <template v-else>
                  <input
                    v-model="structuredRule.templateName"
                    class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                    :disabled="templateReferenceMode === 'INLINE'"
                  />
                </template>
              </label>

              <label class="text-[12px] text-[#717182]">
                templateVersion
                <template v-if="hasTemplateOptions && structuredRule.templateName.trim()">
                  <select
                    v-model="structuredRule.templateVersion"
                    class="mt-1 h-9 w-full rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none"
                    :disabled="templateReferenceMode !== 'PINNED_VERSION'"
                  >
                    <option value="">请选择</option>
                    <option v-for="version in templateVersionOptions" :key="version" :value="version">{{ version }}</option>
                  </select>
                </template>
                <template v-else>
                  <input
                    v-model="structuredRule.templateVersion"
                    class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                    :disabled="templateReferenceMode !== 'PINNED_VERSION'"
                  />
                </template>
              </label>

              <label v-if="templateReferenceMode !== 'INLINE'" class="text-[12px] text-[#717182] md:col-span-2">
                templateStrategy
                <select
                  v-model="structuredRule.templateStrategy"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none"
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="CANARY">CANARY</option>
                </select>
              </label>

              <label
                v-if="templateReferenceMode !== 'INLINE' && structuredRule.templateStrategy === 'CANARY'"
                class="text-[12px] text-[#717182]"
              >
                templateCanaryVersion
                <input
                  v-model="structuredRule.templateCanaryVersion"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                />
              </label>

              <label
                v-if="templateReferenceMode !== 'INLINE' && structuredRule.templateStrategy === 'CANARY'"
                class="text-[12px] text-[#717182]"
              >
                templateCanaryPercent
                <input
                  v-model.number="structuredRule.templateCanaryPercent"
                  type="number"
                  min="1"
                  max="100"
                  step="1"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                />
              </label>

              <div class="md:col-span-2 mt-1 border-t border-black/10 pt-3">
                <div class="text-[12px] text-[#0A0A0A]">多维灰度策略 (rolloutScope)</div>
              </div>

              <label class="text-[12px] text-[#717182] md:col-span-2">
                envIds（逗号分隔）
                <input
                  v-model="rolloutScopeEnvIdsText"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                  placeholder="env-a, env-b"
                />
              </label>

              <div class="md:col-span-2">
                <div class="text-[12px] text-[#717182]">triggerTypes</div>
                <div class="mt-1 flex flex-wrap gap-3">
                  <label
                    v-for="triggerType in rolloutTriggerTypeOptions"
                    :key="triggerType"
                    class="flex items-center gap-1 text-[12px] text-[#0A0A0A]"
                  >
                    <input
                      v-model="structuredRule.rolloutScopeTriggerTypes"
                      type="checkbox"
                      :value="triggerType"
                      class="h-4 w-4 accent-[#155DFC]"
                    />
                    {{ triggerType }}
                  </label>
                </div>
              </div>

              <label class="text-[12px] text-[#717182] md:col-span-2">
                metaTags（逗号分隔）
                <input
                  v-model="rolloutScopeMetaTagsText"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                  placeholder="regression, smoke"
                />
              </label>

              <label class="text-[12px] text-[#717182]">
                batchPercent
                <input
                  v-model.number="structuredRule.rolloutScopeBatchPercent"
                  type="number"
                  min="1"
                  max="100"
                  step="1"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                />
              </label>

              <label class="text-[12px] text-[#717182]">
                priority
                <input
                  v-model.number="structuredRule.rolloutScopePriority"
                  type="number"
                  min="1"
                  max="1000"
                  step="1"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                />
              </label>

              <label class="text-[12px] text-[#717182]">
                layerKey
                <input
                  v-model="structuredRule.rolloutScopeLayerKey"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                  placeholder="releaseRing"
                />
              </label>

              <label class="text-[12px] text-[#717182] md:col-span-2">
                layerValues（逗号分隔）
                <input
                  v-model="rolloutScopeLayerValuesText"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                  placeholder="canary, prod"
                />
              </label>

              <div class="md:col-span-2 mt-1 border-t border-black/10 pt-3">
                <div class="flex items-center justify-between gap-2">
                  <div class="text-[12px] text-[#0A0A0A]">timeWindows</div>
                  <button class="h-7 rounded-[8px] border border-black/10 px-2 text-[12px]" type="button" @click="addRolloutTimeWindow">
                    新增窗口
                  </button>
                </div>
                <div class="mt-2 space-y-2">
                  <div
                    v-for="(windowItem, index) in structuredRule.rolloutScopeTimeWindows"
                    :key="`${windowItem.id}-${index}`"
                    class="rounded-[8px] border border-black/10 p-3"
                  >
                    <div class="mb-2 flex items-center justify-between gap-2">
                      <div class="text-[12px] text-[#0A0A0A]">窗口 {{ index + 1 }}</div>
                      <button class="h-7 rounded-[8px] border border-[#FB2C36]/30 px-2 text-[11px] text-[#B91C1C]" type="button" @click="removeRolloutTimeWindow(index)">
                        删除
                      </button>
                    </div>
                    <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
                      <label class="text-[12px] text-[#717182]">
                        id
                        <input v-model="windowItem.id" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
                      </label>
                      <label class="flex items-center gap-2 text-[12px] text-[#0A0A0A]">
                        <input v-model="windowItem.enabled" type="checkbox" class="h-4 w-4 accent-[#155DFC]" />
                        enabled
                      </label>
                      <label class="text-[12px] text-[#717182]">
                        priority
                        <input v-model.number="windowItem.priority" type="number" min="1" max="1000" step="1" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
                      </label>
                      <label class="text-[12px] text-[#717182]">
                        weight
                        <input v-model.number="windowItem.weight" type="number" min="1" max="100" step="1" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
                      </label>
                      <label class="text-[12px] text-[#717182]">
                        batchPercent
                        <input v-model.number="windowItem.batchPercent" type="number" min="1" max="100" step="1" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
                      </label>
                      <label class="text-[12px] text-[#717182]">
                        timezoneOffsetMinutes
                        <input v-model.number="windowItem.timezoneOffsetMinutes" type="number" min="-720" max="840" step="1" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
                      </label>
                      <label class="text-[12px] text-[#717182]">
                        startHour
                        <input v-model.number="windowItem.startHour" type="number" min="0" max="23" step="1" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
                      </label>
                      <label class="text-[12px] text-[#717182]">
                        endHour
                        <input v-model.number="windowItem.endHour" type="number" min="0" max="23" step="1" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
                      </label>
                      <div class="md:col-span-2">
                        <div class="text-[12px] text-[#717182]">weekdays</div>
                        <div class="mt-1 flex flex-wrap gap-3">
                          <label
                            v-for="weekday in rolloutTimeWindowWeekdayOptions"
                            :key="weekday.value"
                            class="flex items-center gap-1 text-[12px] text-[#0A0A0A]"
                          >
                            <input
                              v-model="windowItem.weekdays"
                              type="checkbox"
                              :value="weekday.value"
                              class="h-4 w-4 accent-[#155DFC]"
                            />
                            {{ weekday.label }}
                          </label>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="md:col-span-2 mt-1 border-t border-black/10 pt-3">
                <div class="text-[12px] text-[#0A0A0A]">自动回滚</div>
              </div>

              <label class="flex items-center gap-2 text-[12px] text-[#0A0A0A] md:col-span-2">
                <input v-model="structuredRule.autoRollbackEnabled" type="checkbox" class="h-4 w-4 accent-[#155DFC]" />
                autoRollbackEnabled
              </label>

              <label class="text-[12px] text-[#717182]">
                autoRollbackFailureThreshold
                <input
                  v-model.number="structuredRule.autoRollbackFailureThreshold"
                  type="number"
                  min="1"
                  max="20"
                  step="1"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                />
              </label>

              <label class="text-[12px] text-[#717182]">
                autoRollbackWindowMinutes
                <input
                  v-model.number="structuredRule.autoRollbackWindowMinutes"
                  type="number"
                  min="1"
                  max="1440"
                  step="1"
                  class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
                />
              </label>

              <div
                v-if="templateLoadError"
                class="md:col-span-2 rounded-[8px] border border-[#FB2C36]/30 bg-[#FEF2F2] px-3 py-2 text-[12px] text-[#B91C1C]"
              >
                模板加载失败，已降级为手工输入：{{ templateLoadError }}
              </div>

              <div
                v-if="templateReferenceTip"
                class="md:col-span-2 rounded-[8px] border border-[#155DFC]/20 bg-[#EFF6FF] px-3 py-2 text-[12px] text-[#1D4ED8]"
              >
                {{ templateReferenceTip }}
              </div>

              <div class="md:col-span-2 rounded-[8px] border border-[#155DFC]/20 bg-[#EFF6FF] px-3 py-2 text-[12px] text-[#1D4ED8]">
                {{ templateSceneDefaultTip }}
              </div>
            </div>
          </div>
        </div>

        <div v-if="saveError" class="mt-4 rounded-[8px] border border-[#FB2C36]/30 bg-[#FEF2F2] p-2 text-[12px] text-[#B91C1C]">{{ saveError }}</div>
        <div v-if="successMessage" class="mt-4 rounded-[8px] border border-[#00A63E]/30 bg-[#F0FDF4] p-2 text-[12px] text-[#166534]">{{ successMessage }}</div>

        <div class="mt-4 flex items-center gap-2">
          <button
            class="h-9 rounded-[8px] bg-[#155DFC] px-4 text-[13px] font-medium text-white disabled:opacity-60"
            :disabled="saving"
            @click="submit"
          >
            {{ saving ? '保存中...' : mode === 'create' ? '创建规则' : '保存修改' }}
          </button>
          <button class="h-9 rounded-[8px] border border-black/10 px-4 text-[13px]" @click="startCreate">重置为新建</button>
        </div>
      </section>
    </div>

    <section id="integration-diagnostics" class="mt-4 rounded-[12px] border border-black/10 bg-white p-4">
      <div class="flex items-center justify-between gap-2">
        <h2 class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">联调诊断</h2>
        <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px]" :disabled="diagnosticsLoading" @click="loadDiagnostics">
          {{ diagnosticsLoading ? '刷新中...' : '刷新' }}
        </button>
      </div>
      <div v-if="diagnosticsErrorMessage" class="mt-3 rounded-[8px] border border-[#FB2C36]/30 bg-[#FEF2F2] p-2 text-[12px] text-[#B91C1C]">
        {{ diagnosticsErrorMessage }}
      </div>
      <div class="mt-3 rounded-[8px] border border-black/10 bg-[#FAFBFC] p-3">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div class="text-[13px] font-semibold text-[#0A0A0A]">统一联调总览</div>
            <div class="mt-1 text-[12px] text-[#717182]">
              总项: {{ externalDiagnostics.summary.totalChecks }} · 阻塞: {{ externalDiagnostics.summary.blocking }} · 告警: {{ externalDiagnostics.summary.warnings }} · 就绪: {{ externalDiagnostics.summary.ready }}
            </div>
          </div>
          <span class="rounded-[999px] border px-2 py-1 text-[12px]" :class="diagnosticsStatusTagClass(externalDiagnostics.summary.status)">
            {{ externalDiagnostics.summary.status }}
          </span>
        </div>
        <div class="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
          <div
            v-for="row in externalDiagnostics.checks.slice(0, 6) as ExternalIntegrationDiagnosticItem[]"
            :key="row.id"
            class="rounded-[8px] border border-black/10 bg-white px-3 py-2 text-[12px]"
          >
            <div class="flex items-center justify-between gap-2">
              <span class="truncate font-medium text-[#0A0A0A]">{{ row.title }}</span>
              <span class="shrink-0 rounded-[999px] border px-2 py-0.5" :class="diagnosticsStatusTagClass(row.status)">{{ row.status }}</span>
            </div>
            <div class="mt-1 truncate text-[#717182]" :title="row.detail">{{ row.provider }} · {{ row.category }} · {{ row.detail }}</div>
            <div v-if="row.missingFields.length" class="mt-1 text-[#A16207]">缺少: {{ row.missingFields.join('、') }}</div>
          </div>
          <div v-if="!diagnosticsLoading && externalDiagnostics.checks.length === 0" class="rounded-[8px] border border-black/10 bg-white px-3 py-2 text-[12px] text-[#717182]">
            暂无统一联调检查项
          </div>
        </div>
        <div v-if="externalDiagnostics.issueLinks.length" class="mt-3 flex flex-wrap gap-2 text-[12px]">
          <span class="text-[#717182]">Issue 回链</span>
          <span v-for="item in externalDiagnostics.issueLinks" :key="item.provider" class="rounded-[999px] border border-black/10 bg-white px-2 py-1 text-[#0A0A0A]">
            {{ item.provider }}: {{ item.total }}
          </span>
        </div>
        <div v-if="externalDiagnostics.nextActions.length" class="mt-3 flex flex-wrap gap-2 text-[12px]">
          <span class="text-[#717182]">下一步</span>
          <span v-for="item in externalDiagnostics.nextActions" :key="item" class="rounded-[999px] border border-black/10 bg-white px-2 py-1 text-[#0A0A0A]">
            {{ item }}
          </span>
        </div>
      </div>
      <div class="mt-3 flex flex-wrap items-center gap-2 text-[12px] text-[#0A0A0A]">
        <span class="rounded-[999px] border px-2 py-1" :class="diagnosticsStatusTagClass(diagnostics.summary.status)">{{ diagnostics.summary.status }}</span>
        <span>总检查: {{ diagnostics.summary.total }}</span>
        <span>阻塞: {{ diagnostics.summary.blocking }}</span>
        <span>告警: {{ diagnostics.summary.warnings }}</span>
        <span>就绪: {{ diagnostics.summary.ready }}</span>
        <span>最近失败: {{ diagnostics.summary.failedDeliveries }}</span>
      </div>
      <div class="mt-3 overflow-x-auto rounded-[8px] border border-black/10">
        <table class="min-w-full border-collapse text-left text-[12px] text-[#0A0A0A]">
          <thead class="bg-[rgba(236,236,240,0.45)] text-[#717182]">
            <tr>
              <th class="px-3 py-2 font-medium">level</th>
              <th class="px-3 py-2 font-medium">scope</th>
              <th class="px-3 py-2 font-medium">title</th>
              <th class="px-3 py-2 font-medium">detail</th>
              <th class="px-3 py-2 font-medium">recommendation</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="diagnosticsLoading"><td class="px-3 py-3 text-[#717182]" colspan="5">加载中...</td></tr>
            <tr v-else-if="diagnostics.checks.length === 0"><td class="px-3 py-3 text-[#717182]" colspan="5">暂无诊断检查项</td></tr>
            <tr v-for="row in diagnostics.checks as IntegrationDiagnosticsCheck[]" v-else :key="row.id" class="border-t border-black/10">
              <td class="px-3 py-2"><span class="rounded-[999px] border px-2 py-1" :class="diagnosticsStatusTagClass(row.level)">{{ row.level }}</span></td>
              <td class="px-3 py-2">{{ row.scope || '-' }}</td>
              <td class="px-3 py-2">{{ row.title || '-' }}</td>
              <td class="max-w-[360px] truncate px-3 py-2" :title="row.detail">{{ row.detail || '-' }}</td>
              <td class="max-w-[360px] truncate px-3 py-2" :title="row.recommendation">{{ row.recommendation || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="mt-3 overflow-x-auto rounded-[8px] border border-black/10">
        <table class="min-w-full border-collapse text-left text-[12px] text-[#0A0A0A]">
          <thead class="bg-[rgba(236,236,240,0.45)] text-[#717182]">
            <tr><th class="px-3 py-2 font-medium">provider</th><th class="px-3 py-2 font-medium">ready</th><th class="px-3 py-2 font-medium">notificationCount</th><th class="px-3 py-2 font-medium">reason</th></tr>
          </thead>
          <tbody>
            <tr v-if="diagnosticsLoading"><td class="px-3 py-3 text-[#717182]" colspan="4">加载中...</td></tr>
            <tr v-else-if="diagnostics.providerReadiness.length === 0"><td class="px-3 py-3 text-[#717182]" colspan="4">暂无 provider 就绪信息</td></tr>
            <tr v-for="row in diagnostics.providerReadiness as IntegrationDiagnosticsProviderReadiness[]" v-else :key="`${row.provider}-${row.reason}`" class="border-t border-black/10">
              <td class="px-3 py-2">{{ row.provider || '-' }}</td>
              <td class="px-3 py-2"><span class="rounded-[999px] border px-2 py-1" :class="diagnosticsStatusTagClass(row.ready ? 'READY' : 'BLOCKED')">{{ row.ready ? 'READY' : 'BLOCKED' }}</span></td>
              <td class="px-3 py-2">{{ row.notificationCount }}</td>
              <td class="max-w-[360px] truncate px-3 py-2" :title="row.reason">{{ row.reason || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="mt-3 overflow-x-auto rounded-[8px] border border-black/10">
        <table class="min-w-full border-collapse text-left text-[12px] text-[#0A0A0A]">
          <thead class="bg-[rgba(236,236,240,0.45)] text-[#717182]">
            <tr><th class="px-3 py-2 font-medium">notificationId</th><th class="px-3 py-2 font-medium">channel</th><th class="px-3 py-2 font-medium">provider</th><th class="px-3 py-2 font-medium">target</th><th class="px-3 py-2 font-medium">status</th><th class="px-3 py-2 font-medium">attempts</th><th class="px-3 py-2 font-medium">lastStatusCode</th><th class="px-3 py-2 font-medium">lastError</th><th class="px-3 py-2 font-medium">updatedAt</th></tr>
          </thead>
          <tbody>
            <tr v-if="diagnosticsLoading"><td class="px-3 py-3 text-[#717182]" colspan="9">加载中...</td></tr>
            <tr v-else-if="diagnostics.recentFailures.length === 0"><td class="px-3 py-3 text-[#717182]" colspan="9">暂无最近失败记录</td></tr>
            <tr v-for="row in diagnostics.recentFailures as IntegrationDiagnosticsRecentFailure[]" v-else :key="row.id" class="border-t border-black/10">
              <td class="px-3 py-2">{{ row.notificationId || '-' }}</td>
              <td class="px-3 py-2">{{ row.channel || '-' }}</td>
              <td class="px-3 py-2">{{ row.provider || '-' }}</td>
              <td class="max-w-[260px] truncate px-3 py-2" :title="row.target">{{ row.target || '-' }}</td>
              <td class="px-3 py-2">{{ row.status || '-' }}</td>
              <td class="px-3 py-2">{{ row.attempts }}</td>
              <td class="px-3 py-2">{{ row.lastStatusCode ?? '-' }}</td>
              <td class="max-w-[260px] truncate px-3 py-2" :title="row.lastError || ''">{{ row.lastError || '-' }}</td>
              <td class="px-3 py-2">{{ normalizeDiagnosticsTimeText(row.updatedAt) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="mt-4 rounded-[12px] border border-black/10 bg-white p-4">
      <div class="flex items-center justify-between gap-2">
        <h2 class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">策略中心</h2>
        <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px]" :disabled="strategyCenterLoading" @click="loadStrategyCenter">
          {{ strategyCenterLoading ? '刷新中...' : '刷新' }}
        </button>
      </div>

      <div
        v-if="strategyCenterErrorMessage"
        class="mt-3 rounded-[8px] border border-[#FB2C36]/30 bg-[#FEF2F2] p-2 text-[12px] text-[#B91C1C]"
      >
        {{ strategyCenterErrorMessage }}
      </div>

      <div class="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <label class="text-[12px] text-[#717182]">
          channel
          <select
            v-model="strategyCenterChannelFilter"
            class="mt-1 h-9 w-full rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none"
          >
            <option value="ALL">全部</option>
            <option v-for="item in strategyCenterChannelOptions" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label class="text-[12px] text-[#717182]">
          topScopeReason
          <select
            v-model="strategyCenterTopScopeReasonFilter"
            class="mt-1 h-9 w-full rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none"
          >
            <option value="ALL">全部</option>
            <option v-for="item in strategyCenterTopScopeReasonOptions" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label class="text-[12px] text-[#717182] xl:col-span-2">
          keyword（notificationId/target）
          <input
            v-model="strategyCenterKeyword"
            class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
            placeholder="输入关键字"
          />
        </label>
        <label class="text-[12px] text-[#717182]">
          sortBy
          <select
            v-model="strategyCenterSortBy"
            class="mt-1 h-9 w-full rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none"
          >
            <option value="DEFAULT">DEFAULT</option>
            <option value="HIT_RATE_DESC">HIT_RATE_DESC</option>
            <option value="SAMPLE_COUNT_DESC">SAMPLE_COUNT_DESC</option>
          </select>
        </label>
        <div class="relative flex flex-wrap items-end gap-2">
          <button class="h-9 rounded-[8px] border border-black/10 px-3 text-[12px]" @click="strategyCenterCsvSelectorOpen = !strategyCenterCsvSelectorOpen">
            CSV 列选择
          </button>
          <div
            v-if="strategyCenterCsvSelectorOpen"
            class="absolute left-0 top-11 z-20 min-w-[240px] rounded-[8px] border border-black/10 bg-white p-2 shadow-sm"
          >
            <div class="mb-2 flex items-center gap-2">
              <button class="h-7 rounded-[6px] border border-black/10 px-2 text-[12px]" @click="selectAllStrategyCenterCsvColumns">全选</button>
              <button class="h-7 rounded-[6px] border border-black/10 px-2 text-[12px]" @click="clearStrategyCenterCsvColumns">清空</button>
            </div>
            <label
              v-for="column in strategyCenterCsvColumns"
              :key="`csv-column-${column}`"
              class="mb-1 flex cursor-pointer items-center gap-2 text-[12px] text-[#0A0A0A]"
            >
              <input
                type="checkbox"
                role="menuitemcheckbox"
                :aria-label="column"
                :checked="selectedStrategyCenterCsvColumns.includes(column)"
                @change="toggleStrategyCenterCsvColumn(column)"
              />
              <span>{{ column }}</span>
            </label>
          </div>
          <button class="h-9 rounded-[8px] border border-black/10 px-3 text-[12px]" @click="exportStrategyCenterRows">
            导出当前筛选 JSON
          </button>
          <button class="h-9 rounded-[8px] border border-black/10 px-3 text-[12px]" @click="exportStrategyCenterRowsCsv">
            导出当前筛选 CSV
          </button>
          <button class="h-9 rounded-[8px] border border-black/10 px-3 text-[12px]" @click="saveStrategyCenterFilterSnapshot">
            保存快照
          </button>
          <button class="h-9 rounded-[8px] border border-black/10 px-3 text-[12px]" @click="restoreStrategyCenterFilterSnapshot">
            回填快照
          </button>
          <button
            class="h-9 rounded-[8px] border border-black/10 px-3 text-[12px]"
            :disabled="!selectedStrategyCenterSnapshotId"
            @click="removeStrategyCenterFilterSnapshotById(selectedStrategyCenterSnapshotId)"
          >
            删除快照
          </button>
          <select
            v-model="selectedStrategyCenterSnapshotId"
            class="h-9 min-w-[260px] rounded-[8px] border border-black/10 bg-white px-3 text-[12px] text-[#0A0A0A] outline-none"
          >
            <option value="">选择快照（最新3条）</option>
            <option
              v-for="snapshot in strategyCenterFilterSnapshots"
              :key="snapshot.id"
              :value="snapshot.id"
            >
              {{ `${strategyCenterSnapshotTimeText(snapshot.createdAt)} | ${snapshot.channel} | ${snapshot.topScopeReason} | ${snapshot.keyword || '-'}` }}
            </option>
          </select>
        </div>
      </div>

      <div class="mt-3 flex flex-wrap items-center gap-4 text-[12px] text-[#0A0A0A]">
        <span>总规则数: {{ strategyCenterSummary.total }}</span>
        <span>启用数: {{ strategyCenterSummary.enabled }}</span>
        <span>含 simulationStats: {{ strategyCenterSummary.withSimulationStats }}</span>
      </div>

      <div class="mt-3 overflow-x-auto rounded-[8px] border border-black/10">
        <table class="min-w-full border-collapse text-left text-[12px] text-[#0A0A0A]">
          <thead class="bg-[rgba(236,236,240,0.45)] text-[#717182]">
            <tr>
              <th class="px-3 py-2 font-medium">notificationId</th>
              <th class="px-3 py-2 font-medium">channel</th>
              <th class="px-3 py-2 font-medium">target</th>
              <th class="px-3 py-2 font-medium">enabled</th>
              <th class="px-3 py-2 font-medium">策略摘要</th>
              <th class="px-3 py-2 font-medium">灰度窗口</th>
              <th class="px-3 py-2 font-medium">最近投递</th>
              <th class="px-3 py-2 font-medium">投递统计(S/F/Q)</th>
              <th class="px-3 py-2 font-medium">过滤原因统计</th>
              <th class="px-3 py-2 font-medium">simulationStats</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="strategyCenterLoading">
              <td class="px-3 py-3 text-[#717182]" colspan="10">加载中...</td>
            </tr>
            <tr v-else-if="sortedStrategyCenterRows.length === 0">
              <td class="px-3 py-3 text-[#717182]" colspan="10">暂无策略中心数据</td>
            </tr>
            <tr v-for="row in sortedStrategyCenterRows" v-else :key="row.notificationId || `${row.channel}-${row.target}`" class="border-t border-black/10">
              <td class="max-w-[240px] truncate px-3 py-2" :title="row.notificationId || ''">{{ row.notificationId || '-' }}</td>
              <td class="px-3 py-2">{{ row.channel || '-' }}</td>
              <td class="max-w-[220px] truncate px-3 py-2" :title="row.target || ''">{{ row.target || '-' }}</td>
              <td class="px-3 py-2">{{ row.enabled ? 'true' : 'false' }}</td>
              <td class="max-w-[440px] truncate px-3 py-2" :title="row.strategySummary || ''">{{ row.strategySummary || '-' }}</td>
              <td class="max-w-[280px] truncate px-3 py-2" :title="strategyRolloutWindowText(row)">{{ strategyRolloutWindowText(row) }}</td>
              <td class="px-3 py-2">
                {{ normalizeTimeText(row.deliveryStats.lastDeliveryAt) }}
                <span class="text-[#717182]"> / {{ row.deliveryStats.lastStatus || '-' }}</span>
              </td>
              <td class="px-3 py-2">{{ row.deliveryStats.sent }} / {{ row.deliveryStats.failed }} / {{ row.deliveryStats.queued }}</td>
              <td class="px-3 py-2">
                {{ row.filterReasonStats.scopeReason }} / {{ row.filterReasonStats.eventFiltered }} /
                {{ row.filterReasonStats.unsupportedProvider }} / {{ row.filterReasonStats.templateNotFound }}
              </td>
              <td class="max-w-[320px] truncate px-3 py-2" :title="strategyCenterSimulationStatsText(row)">{{ strategyCenterSimulationStatsText(row) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="mt-4 rounded-[12px] border border-black/10 bg-white p-4">
      <div class="flex items-center justify-between gap-2">
        <h2 class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">策略模拟器</h2>
        <div class="flex items-center gap-2">
          <button
            class="h-8 rounded-[8px] bg-[#155DFC] px-3 text-[12px] font-medium text-white disabled:opacity-60"
            :disabled="strategySimulationLoading"
            @click="submitStrategySimulation"
          >
            {{ strategySimulationLoading ? '模拟中...' : '模拟策略' }}
          </button>
          <button
            class="h-8 rounded-[8px] border border-[#155DFC]/40 px-3 text-[12px] font-medium text-[#155DFC] disabled:opacity-60"
            :disabled="strategySimulationLoading"
            @click="submitStrategySimulationBatch"
          >
            {{ strategySimulationLoading ? '模拟中...' : '批量模拟' }}
          </button>
        </div>
      </div>

      <div class="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <label class="text-[12px] text-[#717182]">
          notificationId
          <select
            v-model="strategySimulatorForm.notificationId"
            class="mt-1 h-9 w-full rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none"
          >
            <option value="">请选择</option>
            <option v-for="item in rules" :key="item.id" :value="item.id">
              {{ item.id }}
            </option>
          </select>
        </label>

        <label class="text-[12px] text-[#717182]">
          envId
          <input v-model="strategySimulatorForm.envId" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
        </label>
        <label class="text-[12px] text-[#717182]">
          triggerType
          <input v-model="strategySimulatorForm.triggerType" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
        </label>
        <label class="text-[12px] text-[#717182]">
          metaTags（逗号分隔）
          <input v-model="strategySimulatorForm.metaTagsText" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
        </label>
        <label class="text-[12px] text-[#717182]">
          layerValue
          <input v-model="strategySimulatorForm.layerValue" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
        </label>
        <label class="text-[12px] text-[#717182]">
          weekday
          <input v-model="strategySimulatorForm.weekday" type="number" min="1" max="7" step="1" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
        </label>
        <label class="text-[12px] text-[#717182]">
          hour
          <input v-model="strategySimulatorForm.hour" type="number" min="0" max="23" step="1" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
        </label>
        <label class="text-[12px] text-[#717182]">
          timezoneOffsetMinutes
          <input v-model="strategySimulatorForm.timezoneOffsetMinutes" type="number" min="-720" max="840" step="1" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
        </label>
        <label class="text-[12px] text-[#717182]">
          seed
          <input v-model="strategySimulatorForm.seed" type="number" step="1" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
        </label>
      </div>

      <div
        v-if="strategySimulationErrorMessage"
        class="mt-3 rounded-[8px] border border-[#FB2C36]/30 bg-[#FEF2F2] p-2 text-[12px] text-[#B91C1C]"
      >
        {{ strategySimulationErrorMessage }}
      </div>

      <div class="mt-3 overflow-x-auto rounded-[8px] border border-black/10">
        <table class="min-w-full border-collapse text-left text-[12px] text-[#0A0A0A]">
          <thead class="bg-[rgba(236,236,240,0.45)] text-[#717182]">
            <tr>
              <th class="px-3 py-2 font-medium">matched</th>
              <th class="px-3 py-2 font-medium">scopeReason</th>
              <th class="px-3 py-2 font-medium">selectedWindowId</th>
              <th class="px-3 py-2 font-medium">matchedWindowCount</th>
              <th class="px-3 py-2 font-medium">reason</th>
              <th class="px-3 py-2 font-medium">resolvedBatchPercent</th>
              <th class="px-3 py-2 font-medium">resolvedPriority</th>
              <th class="px-3 py-2 font-medium">resolvedLayer</th>
              <th class="px-3 py-2 font-medium">resolvedTimeWindow</th>
              <th class="px-3 py-2 font-medium">explanations</th>
              <th class="px-3 py-2 font-medium">conflictCandidates</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="strategySimulationLoading">
              <td class="px-3 py-3 text-[#717182]" colspan="11">模拟中...</td>
            </tr>
            <tr v-else-if="!strategySimulationResult">
              <td class="px-3 py-3 text-[#717182]" colspan="11">暂无模拟结果</td>
            </tr>
            <tr v-else class="border-t border-black/10">
              <td class="px-3 py-2">{{ simulationFieldText(strategySimulationResult.matched) }}</td>
              <td class="px-3 py-2">{{ simulationFieldText(strategySimulationResult.scopeReason) }}</td>
              <td class="px-3 py-2">{{ simulationFieldText(strategySimulationResult.selectedWindowId) }}</td>
              <td class="px-3 py-2">{{ simulationFieldText(strategySimulationResult.matchedWindowCount) }}</td>
              <td class="px-3 py-2">{{ simulationFieldText(strategySimulationResult.reason) }}</td>
              <td class="px-3 py-2">{{ simulationFieldText(strategySimulationResult.resolvedBatchPercent) }}</td>
              <td class="px-3 py-2">{{ simulationFieldText(strategySimulationResult.resolvedPriority) }}</td>
              <td class="px-3 py-2">{{ simulationFieldText(strategySimulationResult.resolvedLayer) }}</td>
              <td class="px-3 py-2">{{ simulationFieldText(strategySimulationResult.resolvedTimeWindow) }}</td>
              <td class="max-w-[280px] truncate px-3 py-2" :title="simulationListText(strategySimulationResult.explanations)">
                {{ simulationListText(strategySimulationResult.explanations) }}
              </td>
              <td class="max-w-[280px] truncate px-3 py-2" :title="simulationListText(strategySimulationResult.conflictCandidates)">
                {{ simulationListText(strategySimulationResult.conflictCandidates) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-4 rounded-[8px] border border-black/10 p-3">
        <label class="block text-[12px] text-[#717182]">
          批量回放 runContext（JSON 行，每行一个对象）
          <textarea
            v-model="strategySimulationBatchText"
            class="mt-1 h-32 w-full rounded-[8px] border border-black/10 px-3 py-2 text-[12px] text-[#0A0A0A] outline-none"
            placeholder='{"envId":"prod","triggerType":"CRON","hour":9}'
          />
        </label>
      </div>

      <div class="mt-3 flex flex-wrap gap-4 text-[12px] text-[#0A0A0A]">
        <span>批量样本: {{ strategySimulationBatchSummary.total }}</span>
        <span>命中: {{ strategySimulationBatchSummary.matched }}</span>
        <span>未命中: {{ strategySimulationBatchSummary.unmatched }}</span>
        <span>命中率: {{ strategySimulationBatchSummary.hitRateText }}</span>
        <span class="max-w-[420px] truncate" :title="strategySimulationBatchSummary.reasonBreakdown || ''">
          scopeReason 分布: {{ strategySimulationBatchSummary.reasonBreakdown || '-' }}
        </span>
      </div>
      <div class="mt-2 flex flex-wrap items-center gap-2 text-[12px]">
        <button
          class="h-7 rounded-[999px] border px-3"
          :class="strategySimulationBatchReasonFilter === 'ALL' ? 'border-[#155DFC] bg-[#EFF6FF] text-[#155DFC]' : 'border-black/10 text-[#717182]'"
          @click="strategySimulationBatchReasonFilter = 'ALL'"
        >
          全部 ({{ strategySimulationBatchResults.length }})
        </button>
        <button
          v-for="item in strategySimulationBatchReasonOptions"
          :key="item.reason"
          class="h-7 rounded-[999px] border px-3"
          :class="strategySimulationBatchReasonFilter === item.reason ? 'border-[#155DFC] bg-[#EFF6FF] text-[#155DFC]' : 'border-black/10 text-[#717182]'"
          @click="strategySimulationBatchReasonFilter = item.reason"
        >
          {{ item.reason }} ({{ item.count }})
        </button>
      </div>

      <div class="mt-3 overflow-x-auto rounded-[8px] border border-black/10">
        <table class="min-w-full border-collapse text-left text-[12px] text-[#0A0A0A]">
          <thead class="bg-[rgba(236,236,240,0.45)] text-[#717182]">
            <tr>
              <th class="px-3 py-2 font-medium">runContext</th>
              <th class="px-3 py-2 font-medium">matched</th>
              <th class="px-3 py-2 font-medium">scopeReason</th>
              <th class="px-3 py-2 font-medium">selectedWindowId</th>
              <th class="px-3 py-2 font-medium">matchedWindowCount</th>
              <th class="px-3 py-2 font-medium">resolvedBatchPercent</th>
              <th class="px-3 py-2 font-medium">explanations</th>
              <th class="px-3 py-2 font-medium">conflictCandidates</th>
              <th class="px-3 py-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="strategySimulationLoading">
              <td class="px-3 py-3 text-[#717182]" colspan="9">批量模拟中...</td>
            </tr>
            <tr v-else-if="filteredStrategySimulationBatchRows.length === 0">
              <td class="px-3 py-3 text-[#717182]" colspan="9">暂无批量回放结果</td>
            </tr>
            <template v-for="{ row, index } in filteredStrategySimulationBatchRows" :key="index">
              <tr class="border-t border-black/10">
                <td class="max-w-[280px] truncate px-3 py-2" :title="simulationFieldText(row.runContext)">
                  {{ simulationFieldText(row.runContext) }}
                </td>
                <td class="px-3 py-2">{{ simulationFieldText(row.matched) }}</td>
                <td class="px-3 py-2">{{ simulationFieldText(row.scopeReason) }}</td>
                <td class="px-3 py-2">{{ simulationFieldText(row.selectedWindowId) }}</td>
                <td class="px-3 py-2">{{ simulationFieldText(row.matchedWindowCount) }}</td>
                <td class="px-3 py-2">{{ simulationFieldText(row.resolvedBatchPercent) }}</td>
                <td class="max-w-[280px] truncate px-3 py-2" :title="simulationListText(row.explanations)">{{ simulationListText(row.explanations) }}</td>
                <td class="max-w-[320px] px-3 py-2">
                  <div v-if="normalizeConflictCandidateList(row.conflictCandidates).length === 0" class="text-[#717182]">-</div>
                  <div v-else class="flex flex-wrap gap-1">
                    <span
                      v-for="candidate in normalizeConflictCandidateList(row.conflictCandidates).slice(0, 2)"
                      :key="candidate.key"
                      class="inline-flex items-center gap-1 rounded-[999px] border border-black/10 bg-[#F8F9FB] px-2 py-1 text-[11px] text-[#0A0A0A]"
                    >
                      <span>{{ candidate.id || '-' }}</span>
                      <span class="text-[#717182]">P:{{ simulationFieldText(candidate.priority) }}</span>
                      <span class="text-[#717182]">W:{{ simulationFieldText(candidate.weight) }}</span>
                    </span>
                    <span v-if="normalizeConflictCandidateList(row.conflictCandidates).length > 2" class="text-[#717182]">
                      +{{ normalizeConflictCandidateList(row.conflictCandidates).length - 2 }}
                    </span>
                  </div>
                </td>
                <td class="px-3 py-2">
                  <button class="rounded-[6px] border border-black/10 px-2 py-1 text-[11px]" @click="toggleBatchSimulationRowExpanded(index)">
                    {{ isBatchSimulationRowExpanded(index) ? '收起详情' : '展开详情' }}
                  </button>
                </td>
              </tr>
              <tr v-if="isBatchSimulationRowExpanded(index)" class="border-t border-black/10 bg-[rgba(236,236,240,0.18)]">
                <td colspan="9" class="px-3 py-3">
                  <div class="grid grid-cols-1 gap-3 xl:grid-cols-2">
                    <div>
                      <div class="mb-1 text-[12px] font-medium text-[#0A0A0A]">scopeDecision</div>
                      <div class="text-[12px] text-[#0A0A0A]" :title="simulationScopeDecisionSummary(row.scopeDecision)">
                        {{ simulationScopeDecisionSummary(row.scopeDecision) }}
                      </div>
                    </div>
                    <div>
                      <div class="mb-1 text-[12px] font-medium text-[#0A0A0A]">explanations</div>
                      <ul v-if="Array.isArray(row.explanations) && row.explanations.length > 0" class="list-disc pl-5 text-[12px] text-[#0A0A0A]">
                        <li v-for="(item, itemIdx) in row.explanations" :key="`exp-${index}-${itemIdx}`">{{ simulationFieldText(item) }}</li>
                      </ul>
                      <div v-else class="text-[12px] text-[#717182]">-</div>
                    </div>
                    <div>
                      <div class="mb-1 text-[12px] font-medium text-[#0A0A0A]">conflictCandidates</div>
                      <ul v-if="normalizeConflictCandidateList(row.conflictCandidates).length > 0" class="space-y-1 text-[12px]">
                        <li
                          v-for="candidate in normalizeConflictCandidateList(row.conflictCandidates)"
                          :key="`${candidate.key}-detail`"
                          class="rounded-[8px] border border-black/10 bg-white px-2 py-1"
                        >
                          <div class="flex flex-wrap items-center gap-1">
                            <span class="rounded-[999px] bg-[#F3F4F6] px-2 py-[2px] text-[11px] text-[#0A0A0A]">id: {{ candidate.id || '-' }}</span>
                            <span class="rounded-[999px] bg-[#EFF6FF] px-2 py-[2px] text-[11px] text-[#155DFC]">priority: {{ simulationFieldText(candidate.priority) }}</span>
                            <span class="rounded-[999px] bg-[#F0FDF4] px-2 py-[2px] text-[11px] text-[#166534]">weight: {{ simulationFieldText(candidate.weight) }}</span>
                          </div>
                          <div class="mt-1 break-all text-[#717182]">{{ candidate.text }}</div>
                        </li>
                      </ul>
                      <div v-else class="text-[12px] text-[#717182]">-</div>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </section>

    <section class="mt-4 rounded-[12px] border border-black/10 bg-white p-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h2 class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">投递治理</h2>
        <div class="flex flex-wrap items-end gap-2">
          <label class="text-[12px] text-[#717182]">
            status
            <select
              v-model="deliveryQuery.status"
              class="mt-1 h-9 min-w-[120px] rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none"
            >
              <option value="">全部</option>
              <option v-for="status in deliveryStatusOptions" :key="status.value" :value="status.value">{{ status.label }}</option>
            </select>
          </label>
          <label class="text-[12px] text-[#717182]">
            runId
            <input
              v-model="deliveryQuery.runId"
              class="mt-1 h-9 min-w-[220px] rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none"
            />
          </label>
          <button class="h-9 rounded-[8px] bg-[#155DFC] px-3 text-[12px] font-medium text-white" @click="applyDeliveryFilters">筛选</button>
          <button class="h-9 rounded-[8px] border border-black/10 px-3 text-[12px]" @click="resetDeliveryFilters">重置</button>
        </div>
      </div>

      <div v-if="deliveryErrorMessage" class="mt-3 rounded-[8px] border border-[#FB2C36]/30 bg-[#FEF2F2] p-2 text-[12px] text-[#B91C1C]">
        {{ deliveryErrorMessage }}
      </div>
      <div v-if="deliverySuccessMessage" class="mt-3 rounded-[8px] border border-[#00A63E]/30 bg-[#F0FDF4] p-2 text-[12px] text-[#166534]">
        {{ deliverySuccessMessage }}
      </div>

      <div class="mt-3 overflow-x-auto rounded-[8px] border border-black/10">
        <table class="min-w-full border-collapse text-left text-[12px] text-[#0A0A0A]">
          <thead class="bg-[rgba(236,236,240,0.45)] text-[#717182]">
            <tr>
              <th class="px-3 py-2 font-medium">status</th>
              <th class="px-3 py-2 font-medium">notificationId</th>
              <th class="px-3 py-2 font-medium">runId</th>
              <th class="px-3 py-2 font-medium">attempts</th>
              <th class="px-3 py-2 font-medium">statusCode</th>
              <th class="px-3 py-2 font-medium">durationMs</th>
              <th class="px-3 py-2 font-medium">error</th>
              <th class="px-3 py-2 font-medium">createdAt</th>
              <th class="px-3 py-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="deliveryLoading">
              <td class="px-3 py-3 text-[#717182]" colspan="9">加载中...</td>
            </tr>
            <tr v-else-if="deliveryRows.length === 0">
              <td class="px-3 py-3 text-[#717182]" colspan="9">暂无投递记录</td>
            </tr>
            <tr v-for="row in deliveryRows" v-else :key="row.id" class="border-t border-black/10">
              <td class="px-3 py-2">{{ deliveryStatusText(row.status) }}</td>
              <td class="max-w-[220px] truncate px-3 py-2" :title="row.notificationId">{{ row.notificationId || '-' }}</td>
              <td class="max-w-[220px] truncate px-3 py-2" :title="row.runId">{{ row.runId || '-' }}</td>
              <td class="px-3 py-2">{{ row.attempts ?? '-' }}</td>
              <td class="px-3 py-2">{{ row.statusCode ?? '-' }}</td>
              <td class="px-3 py-2">{{ row.durationMs ?? '-' }}</td>
              <td class="max-w-[260px] truncate px-3 py-2" :title="row.error || ''">{{ row.error || '-' }}</td>
              <td class="px-3 py-2">{{ normalizeTimeText(row.createdAt) }}</td>
              <td class="px-3 py-2">
                <button
                  class="rounded-[6px] border border-[#155DFC]/30 px-2 py-1 text-[11px] text-[#155DFC] disabled:opacity-60"
                  :disabled="deliveryRetryingId === row.id"
                  @click="retryDelivery(row)"
                >
                  {{ deliveryRetryingId === row.id ? '重试中...' : '重试' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-3 flex flex-wrap items-center justify-between gap-2 text-[12px] text-[#717182]">
        <div>共 {{ deliveryTotal }} 条</div>
        <div class="flex items-center gap-2">
          <label class="flex items-center gap-1">
            pageSize
            <select
              :value="String(deliveryQuery.pageSize)"
              class="h-8 rounded-[8px] border border-black/10 bg-white px-2 text-[12px] text-[#0A0A0A] outline-none"
              @change="onDeliveryPageSizeChange"
            >
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="50">50</option>
            </select>
          </label>
          <button class="h-8 rounded-[8px] border border-black/10 px-3" :disabled="deliveryQuery.page <= 1" @click="goDeliveryPage(deliveryQuery.page - 1)">
            上一页
          </button>
          <span class="text-[#0A0A0A]">{{ deliveryQuery.page }} / {{ deliveryTotalPages }}</span>
          <button
            class="h-8 rounded-[8px] border border-black/10 px-3"
            :disabled="deliveryQuery.page >= deliveryTotalPages"
            @click="goDeliveryPage(deliveryQuery.page + 1)"
          >
            下一页
          </button>
        </div>
      </div>
    </section>

    <section class="mt-4 rounded-[12px] border border-black/10 bg-white p-4">
      <div class="flex items-center justify-between gap-2">
        <h2 class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">模板治理（单活）</h2>
        <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px]" :disabled="governanceLoading" @click="loadGovernance">
          {{ governanceLoading ? '刷新中...' : '刷新' }}
        </button>
      </div>

      <div v-if="governanceErrorMessage" class="mt-3 rounded-[8px] border border-[#FB2C36]/30 bg-[#FEF2F2] p-2 text-[12px] text-[#B91C1C]">
        {{ governanceErrorMessage }}
      </div>
      <div v-if="governanceSuccessMessage" class="mt-3 rounded-[8px] border border-[#00A63E]/30 bg-[#F0FDF4] p-2 text-[12px] text-[#166534]">
        {{ governanceSuccessMessage }}
      </div>

      <div class="mt-3 overflow-x-auto rounded-[8px] border border-black/10">
        <table class="min-w-full border-collapse text-left text-[12px] text-[#0A0A0A]">
          <thead class="bg-[rgba(236,236,240,0.45)] text-[#717182]">
            <tr>
              <th class="px-3 py-2 font-medium">scene</th>
              <th class="px-3 py-2 font-medium">name</th>
              <th class="px-3 py-2 font-medium">activeVersion</th>
              <th class="px-3 py-2 font-medium">latestVersion</th>
              <th class="px-3 py-2 font-medium">versionCount</th>
              <th class="px-3 py-2 font-medium">回滚 targetVersion</th>
              <th class="px-3 py-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="governanceLoading">
              <td class="px-3 py-3 text-[#717182]" colspan="7">加载中...</td>
            </tr>
            <tr v-else-if="governanceRows.length === 0">
              <td class="px-3 py-3 text-[#717182]" colspan="7">暂无治理数据</td>
            </tr>
            <tr v-for="row in governanceRows" v-else :key="governanceRowKey(row)" class="border-t border-black/10">
              <td class="px-3 py-2">{{ row.scene || '-' }}</td>
              <td class="px-3 py-2">{{ row.name || '-' }}</td>
              <td class="px-3 py-2">{{ row.activeVersion || '-' }}</td>
              <td class="px-3 py-2">{{ row.latestVersion || '-' }}</td>
              <td class="px-3 py-2">{{ row.versionCount }}</td>
              <td class="px-3 py-2">
                <input
                  v-model="rollbackDrafts[governanceRowKey(row)]"
                  class="h-8 min-w-[140px] rounded-[8px] border border-black/10 px-2 text-[12px] text-[#0A0A0A] outline-none"
                  placeholder="输入版本号"
                />
              </td>
              <td class="px-3 py-2">
                <button
                  class="h-8 rounded-[8px] border border-[#155DFC]/30 px-3 text-[12px] text-[#155DFC] disabled:opacity-60"
                  :disabled="governanceRollingKey === governanceRowKey(row)"
                  @click="submitRollback(row)"
                >
                  {{ governanceRollingKey === governanceRowKey(row) ? '回滚中...' : '回滚' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
