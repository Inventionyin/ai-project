<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { RefreshCw, CheckCircle, XCircle, Clock, Activity, SlidersHorizontal } from 'lucide-vue-next'
import QualityGateCard from '@/components/figma/QualityGateCard.vue'
import FailureTop5Card from '@/components/figma/FailureTop5Card.vue'
import RecentRunsCard from '@/components/figma/RecentRunsCard.vue'

type ApiResponse<T> = {
  code?: number
  message?: string
  data?: T
}

type PageData<T> = {
  page: number
  pageSize: number
  total: number
  items: T[]
}

type DashboardSummaryData = {
  date: string
  totalRuns: number
  passedRuns: number
  failedRuns: number
  runningRuns: number
  canceledRuns: number
  passRate: number
}

type DashboardFailureTopItem = {
  id: string
  name: string
  failCount: number
  totalRuns: number
  flake?: boolean
  suiteNames: string[]
}

type DashboardFailureTopData = {
  dimension: 'testcase' | 'suite'
  items: DashboardFailureTopItem[]
}

type DashboardQualityGateItem = {
  name: string
  threshold: string
  current: string
  passed: boolean
}

type DashboardQualityGateData = {
  overall: 'PASSED' | 'PARTIAL_FAIL' | 'FAILED' | 'UNKNOWN'
  lastCheckedAt?: number | null
  linkedRunId?: string | null
  gates: DashboardQualityGateItem[]
}

type DashboardTrendItem = {
  date: string
  passRate: number
  failCount: number
  totalRuns: number
}

type DashboardTrendData = {
  days: 7 | 14 | 30
  items: DashboardTrendItem[]
}

type RunApiStatus = 'QUEUED' | 'RUNNING' | 'PASSED' | 'FAILED' | 'CANCELED'

type DashboardRunData = {
  id: string
  status: RunApiStatus
  progress?: number
  suiteId?: string | null
  envId?: string | null
  startAt?: number | null
}

type SuitePublic = {
  id: string
  name: string
}

type EnvironmentPublic = {
  id: string
  name: string
}

type RecentRunCardItem = {
  id: string
  status: '通过' | '失败' | '执行中' | '排队中' | '已取消'
  title: string
  envTime: string
  right: { type: 'text'; value: string; color: string } | { type: 'spinner' }
}

type DashboardModuleKey = 'trend' | 'qualityGate' | 'failureTop' | 'recentRuns'

type DashboardModuleOption = {
  key: DashboardModuleKey
  label: string
  description: string
}

type DashboardFilterDimension = 'testcase' | 'suite'

const route = useRoute()
const router = useRouter()
const isLoadingSummary = ref(false)
const summary = ref<DashboardSummaryData | null>(null)
const isLoadingFailureTop = ref(false)
const failureTopItems = ref<DashboardFailureTopItem[]>([])
const isLoadingQualityGate = ref(false)
const qualityGateData = ref<DashboardQualityGateData | null>(null)
const isLoadingTrend = ref(false)
const trendItems = ref<DashboardTrendItem[]>([])
const isLoadingRecentRuns = ref(false)
const recentRuns = ref<RecentRunCardItem[]>([])
const isCustomizeOpen = ref(false)
const layoutMessage = ref('')
const dashboardErrors = ref<string[]>([])
const visibleModules = ref<Record<DashboardModuleKey, boolean>>({
  trend: true,
  qualityGate: true,
  failureTop: true,
  recentRuns: true
})
const dashboardFilters = ref<{
  days: '7' | '14' | '30'
  dimension: DashboardFilterDimension
}>({
  days: '7',
  dimension: 'testcase'
})

const dashboardModuleOptions: DashboardModuleOption[] = [
  { key: 'trend', label: '近 7 天趋势', description: '通过率与失败数趋势图' },
  { key: 'qualityGate', label: '质量门禁', description: '上线/验收门禁结果' },
  { key: 'failureTop', label: '失败 Top 5', description: '高频失败用例排行' },
  { key: 'recentRuns', label: '最近运行', description: '最新执行记录回执' }
]

