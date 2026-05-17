<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchProjectAllureReports,
  fetchProjectEnvironments,
  fetchRunCaseRuns,
  fetchRunDetail,
  fetchSuitesLite,
  generateRunAllureReport,
  type CaseRunItem,
  type RunDetailData
} from '@/lib/aiTestingPlatformApi'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => String(route.params.projectId || '').trim())
const runId = computed(() => String(route.params.runId || '').trim())

const isLoading = ref(false)
const loadError = ref('')
const runDetail = ref<RunDetailData | null>(null)
const caseRuns = ref<CaseRunItem[]>([])
const suiteName = ref('-')
const envName = ref('-')
const isGeneratingReport = ref(false)
const reportStatus = ref('未生成')
const reportUrl = ref('')
const reportError = ref('')

function showToast(message: string, type: 'success' | 'error' = 'success') {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, type } }))
}

function formatDateTime(timestamp?: number | null) {
  if (!timestamp || timestamp <= 0) return '-'
  const date = new Date(timestamp * 1000)
  if (Number.isNaN(date.getTime())) return '-'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).format(date)
}

function mapStatusText(status?: RunDetailData['status']) {
  if (status === 'PASSED') return '通过'
  if (status === 'FAILED') return '失败'
  if (status === 'RUNNING') return '执行中'
  if (status === 'QUEUED') return '排队中'
  if (status === 'CANCELED') return '已取消'
  return '未知'
}

function statusClass(status?: RunDetailData['status']) {
  if (status === 'PASSED') return 'bg-[#DCFCE7] text-[#008236]'
  if (status === 'FAILED') return 'bg-[#FFE2E2] text-[#E7000B]'
  if (status === 'RUNNING' || status === 'QUEUED') return 'bg-[#DBEAFE] text-[#155DFC]'
  return 'bg-[#F3F4F6] text-[#6A7282]'
}

function triggerText(triggerType?: RunDetailData['triggerType']) {
  if (triggerType === 'MANUAL') return '手动'
  if (triggerType === 'CI') return 'CI/CD'
  if (triggerType === 'CRON') return '定时'
  if (triggerType === 'WEBHOOK') return 'Webhook'
  return '-'
}

function caseStatusClass(status?: string) {
  if (status === 'PASSED') return 'text-[#008236]'
  if (status === 'FAILED') return 'text-[#E7000B]'
  if (status === 'RUNNING' || status === 'QUEUED') return 'text-[#155DFC]'
  return 'text-[#717182]'
}

const metricsSummary = computed(() => {
  const detail = runDetail.value
  const total = Number(detail?.metrics?.total ?? detail?.progress?.total ?? 0)
  const done = Number(detail?.metrics?.done ?? detail?.progress?.done ?? 0)
  const passed = Number(detail?.metrics?.passed ?? 0)
  const failed = Number(detail?.metrics?.failed ?? 0)
  const skipped = Number(detail?.metrics?.skipped ?? 0)
  const passRate = total > 0 ? `${((passed / total) * 100).toFixed(passed % total === 0 ? 0 : 1)}%` : '-'
  return { total, done, passed, failed, skipped, passRate }
})

async function loadRunDetail() {
  const pid = projectId.value
  const rid = runId.value
  if (!pid || !rid) return
  isLoading.value = true
  loadError.value = ''
  reportError.value = ''
  try {
    const detail = await fetchRunDetail(rid)
    runDetail.value = detail

    const [rows, suites, environments] = await Promise.all([
      fetchRunCaseRuns(rid),
      fetchSuitesLite(pid, 1, 200),
      fetchProjectEnvironments(pid)
    ])
    caseRuns.value = rows
    suiteName.value = suites.items.find((item) => item.id === detail.suiteId)?.name || detail.suiteId || '-'
    envName.value = detail.envId ? environments.find((item) => item.id === detail.envId)?.name || detail.envId : '-'
    try {
      const reports = await fetchProjectAllureReports(pid, 1, 100)
      const report = reports.find((item) => item.runId === rid)
      reportStatus.value = report ? 'READY' : '未生成'
      reportUrl.value = report?.reportUrl || ''
    } catch {
      reportStatus.value = '未生成'
      reportUrl.value = ''
    }
  } catch (error) {
    runDetail.value = null
    caseRuns.value = []
    suiteName.value = '-'
    envName.value = '-'
    loadError.value = error instanceof Error ? error.message : '加载运行详情失败'
  } finally {
    isLoading.value = false
  }
}

