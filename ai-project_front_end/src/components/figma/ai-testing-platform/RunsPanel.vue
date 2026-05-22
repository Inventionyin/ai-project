<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import filterSearch from '@/assets/figma/ai-testing-platform/filter-search.svg'
import headerPlus from '@/assets/figma/ai-testing-platform/header-plus.svg'
import runsFilter from '@/assets/figma/ai-testing-platform/runs-filter.svg'
import runsRefresh from '@/assets/figma/ai-testing-platform/runs-refresh.svg'
import RunsTable, { type RunRow } from '@/components/figma/ai-testing-platform/RunsTable.vue'
import { fetchProjectEnvironments, fetchRuns, fetchSuitesLite, type RunDetailData } from '@/lib/aiTestingPlatformApi'

const openCreateRun = inject<() => void>('aiTestingPlatformOpenCreateRun', () => {})

const route = useRoute()
const router = useRouter()
const projectId = computed(() => String(route.params.projectId || '').trim())

const totalRuns = ref(0)
const isLoadingRuns = ref(false)
const statusFilter = ref<RunDetailData['status'] | ''>('')
const searchText = ref('')
const page = ref(1)
const pageSize = ref(20)

const suiteNameMap = ref<Record<string, string>>({})
const environmentNameMap = ref<Record<string, string>>({})
const allRows = ref<RunRow[]>([])

const filteredRows = computed(() => {
  const query = String(searchText.value || '').trim().toLowerCase()
  if (!query) return allRows.value
  return allRows.value.filter((row) => {
    return row.runId.toLowerCase().includes(query) || row.suiteName.toLowerCase().includes(query)
  })
})

const toNameMap = <T extends { id: string; name: string }>(items: T[]) => {
  return items.reduce<Record<string, string>>((acc, item) => {
    acc[item.id] = item.name
    return acc
  }, {})
}

const formatDateTime = (timestamp?: number | null) => {
  if (!timestamp) return '-'
  const value = new Date(timestamp * 1000)
  if (Number.isNaN(value.getTime())) return '-'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(value)
}

function mapStatus(status: RunDetailData['status']): RunRow['status'] {
  if (status === 'PASSED') return '通过'
  if (status === 'FAILED') return '失败'
  if (status === 'RUNNING') return '执行中'
  if (status === 'QUEUED') return '排队中'
  return '已取消'
}

function mapTrigger(triggerType: RunDetailData['triggerType']): RunRow['trigger'] {
  if (triggerType === 'MANUAL') return '手动'
  if (triggerType === 'CI') return 'CI/CD'
  if (triggerType === 'CRON') return '定时'
  return '未知'
}

function formatPassRate(
  metrics: RunDetailData['metrics'],
  progress: RunDetailData['progress'],
  status: RunDetailData['status']
) {
  const passed = Number(metrics?.passed ?? progress?.done ?? 0)
  const total = Number(metrics?.total ?? progress?.total ?? 0)
  if (!total || total <= 0) return { value: '-', color: '#717182' }
  const rate = Math.max(0, Math.min(1, passed / total))
  const percentRaw = rate * 100
  const percent = percentRaw % 1 === 0 ? `${percentRaw.toFixed(0)}%` : `${percentRaw.toFixed(1)}%`
  if (status === 'PASSED') return { value: percent, color: '#00A63E' }
  if (status === 'FAILED') return { value: percent, color: '#D08700' }
  if (status === 'RUNNING' || status === 'QUEUED') return { value: percent, color: '#155DFC' }
  return { value: percent, color: '#717182' }
}

function mapRunToRow(run: RunDetailData): RunRow {
  const suiteName = suiteNameMap.value[run.suiteId] || run.suiteId
  const environment = run.envId ? (environmentNameMap.value[run.envId] || run.envId) : '-'
  const done = run.metrics?.done ?? run.progress?.done ?? 0
  const total = run.metrics?.total ?? run.progress?.total ?? 0
  const suiteSummary = `${done}/${total}`
  const passRate = formatPassRate(run.metrics, run.progress, run.status)
  return {
    runId: run.id,
    trigger: mapTrigger(run.triggerType),
    suiteName,
    suiteSummary,
    environment,
    status: mapStatus(run.status),
    passRate: passRate.value,
    passRateColor: passRate.color,
    startedAt: formatDateTime(run.startAt),
    duration: '-',
    createdBy: '-'
  }
}

async function loadNameMaps(pid: string) {
  const [suites, environments] = await Promise.all([fetchSuitesLite(pid, 1, 200), fetchProjectEnvironments(pid)])
  suiteNameMap.value = toNameMap(suites.items)
  environmentNameMap.value = toNameMap(environments)
}