const dashboardDimensionLabels: Record<DashboardFilterDimension, string> = {
  testcase: '按用例',
  suite: '按套件'
}

const resolveApiBaseUrl = () => {
  const envBase = String(import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!envBase) return ''
  return envBase.endsWith('/') ? envBase.slice(0, -1) : envBase
}

const resolveAuthHeader = () => {
  const accessToken = localStorage.getItem('accessToken')
  if (!accessToken) {
    throw new Error('登录状态已失效，请重新登录')
  }
  return `Bearer ${accessToken}`
}

const projectId = computed(() => String(route.params.projectId || '').trim())
const layoutStorageKey = computed(() => `weitesting.dashboard.layout.${projectId.value || 'default'}`)
const dashboardDate = computed(() => summary.value?.date || '-')
const dashboardFilterSummary = computed(() => `当前筛选：近 ${dashboardFilters.value.days} 天 · ${dashboardDimensionLabels[dashboardFilters.value.dimension]}`)
const totalRuns = computed(() => summary.value?.totalRuns ?? 0)
const passedRuns = computed(() => summary.value?.passedRuns ?? 0)
const failedRuns = computed(() => summary.value?.failedRuns ?? 0)
const runningRuns = computed(() => summary.value?.runningRuns ?? 0)
const canceledRuns = computed(() => summary.value?.canceledRuns ?? 0)
const passRateText = computed(() => `${(summary.value?.passRate ?? 0).toFixed(1)}%`)
const qualityGateItems = computed(() => qualityGateData.value?.gates || [])
const qualityGateOverall = computed(() => qualityGateData.value?.overall || 'UNKNOWN')

const recentRunStatusMap: Record<RunApiStatus, RecentRunCardItem['status']> = {
  PASSED: '通过',
  FAILED: '失败',
  RUNNING: '执行中',
  QUEUED: '排队中',
  CANCELED: '已取消'
}

const recentRunRightColor: Record<RecentRunCardItem['status'], string> = {
  通过: '#00A63E',
  失败: '#D08700',
  执行中: '#2B7FFF',
  排队中: '#B45309',
  已取消: '#FB2C36'
}

const toDashboardErrorMessage = (error: unknown, fallback: string) => {
  if (!(error instanceof Error)) return fallback
  const message = String(error.message || '').trim()
  if (!message || message === 'Failed to fetch') return fallback
  return message
}

const pushDashboardError = (message: string) => {
  const normalized = String(message || '').trim()
  if (!normalized) return
  if (dashboardErrors.value.includes(normalized)) return
  dashboardErrors.value = [...dashboardErrors.value, normalized]
}

const clearDashboardErrors = () => {
  dashboardErrors.value = []
}

const toNameMap = <T extends { id: string; name: string }>(items: T[]) => {
  return items.reduce<Record<string, string>>((acc, item) => {
    acc[item.id] = item.name
    return acc
  }, {})
}

const formatStartTime = (startAt?: number | null) => {
  if (!startAt) return '--:--'
  const value = new Date(startAt * 1000)
  if (Number.isNaN(value.getTime())) return '--:--'
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(value)
}

const resolveDisplayName = (id: string | null | undefined, nameMap: Record<string, string>, fallback = '-') => {
  if (!id) return fallback
  const name = nameMap[id]
  if (name) return name
  return id.slice(0, 8)
}

const loadSuiteNameMap = async (authorization: string) => {
  const query = new URLSearchParams({
    projectId: projectId.value,
    page: '1',
    pageSize: '200'
  })
  const response = await fetch(`${resolveApiBaseUrl()}/api/suites?${query.toString()}`, {
    method: 'GET',
    headers: {
      Authorization: authorization
    }
  })
  const payload = await response.json() as ApiResponse<PageData<SuitePublic>>
  if (!response.ok || payload.code !== 0 || !payload.data) {
    return {}
  }
  return toNameMap(payload.data.items)
}

const loadEnvironmentNameMap = async (authorization: string) => {
  const response = await fetch(`${resolveApiBaseUrl()}/api/projects/${encodeURIComponent(projectId.value)}/environments`, {
    method: 'GET',
    headers: {
      Authorization: authorization
    }
  })
  const payload = await response.json() as ApiResponse<EnvironmentPublic[]>
  if (!response.ok || payload.code !== 0 || !payload.data) {
    return {}
  }
  return toNameMap(payload.data)
}