async function handleGenerateAllureReport() {
  const rid = runId.value
  if (!rid) return
  isGeneratingReport.value = true
  reportError.value = ''
  try {
    const data = await generateRunAllureReport(rid)
    reportStatus.value = data.reportStatus || ''
    reportUrl.value = data.reportUrl || ''
    if (data.reportStatus === 'READY') {
      showToast('Allure 报告生成成功')
    } else {
      reportError.value = data.errorMessage || '报告生成失败'
      showToast(reportError.value, 'error')
    }
  } catch (error) {
    reportError.value = error instanceof Error ? error.message : '生成 Allure 报告失败'
    showToast(reportError.value, 'error')
  } finally {
    isGeneratingReport.value = false
  }
}

function openAllureReportPage() {
  const pid = projectId.value
  const rid = runId.value
  if (!pid || !rid) return
  void router.push({
    path: `/projects/${encodeURIComponent(pid)}/reports/allure`,
    query: { runId: rid }
  })
}

watch(
  () => [projectId.value, runId.value],
  () => {
    void loadRunDetail()
  },
  { immediate: true }
)
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)] md:pr-[16.67px]">
    <div class="flex flex-col gap-[12px] px-[16px] pt-[16px] md:px-[24px] md:pt-[24px]">
      <div class="rounded-[12px] border border-black/10 bg-white px-[16px] py-[12px]">
        <div class="flex flex-wrap items-start justify-between gap-[12px]">
          <div class="min-w-0">
            <div class="truncate text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">运行详情</div>
            <div class="mt-[2px] break-all font-mono text-[12px] leading-[16px] text-[#155DFC]">{{ runId || '-' }}</div>
          </div>
          <div class="flex items-center gap-[8px]">
            <button
              type="button"
              class="h-[32px] rounded-[10px] border border-black/10 px-[12px] text-[13px] leading-[18px] text-[#717182] disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="isGeneratingReport || isLoading"
              @click="handleGenerateAllureReport"
            >
              {{ isGeneratingReport ? '生成中...' : '生成 Allure 报告' }}
            </button>
            <button
              type="button"
              class="h-[32px] rounded-[10px] bg-[#155DFC] px-[12px] text-[13px] leading-[18px] text-white"
              @click="openAllureReportPage"
            >
              打开报告页
            </button>
          </div>
        </div>
      </div>

      <div v-if="isLoading" class="rounded-[12px] border border-black/10 bg-white px-[16px] py-[14px] text-[13px] leading-[20px] text-[#717182]">
        详情加载中...
      </div>
      <div v-else-if="loadError" class="rounded-[12px] border border-black/10 bg-white px-[16px] py-[14px] text-[13px] leading-[20px] text-[#E7000B]">
        {{ loadError }}
      </div>

      <template v-else-if="runDetail">
        <div class="grid grid-cols-1 gap-[12px] xl:grid-cols-2">
          <div class="rounded-[12px] border border-black/10 bg-white px-[16px] py-[12px]">
            <div class="mb-[8px] text-[13px] font-medium leading-[18px] text-[#0A0A0A]">基础信息</div>
            <div class="grid grid-cols-[96px_1fr] gap-y-[6px] text-[12px] leading-[16px]">
              <div class="text-[#717182]">状态</div>
              <div><span class="rounded-full px-[8px] py-[2px] font-medium" :class="statusClass(runDetail.status)">{{ mapStatusText(runDetail.status) }}</span></div>
              <div class="text-[#717182]">触发方式</div>
              <div class="text-[#0A0A0A]">{{ triggerText(runDetail.triggerType) }}</div>
              <div class="text-[#717182]">套件</div>
              <div class="break-all text-[#0A0A0A]">{{ suiteName }}</div>
              <div class="text-[#717182]">环境</div>
              <div class="break-all text-[#0A0A0A]">{{ envName }}</div>
              <div class="text-[#717182]">开始时间</div>
              <div class="text-[#0A0A0A]">{{ formatDateTime(runDetail.startAt) }}</div>
            </div>
          </div>

          <div class="rounded-[12px] border border-black/10 bg-white px-[16px] py-[12px]">
            <div class="mb-[8px] text-[13px] font-medium leading-[18px] text-[#0A0A0A]">执行指标</div>
            <div class="grid grid-cols-3 gap-[8px]">
              <div class="rounded-[10px] bg-[rgba(236,236,240,0.4)] p-[8px]">
                <div class="text-[12px] leading-[16px] text-[#717182]">进度</div>
                <div class="mt-[2px] text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">{{ metricsSummary.done }}/{{ metricsSummary.total }}</div>
              </div>
              <div class="rounded-[10px] bg-[rgba(236,236,240,0.4)] p-[8px]">
                <div class="text-[12px] leading-[16px] text-[#717182]">通过率</div>
                <div class="mt-[2px] text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">{{ metricsSummary.passRate }}</div>
              </div>
              <div class="rounded-[10px] bg-[rgba(236,236,240,0.4)] p-[8px]">
                <div class="text-[12px] leading-[16px] text-[#717182]">失败数</div>
                <div class="mt-[2px] text-[14px] font-semibold leading-[20px] text-[#E7000B]">{{ metricsSummary.failed }}</div>
              </div>
            </div>
            <div class="mt-[8px] grid grid-cols-3 gap-[8px] text-[12px] leading-[16px] text-[#717182]">
              <div>通过：{{ metricsSummary.passed }}</div>
              <div>失败：{{ metricsSummary.failed }}</div>
              <div>跳过：{{ metricsSummary.skipped }}</div>
            </div>
          </div>
        </div>

        <div class="rounded-[12px] border border-black/10 bg-white px-[16px] py-[12px]">
          <div class="mb-[8px] text-[13px] font-medium leading-[18px] text-[#0A0A0A]">Allure 报告</div>
          <div class="grid grid-cols-[96px_1fr] gap-y-[6px] text-[12px] leading-[16px]">
            <div class="text-[#717182]">生成状态</div>
            <div class="text-[#0A0A0A]">{{ reportStatus || '-' }}</div>
            <div class="text-[#717182]">报告链接</div>
            <div class="break-all">
              <a v-if="reportUrl" :href="reportUrl" target="_blank" rel="noreferrer" class="text-[#155DFC] underline">
                {{ reportUrl }}
              </a>
              <span v-else class="text-[#717182]">-</span>
            </div>
            <div class="text-[#717182]">失败信息</div>
            <div class="break-all" :class="reportError ? 'text-[#E7000B]' : 'text-[#717182]'">{{ reportError || '-' }}</div>
          </div>
        </div>

        <div class="overflow-hidden rounded-[12px] border border-black/10 bg-white">
          <div class="border-b border-black/10 px-[16px] py-[10px] text-[13px] font-medium leading-[18px] text-[#0A0A0A]">
            Case Runs（{{ caseRuns.length }}）
          </div>
          <div class="overflow-x-auto">
            <table class="w-full min-w-[880px] border-collapse">
              <thead>
                <tr class="bg-[rgba(236,236,240,0.3)]">
                  <th class="px-[12px] py-[8px] text-left text-[12px] font-medium leading-[16px] text-[#717182]">Case Run ID</th>
                  <th class="px-[12px] py-[8px] text-left text-[12px] font-medium leading-[16px] text-[#717182]">Testcase ID</th>
                  <th class="px-[12px] py-[8px] text-left text-[12px] font-medium leading-[16px] text-[#717182]">状态</th>
                  <th class="px-[12px] py-[8px] text-left text-[12px] font-medium leading-[16px] text-[#717182]">开始时间</th>
                  <th class="px-[12px] py-[8px] text-left text-[12px] font-medium leading-[16px] text-[#717182]">结束时间</th>
                  <th class="px-[12px] py-[8px] text-left text-[12px] font-medium leading-[16px] text-[#717182]">失败信息</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in caseRuns" :key="item.caseRunId" class="border-t border-black/10">
                  <td class="px-[12px] py-[8px] font-mono text-[12px] leading-[16px] text-[#0A0A0A]">{{ item.caseRunId }}</td>
                  <td class="px-[12px] py-[8px] font-mono text-[12px] leading-[16px] text-[#0A0A0A]">{{ item.testcaseId || '-' }}</td>
                  <td class="px-[12px] py-[8px] text-[12px] font-medium leading-[16px]" :class="caseStatusClass(item.status)">{{ item.status || '-' }}</td>
                  <td class="px-[12px] py-[8px] text-[12px] leading-[16px] text-[#717182]">{{ formatDateTime(item.startAt ?? null) }}</td>
                  <td class="px-[12px] py-[8px] text-[12px] leading-[16px] text-[#717182]">{{ formatDateTime(item.endAt ?? null) }}</td>
                  <td class="px-[12px] py-[8px] text-[12px] leading-[16px] text-[#E7000B]">{{ item.errorMessage || '-' }}</td>
                </tr>
                <tr v-if="!caseRuns.length">
                  <td colspan="6" class="px-[12px] py-[16px] text-center text-[12px] leading-[16px] text-[#717182]">暂无 case-runs 数据</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