async function loadRuns() {
  const pid = projectId.value
  if (!pid) {
    totalRuns.value = 0
    allRows.value = []
    return
  }
  isLoadingRuns.value = true
  try {
    await loadNameMaps(pid)
    const data = await fetchRuns({
      projectId: pid,
      page: page.value,
      pageSize: pageSize.value,
      status: statusFilter.value || undefined
    })
    totalRuns.value = data.total
    allRows.value = data.items.map((run) => mapRunToRow(run))
  } catch (error) {
    totalRuns.value = 0
    allRows.value = []
    const errorMessage = error instanceof Error ? error.message : '获取运行记录失败，请稍后重试'
    window.alert(errorMessage)
  } finally {
    isLoadingRuns.value = false
  }
}

function refreshRuns() {
  void loadRuns()
}

function openRun(runId: string) {
  const rid = String(runId || '').trim()
  const pid = projectId.value
  if (!rid || !pid) return
  void router.push(`/projects/${encodeURIComponent(pid)}/runs/${encodeURIComponent(rid)}`)
}

function toggleStatus(status: RunDetailData['status']) {
  statusFilter.value = statusFilter.value === status ? '' : status
}

function statusButtonClass(active: boolean) {
  return [
    'h-[28px] rounded-full border border-black/10 px-[12px] text-[12px] font-medium leading-[16px]',
    active ? 'bg-[#155DFC] text-white' : 'text-[#717182]'
  ].join(' ')
}

watch(
  [projectId, statusFilter],
  () => {
    page.value = 1
    void loadRuns()
  },
  { immediate: true }
)
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)] md:pr-[16.67px]">
    <div class="flex flex-col gap-[16px] px-[16px] pt-[16px] md:px-[24px] md:pt-[24px]">
      <div class="flex items-center justify-between gap-[16px]">
        <div class="flex flex-col gap-[2px]">
          <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">运行记录</div>
            <div class="text-[14px] leading-[20px] text-[#717182]">{{ isLoadingRuns ? '加载中...' : `共 ${totalRuns} 次运行` }}</div>
        </div>

        <div class="flex items-center gap-[8px]">
          <button
            type="button"
            class="flex h-[32px] items-center gap-[6px] rounded-[10px] border border-black/10 bg-transparent px-[12px]"
            @click="refreshRuns"
          >
            <img :src="runsRefresh" alt="" class="h-[13px] w-[13px]" />
            <span class="text-[14px] leading-[20px] text-[#717182]"> 刷新</span>
          </button>

          <button type="button" class="relative h-[32px] w-[100px] rounded-[10px] bg-[#155DFC]" @click="openCreateRun">
            <img :src="headerPlus" alt="" class="absolute left-[12px] top-[9px] h-[14px] w-[14px]" />
            <span class="absolute left-[32px] top-[6.33px] text-[14px] font-medium leading-[20px] text-white">
              新建执行
            </span>
          </button>
        </div>
      </div>

      <div class="flex flex-col gap-[12px] md:flex-row md:items-center md:justify-between">
        <div class="flex flex-wrap items-center gap-[8px]">
          <img :src="runsFilter" alt="" class="h-[13px] w-[13px]" />

          <button type="button" :class="statusButtonClass(statusFilter === 'PASSED')" @click="toggleStatus('PASSED')">
            通过
          </button>
          <button type="button" :class="statusButtonClass(statusFilter === 'FAILED')" @click="toggleStatus('FAILED')">
            失败
          </button>
          <button type="button" :class="statusButtonClass(statusFilter === 'RUNNING')" @click="toggleStatus('RUNNING')">
            执行中
          </button>
          <button type="button" :class="statusButtonClass(statusFilter === 'QUEUED')" @click="toggleStatus('QUEUED')">
            排队中
          </button>
          <button type="button" :class="statusButtonClass(statusFilter === 'CANCELED')" @click="toggleStatus('CANCELED')">
            已取消
          </button>
        </div>

        <div class="relative h-[32px] w-full max-w-[224px] rounded-[10px] border border-black/10 bg-white">
          <img :src="filterSearch" alt="" class="absolute left-[10px] top-[8.5px] h-[15px] w-[15px]" />
          <input
            class="h-full w-full rounded-[10px] bg-transparent pl-[32px] pr-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none placeholder:text-[#0A0A0A]"
            placeholder="搜索套件名..."
            v-model="searchText"
          />
        </div>
      </div>

      <section class="w-full overflow-hidden rounded-[14px] border border-black/10 bg-white">
        <RunsTable :rows="filteredRows" @open-run="openRun" />
      </section>
    </div>
  </div>
</template>