const loadDashboardSummary = async () => {
  if (!projectId.value) return
  isLoadingSummary.value = true
  try {
    const authorization = resolveAuthHeader()
    const response = await fetch(`${resolveApiBaseUrl()}/api/projects/${encodeURIComponent(projectId.value)}/dashboard/summary`, {
      method: 'GET',
      headers: {
        Authorization: authorization
      }
    })
    const payload = await response.json() as ApiResponse<DashboardSummaryData>
    if (!response.ok || payload.code !== 0 || !payload.data) {
      throw new Error(payload.message || '获取仪表盘汇总失败，请稍后重试')
    }
    summary.value = payload.data
  } catch (error) {
    pushDashboardError(toDashboardErrorMessage(error, '获取仪表盘汇总失败，请稍后重试'))
  } finally {
    isLoadingSummary.value = false
  }
}

const loadDashboardFailureTop = async () => {
  if (!projectId.value) return
  isLoadingFailureTop.value = true
  try {
    const authorization = resolveAuthHeader()
    const query = new URLSearchParams({
      dimension: dashboardFilters.value.dimension,
      days: dashboardFilters.value.days,
      limit: '5'
    })
    const response = await fetch(`${resolveApiBaseUrl()}/api/projects/${encodeURIComponent(projectId.value)}/dashboard/failure-top?${query.toString()}`, {
      method: 'GET',
      headers: {
        Authorization: authorization
      }
    })
    const payload = await response.json() as ApiResponse<DashboardFailureTopData>
    if (!response.ok || payload.code !== 0 || !payload.data) {
      throw new Error(payload.message || '获取失败 Top 5 失败，请稍后重试')
    }
    failureTopItems.value = payload.data.items.map((item) => ({
      id: item.id,
      name: item.name,
      failCount: item.failCount,
      totalRuns: item.totalRuns,
      flake: item.flake ?? false,
      suiteNames: item.suiteNames ?? []
    }))
  } catch (error) {
    pushDashboardError(toDashboardErrorMessage(error, '获取失败 Top 5 失败，请稍后重试'))
  } finally {
    isLoadingFailureTop.value = false
  }
}

const loadDashboardQualityGate = async () => {
  if (!projectId.value) return
  isLoadingQualityGate.value = true
  try {
    const authorization = resolveAuthHeader()
    const response = await fetch(`${resolveApiBaseUrl()}/api/projects/${encodeURIComponent(projectId.value)}/dashboard/quality-gate`, {
      method: 'GET',
      headers: {
        Authorization: authorization
      }
    })
    const payload = await response.json() as ApiResponse<DashboardQualityGateData>
    if (!response.ok || payload.code !== 0 || !payload.data) {
      throw new Error(payload.message || '获取质量门禁状态失败，请稍后重试')
    }
    qualityGateData.value = payload.data
  } catch (error) {
    pushDashboardError(toDashboardErrorMessage(error, '获取质量门禁状态失败，请稍后重试'))
  } finally {
    isLoadingQualityGate.value = false
  }
}

const loadDashboardTrend = async () => {
  if (!projectId.value) return
  isLoadingTrend.value = true
  try {
    const authorization = resolveAuthHeader()
    const response = await fetch(`${resolveApiBaseUrl()}/api/projects/${encodeURIComponent(projectId.value)}/dashboard/trend?days=${dashboardFilters.value.days}`, {
      method: 'GET',
      headers: {
        Authorization: authorization
      }
    })
    const payload = await response.json() as ApiResponse<DashboardTrendData>
    if (!response.ok || payload.code !== 0 || !payload.data) {
      throw new Error(payload.message || '获取近 7 天趋势失败，请稍后重试')
    }
    trendItems.value = payload.data.items
  } catch (error) {
    trendItems.value = []
    pushDashboardError(toDashboardErrorMessage(error, '获取近 7 天趋势失败，请稍后重试'))
  } finally {
    isLoadingTrend.value = false
  }
}

const loadRecentRuns = async () => {
  if (!projectId.value) return
  isLoadingRecentRuns.value = true
  try {
    const authorization = resolveAuthHeader()
    const query = new URLSearchParams({
      projectId: projectId.value,
      page: '1',
      pageSize: '5'
    })
    const response = await fetch(`${resolveApiBaseUrl()}/api/runs?${query.toString()}`, {
      method: 'GET',
      headers: {
        Authorization: authorization
      }
    })
    const payload = await response.json() as ApiResponse<PageData<DashboardRunData>>
    if (!response.ok || payload.code !== 0 || !payload.data) {
      throw new Error(payload.message || '获取最近运行失败，请稍后重试')
    }
    const [suiteNameMap, environmentNameMap] = await Promise.all([
      loadSuiteNameMap(authorization),
      loadEnvironmentNameMap(authorization)
    ])
    recentRuns.value = payload.data.items.map((item) => {
      const status = recentRunStatusMap[item.status]
      const progressValue = typeof item.progress === 'number' ? Math.max(0, Math.min(100, item.progress)) : 0
      const suiteName = resolveDisplayName(item.suiteId, suiteNameMap, '临时执行')
      const envName = resolveDisplayName(item.envId, environmentNameMap, '默认环境')
      return {
        id: item.id,
        status,
        title: suiteName,
        envTime: `${envName} · ${formatStartTime(item.startAt)}`,
        right: status === '执行中' || status === '排队中'
          ? { type: 'spinner' as const }
          : {
              type: 'text' as const,
              value: status === '已取消' ? '-' : `${progressValue}%`,
              color: recentRunRightColor[status]
            }
      }
    })
  } catch (error) {
    recentRuns.value = []
    pushDashboardError(toDashboardErrorMessage(error, '获取最近运行失败，请稍后重试'))
  } finally {
    isLoadingRecentRuns.value = false
  }
}

const refreshDashboard = async () => {
  clearDashboardErrors()
  await Promise.all([loadDashboardSummary(), loadDashboardFailureTop(), loadDashboardQualityGate(), loadDashboardTrend(), loadRecentRuns()])
}

const applyDashboardFilters = () => {
  clearDashboardErrors()
  void Promise.all([loadDashboardFailureTop(), loadDashboardTrend()])
}

const openReports = () => {
  if (!projectId.value) return
  void router.push({
    path: `/projects/${encodeURIComponent(projectId.value)}/reports`,
    query: { tab: 'trend' }
  })
}

const openRuns = () => {
  if (!projectId.value) return
  void router.push(`/projects/${encodeURIComponent(projectId.value)}/runs`)
}

const normalizeLayout = (source: unknown) => {
  const next = { ...visibleModules.value }
  if (!source || typeof source !== 'object') return next
  const raw = source as Record<string, unknown>
  for (const option of dashboardModuleOptions) {
    if (typeof raw[option.key] === 'boolean') {
      next[option.key] = raw[option.key] as boolean
    }
  }
  if (!Object.values(next).some(Boolean)) {
    next.trend = true
  }
  return next
}

const loadDashboardLayout = () => {
  try {
    const raw = localStorage.getItem(layoutStorageKey.value)
    if (!raw) return
    visibleModules.value = normalizeLayout(JSON.parse(raw))
  } catch {
    visibleModules.value = normalizeLayout(null)
  }
}

const saveDashboardLayout = () => {
  visibleModules.value = normalizeLayout(visibleModules.value)
  localStorage.setItem(layoutStorageKey.value, JSON.stringify(visibleModules.value))
  layoutMessage.value = '布局已保存'
  isCustomizeOpen.value = false
  window.setTimeout(() => {
    layoutMessage.value = ''
  }, 2200)
}

const resetDashboardLayout = () => {
  visibleModules.value = {
    trend: true,
    qualityGate: true,
    failureTop: true,
    recentRuns: true
  }
  saveDashboardLayout()
}

const buildDefaultTrendItems = () => {
  const today = new Date()
  return Array.from({ length: 7 }, (_, i) => {
    const date = new Date(today)
    date.setDate(today.getDate() - (6 - i))
    const month = `${date.getMonth() + 1}`.padStart(2, '0')
    const day = `${date.getDate()}`.padStart(2, '0')
    return {
      date: `${month}-${day}`,
      passRate: 0,
      failCount: 0,
      totalRuns: 0
    }
  })
}

const chartTrendItems = computed(() => trendItems.value.length > 0 ? trendItems.value : buildDefaultTrendItems())
const xLabels = computed(() => chartTrendItems.value.map((item) => item.date))
const passRate = computed(() => chartTrendItems.value.map((item) => item.passRate))
const failCount = computed(() => chartTrendItems.value.map((item) => item.failCount))

const chartAspect = 609 / 180
const chartWidth = ref(609)
const chartHeight = ref(180)
const trendContainerRef = ref<HTMLElement | null>(null)
const paddingX = 44
const paddingTop = 16
const paddingBottom = 36

const axisLabelGap = 14
const leftAxisX = computed(() => paddingX)
const rightAxisX = computed(() => chartWidth.value - paddingX)

const plotWidth = computed(() => rightAxisX.value - leftAxisX.value)
const plotHeight = computed(() => chartHeight.value - paddingTop - paddingBottom)

const xForIndex = (i: number) => {
  if (xLabels.value.length <= 1) return leftAxisX.value
  return leftAxisX.value + (plotWidth.value * i) / (xLabels.value.length - 1)
}
const yForPassRate = (v: number) => paddingTop + (plotHeight.value * (100 - v)) / 100
const countTickStep = computed(() => {
  const maxFailCount = Math.max(...failCount.value, 0)
  return Math.max(1, Math.ceil(maxFailCount / 5))
})
const maxCount = computed(() => countTickStep.value * 5)
const yForCount = (v: number) => paddingTop + (plotHeight.value * (maxCount.value - v)) / maxCount.value

const percentTicks = [100, 75, 50, 25, 0]
const countTicks = computed(() => Array.from({ length: 6 }, (_, i) => countTickStep.value * (5 - i)))

const passPoints = computed(() => passRate.value.map((v, i) => `${xForIndex(i)},${yForPassRate(v)}`).join(' '))
const failPoints = computed(() => failCount.value.map((v, i) => `${xForIndex(i)},${yForCount(v)}`).join(' '))

onMounted(() => {
  loadDashboardLayout()
  void refreshDashboard()
  const updateSize = () => {
    const el = trendContainerRef.value
    if (!el) return
    const w = el.clientWidth
    const h = el.clientHeight
    chartWidth.value = Math.max(300, w || 609)
    chartHeight.value = h && h > 0 ? h : Math.max(160, Math.round(chartWidth.value / chartAspect))
  }
  const ro = new ResizeObserver(updateSize)
  if (trendContainerRef.value) ro.observe(trendContainerRef.value)
  updateSize()
})
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)] md:min-h-[calc(100vh-48px)] md:pr-[16.67px]">
    <div class="flex flex-col gap-[16px] px-[16px] pt-[16px] md:px-[24px] md:pt-[24px]">
      <div class="flex flex-col gap-[12px] md:flex-row md:items-center md:justify-between md:gap-0">
        <div class="flex flex-col gap-[2px]">
          <div class="text-[13px] font-normal leading-[18px] text-[#0A0A0A]">仪表盘</div>
          <div class="text-[14px] leading-[20px] text-[#717182]">项目质量概览 · {{ dashboardDate }}</div>
        </div>

        <div class="flex h-[32px] items-center gap-[8px]">
          <div v-if="layoutMessage" class="hidden text-[12px] leading-4 text-[#166534] sm:block">{{ layoutMessage }}</div>
          <div class="relative">
            <button
              type="button"
              class="flex h-[32px] items-center justify-center gap-[6px] rounded-[10px] border border-black/10 bg-white px-[10px]"
              @click="isCustomizeOpen = !isCustomizeOpen"
            >
              <SlidersHorizontal class="h-[13px] w-[13px] text-[#717182]" />
              <span class="text-[14px] font-medium leading-[20px] text-[#717182]">自定义</span>
            </button>

            <div
              v-if="isCustomizeOpen"
              class="absolute right-0 z-20 mt-[8px] w-[280px] rounded-[10px] border border-black/10 bg-white p-[12px] shadow-lg"
            >
              <div class="text-[13px] font-semibold leading-5 text-[#0A0A0A]">自定义仪表盘</div>
              <div class="mt-[2px] text-[12px] leading-4 text-[#717182]">选择本项目首页要显示的模块。</div>
              <div class="mt-[10px] space-y-[8px]">
                <label
                  v-for="option in dashboardModuleOptions"
                  :key="option.key"
                  class="flex cursor-pointer items-start gap-[8px] rounded-[8px] border border-black/10 p-[8px]"
                >
                  <input
                    v-model="visibleModules[option.key]"
                    :aria-label="option.label"
                    type="checkbox"
                    class="mt-[3px] h-[14px] w-[14px] accent-[#155DFC]"
                  />
                  <span class="min-w-0">
                    <span class="block text-[12px] font-medium leading-4 text-[#0A0A0A]">{{ option.label }}</span>
                    <span class="mt-[1px] block text-[11px] leading-4 text-[#717182]">{{ option.description }}</span>
                  </span>
                </label>
              </div>
              <div class="mt-[12px] flex items-center justify-end gap-[8px]">
                <button type="button" class="h-[30px] rounded-[8px] border border-black/10 px-[10px] text-[12px] text-[#717182]" @click="resetDashboardLayout">
                  恢复默认
                </button>
                <button type="button" class="h-[30px] rounded-[8px] bg-[#155DFC] px-[10px] text-[12px] font-medium text-white" @click="saveDashboardLayout">
                  保存布局
                </button>
              </div>
            </div>
          </div>
          <button
            type="button"
            class="flex h-[32px] w-[72.33px] items-center justify-center gap-[6px] rounded-[10px] border border-black/10 bg-white"
            @click="refreshDashboard"
          >
            <RefreshCw class="h-[13px] w-[13px] text-[#717182]" />
            <span class="text-[14px] font-medium leading-[20px] text-[#717182]">
              {{ isLoadingSummary || isLoadingFailureTop || isLoadingQualityGate || isLoadingTrend || isLoadingRecentRuns ? '刷新中...' : '刷新' }}
            </span>
          </button>
        </div>
      </div>

      <div v-if="dashboardErrors.length" class="rounded-[8px] border border-[#FB2C36]/30 bg-[#FEF2F2] px-[12px] py-[10px] text-[12px] text-[#B91C1C]">
        <div v-for="message in dashboardErrors" :key="message">{{ message }}</div>
      </div>

      <div class="flex flex-col gap-[8px] rounded-[10px] border border-black/10 bg-white px-[12px] py-[10px] md:flex-row md:items-center md:justify-between">
        <div class="text-[12px] leading-4 text-[#717182]">{{ dashboardFilterSummary }}</div>
        <div class="flex flex-wrap items-center gap-[8px]">
          <label class="flex items-center gap-[6px] text-[12px] leading-4 text-[#717182]">
            时间范围
            <select
              v-model="dashboardFilters.days"
              aria-label="时间范围"
              class="h-[30px] rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] text-[#0A0A0A] outline-none focus:border-[#155DFC]"
              @change="applyDashboardFilters"
            >
              <option value="7">近 7 天</option>
              <option value="14">近 14 天</option>
              <option value="30">近 30 天</option>
            </select>
          </label>
          <label class="flex items-center gap-[6px] text-[12px] leading-4 text-[#717182]">
            统计维度
            <select
              v-model="dashboardFilters.dimension"
              aria-label="统计维度"
              class="h-[30px] rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] text-[#0A0A0A] outline-none focus:border-[#155DFC]"
              @change="applyDashboardFilters"
            >
              <option value="testcase">用例</option>
              <option value="suite">套件</option>
            </select>
          </label>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-[16px] sm:grid-cols-2 lg:grid-cols-4">
        <div class="h-[121.33px] w-full rounded-[14px] border border-black/10 bg-white px-[16.67px] pt-[16.67px]">
          <div class="flex items-center justify-between">
            <div class="text-[12px] leading-[16px] text-[#717182]">今日执行</div>
            <div class="flex h-[28px] w-[28px] items-center justify-center rounded-[10px] bg-[#FAF5FF]">
              <Activity class="h-[14px] w-[14px] text-[#9333EA]" />
            </div>
          </div>

          <div class="mt-[12px] text-[20px] font-semibold leading-[28px] text-[#0A0A0A]">{{ totalRuns }}</div>
          <div class="mt-[4px] text-[12px] leading-[16px] text-[#717182]">次运行</div>
        </div>

        <div class="h-[121.33px] w-full rounded-[14px] border border-black/10 bg-white px-[16.67px] pt-[16.67px]">
          <div class="flex items-center justify-between">
            <div class="text-[12px] leading-[16px] text-[#717182]">通过</div>
            <div class="flex h-[28px] w-[28px] items-center justify-center rounded-[10px] bg-[#F0FDF4]">
              <CheckCircle class="h-[14px] w-[14px] text-[#00A63E]" />
            </div>
          </div>

          <div class="mt-[12px] text-[20px] font-semibold leading-[28px] text-[#0A0A0A]">{{ passedRuns }}</div>
          <div class="mt-[4px] text-[12px] leading-[16px] text-[#00A63E]">通过率 {{ passRateText }}</div>
        </div>

        <div class="h-[121.33px] w-full rounded-[14px] border border-black/10 bg-white px-[16.67px] pt-[16.67px]">
          <div class="flex items-center justify-between">
            <div class="text-[12px] leading-[16px] text-[#717182]">失败</div>
            <div class="flex h-[28px] w-[28px] items-center justify-center rounded-[10px] bg-[#FEF2F2]">
              <XCircle class="h-[14px] w-[14px] text-[#FB2C36]" />
            </div>
          </div>

          <div class="mt-[12px] text-[20px] font-semibold leading-[28px] text-[#0A0A0A]">{{ failedRuns }}</div>
          <div class="mt-[4px] text-[12px] leading-[16px] text-[#FB2C36]">需要关注</div>
        </div>

        <div class="h-[121.33px] w-full rounded-[14px] border border-black/10 bg-white px-[16.67px] pt-[16.67px]">
          <div class="flex items-center justify-between">
            <div class="text-[12px] leading-[16px] text-[#717182]">进行中</div>
            <div class="flex h-[28px] w-[28px] items-center justify-center rounded-[10px] bg-[#EFF6FF]">
              <Clock class="h-[14px] w-[14px] text-[#155DFC]" />
            </div>
          </div>

          <div class="mt-[12px] text-[20px] font-semibold leading-[28px] text-[#0A0A0A]">{{ runningRuns }}</div>
          <div class="mt-[4px] text-[12px] leading-[16px] text-[#155DFC]">已取消 {{ canceledRuns }}</div>
        </div>
      </div>

      <div
        v-if="visibleModules.trend || visibleModules.qualityGate"
        class="grid grid-cols-1 gap-[16px] xl:grid-cols-2 xl:items-start"
      >
        <section v-if="visibleModules.trend" class="w-full rounded-[14px] border border-black/10 bg-white p-[20.67px]">
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0">
              <h2 class="text-sm font-semibold leading-5 text-[#0A0A0A]">近 7 天趋势</h2>
              <div class="mt-0.5 text-xs font-normal leading-4 text-[#717182]">通过率与失败数变化</div>
            </div>

            <div class="flex items-center gap-4">
              <div class="flex items-center gap-2">
                <span class="h-[2px] w-[12px] rounded" style="background:#2B7FFF"></span>
                <span class="text-xs font-normal leading-4 text-[#717182]">通过率</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="h-[2px] w-[12px] rounded" style="background:#FF6467"></span>
                <span class="text-xs font-normal leading-4 text-[#717182]">失败数</span>
              </div>
            </div>
          </div>

          <div ref="trendContainerRef" class="mt-4 w-full min-h-[160px] overflow-hidden rounded-[10px] bg-white">
            <svg
              :width="chartWidth"
              :height="chartHeight"
              class="h-full w-full"
              :viewBox="`0 0 ${chartWidth} ${chartHeight}`"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              role="img"
              aria-label="近 7 天趋势"
            >
              <g opacity="0.12" stroke="#0A0A0A" stroke-width="1">
                <line :x1="leftAxisX" :y1="paddingTop + plotHeight * (4/5)" :x2="rightAxisX" :y2="paddingTop + plotHeight * (4/5)" />
                <line :x1="leftAxisX" :y1="paddingTop + plotHeight * (3/5)" :x2="rightAxisX" :y2="paddingTop + plotHeight * (3/5)" />
                <line :x1="leftAxisX" :y1="paddingTop + plotHeight * (2/5)" :x2="rightAxisX" :y2="paddingTop + plotHeight * (2/5)" />
                <line :x1="leftAxisX" :y1="paddingTop + plotHeight * (1/5)" :x2="rightAxisX" :y2="paddingTop + plotHeight * (1/5)" />
                <line :x1="leftAxisX" :y1="paddingTop + plotHeight" :x2="rightAxisX" :y2="paddingTop + plotHeight" />

                <line :x1="leftAxisX" :y1="paddingTop" :x2="leftAxisX" :y2="paddingTop + plotHeight" />
                <line :x1="rightAxisX" :y1="paddingTop" :x2="rightAxisX" :y2="paddingTop + plotHeight" />
                <g>
                  <line
                    v-for="(_, i) in xLabels"
                    :key="`tick-${i}`"
                    :x1="xForIndex(i)"
                    :y1="paddingTop + plotHeight"
                    :x2="xForIndex(i)"
                    :y2="paddingTop + plotHeight - 6"
                  />
                </g>
              </g>

              <g font-family="Inter" font-size="12" fill="#717182">
                <g v-for="v in percentTicks" :key="`p-${v}`">
                  <text :x="leftAxisX - axisLabelGap" :y="yForPassRate(v) + 4" text-anchor="end">{{ v }}%</text>
                </g>
                <g v-for="v in countTicks" :key="`c-${v}`">
                  <text :x="rightAxisX + axisLabelGap" :y="yForCount(v) + 4" text-anchor="start">{{ v }}</text>
                </g>
              </g>

              <polyline :points="passPoints" stroke="#2B7FFF" stroke-width="2" fill="none" />
              <polyline :points="failPoints" stroke="#FF6467" stroke-width="2" fill="none" />

              <g v-for="(label, i) in xLabels" :key="`${label}-${i}`">
                <circle :cx="xForIndex(i)" :cy="yForPassRate(passRate[i])" r="3" fill="#2B7FFF" />
                <circle :cx="xForIndex(i)" :cy="yForCount(failCount[i])" r="3" fill="#FF6467" />
                <text
                  v-if="i % 2 === 0"
                  :x="xForIndex(i)"
                  :y="paddingTop + plotHeight + 12"
                  text-anchor="middle"
                  font-family="Inter"
                  font-size="12"
                  fill="#717182"
                >
                  {{ label }}
                </text>
              </g>
            </svg>
          </div>
        </section>

        <QualityGateCard
          v-if="visibleModules.qualityGate"
          :items="qualityGateItems"
          :overall="qualityGateOverall"
          :loading="isLoadingQualityGate"
          class="w-full xl:justify-self-end"
        />
      </div>

      <div
        v-if="visibleModules.failureTop || visibleModules.recentRuns"
        class="grid grid-cols-1 gap-[16px] xl:grid-cols-2 xl:items-start"
      >
        <FailureTop5Card
          v-if="visibleModules.failureTop"
          :items="failureTopItems"
          :loading="isLoadingFailureTop"
          class="w-full"
          @open-report="openReports"
        />
        <RecentRunsCard
          v-if="visibleModules.recentRuns"
          :items="recentRuns"
          :loading="isLoadingRecentRuns"
          class="w-full xl:justify-self-end"
          @open-all-runs="openRuns"
        />
      </div>
    </div>
  </div>
</template>
