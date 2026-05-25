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
import { createRunRetrospectiveDraft } from '@/lib/api/knowledge'
import { createIntegrationIssue, listIntegrationIssues, type IntegrationIssueItem, type IntegrationIssueProvider } from '@/lib/api/integrationIssues'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => String(route.params.projectId || '').trim())
const runId = computed(() => String(route.params.runId || '').trim())

const isLoading = ref(false)
const loadError = ref('')
const runDetail = ref<RunDetailData | null>(null)
const caseRuns = ref<CaseRunItem[]>([])
const isCaseRunsLoading = ref(false)
const caseRunsError = ref('')
const caseRunStatusFilter = ref<'ALL' | 'QUEUED' | 'RUNNING' | 'PASSED' | 'FAILED' | 'SKIPPED'>('ALL')
const caseRunPage = ref(1)
const caseRunPageSize = ref(20)
const caseRunTotal = ref(0)
const suiteName = ref('-')
const envName = ref('-')
const isGeneratingReport = ref(false)
const isGeneratingRetrospective = ref(false)
const reportStatus = ref('未生成')
const reportUrl = ref('')
const reportError = ref('')
const creatingIssue = ref(false)
const createIssueError = ref('')
const createIssueSuccess = ref('')
const issueLinks = ref<IntegrationIssueItem[]>([])
const issueLinksLoading = ref(false)
const issueLinksError = ref('')
const issueProvider = ref<IntegrationIssueProvider>('JIRA')
const issueTitle = ref('')
const issueDescription = ref('')
const issueUrl = ref('')
const issueProjectKey = ref('')
const issueType = ref('')
const issueExecuteRequest = ref(false)
const jiraBaseUrl = ref('')
const jiraEmail = ref('')
const jiraToken = ref('')
const zentaoBaseUrl = ref('')
const zentaoProduct = ref('')
const zentaoToken = ref('')

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

const caseRunTotalPages = computed(() => {
  const pages = Math.ceil(caseRunTotal.value / Math.max(1, caseRunPageSize.value))
  return Math.max(1, pages)
})

async function loadCaseRuns() {
  const rid = runId.value
  if (!rid) {
    caseRuns.value = []
    caseRunTotal.value = 0
    return
  }
  isCaseRunsLoading.value = true
  caseRunsError.value = ''
  try {
    const data = await fetchRunCaseRuns(rid, {
      status: caseRunStatusFilter.value === 'ALL' ? undefined : caseRunStatusFilter.value,
      page: caseRunPage.value,
      pageSize: caseRunPageSize.value
    })
    caseRuns.value = Array.isArray(data.items) ? data.items : []
    caseRunTotal.value = Number(data.total ?? caseRuns.value.length)
    if (caseRunPage.value > caseRunTotalPages.value) {
      caseRunPage.value = caseRunTotalPages.value
      void loadCaseRuns()
      return
    }
  } catch (error) {
    caseRuns.value = []
    caseRunTotal.value = 0
    caseRunsError.value = error instanceof Error ? error.message : '加载 case-runs 失败'
  } finally {
    isCaseRunsLoading.value = false
  }
}

function handleCaseRunStatusChange(event: Event) {
  const target = event.target as HTMLSelectElement | null
  const value = String(target?.value || 'ALL')
  if (value === caseRunStatusFilter.value) return
  caseRunStatusFilter.value = value as typeof caseRunStatusFilter.value
  caseRunPage.value = 1
  void loadCaseRuns()
}

function handleCaseRunPageSizeChange(event: Event) {
  const target = event.target as HTMLSelectElement | null
  const value = Number(target?.value || caseRunPageSize.value)
  if (!Number.isFinite(value) || value <= 0 || value === caseRunPageSize.value) return
  caseRunPageSize.value = value
  caseRunPage.value = 1
  void loadCaseRuns()
}

function goCaseRunPrevPage() {
  if (caseRunPage.value <= 1 || isCaseRunsLoading.value) return
  caseRunPage.value -= 1
  void loadCaseRuns()
}

function goCaseRunNextPage() {
  if (caseRunPage.value >= caseRunTotalPages.value || isCaseRunsLoading.value) return
  caseRunPage.value += 1
  void loadCaseRuns()
}

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

    const [suites, environments] = await Promise.all([
      fetchSuitesLite(pid, 1, 200),
      fetchProjectEnvironments(pid)
    ])
    caseRunPage.value = 1
    await Promise.all([loadCaseRuns(), loadIssueLinks()])
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
    caseRunTotal.value = 0
    suiteName.value = '-'
    envName.value = '-'
    loadError.value = error instanceof Error ? error.message : '加载运行详情失败'
  } finally {
    isLoading.value = false
  }
}

async function loadIssueLinks() {
  const pid = projectId.value
  const rid = runId.value
  if (!pid || !rid) {
    issueLinks.value = []
    return
  }
  issueLinksLoading.value = true
  issueLinksError.value = ''
  try {
    issueLinks.value = await listIntegrationIssues(pid, { runId: rid })
  } catch (error) {
    issueLinks.value = []
    issueLinksError.value = error instanceof Error ? error.message : '加载外部 Issue 失败'
  } finally {
    issueLinksLoading.value = false
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

async function handleGenerateRetrospectiveDraft() {
  const pid = projectId.value
  const rid = runId.value
  if (!pid || !rid) return
  isGeneratingRetrospective.value = true
  try {
    const created = await createRunRetrospectiveDraft(pid, rid)
    const retrospectiveId = String(created?.id || '').trim()
    if (!retrospectiveId) throw new Error('未返回复盘记录 ID')
    showToast('复盘草稿已生成')
    void router.push(`/projects/${encodeURIComponent(pid)}/knowledge/retrospectives?retrospectiveId=${encodeURIComponent(retrospectiveId)}`)
  } catch (error) {
    const message = error instanceof Error ? error.message : '生成复盘草稿失败'
    showToast(message, 'error')
  } finally {
    isGeneratingRetrospective.value = false
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

function openRelatedSuite() {
  const pid = projectId.value
  const suiteId = String(runDetail.value?.suiteId || '').trim()
  if (!pid || !suiteId) return
  void router.push(`/projects/${encodeURIComponent(pid)}/assets/suites/${encodeURIComponent(suiteId)}`)
}

function openCaseDetail(testcaseId?: string | null) {
  const pid = projectId.value
  const id = String(testcaseId || '').trim()
  if (!pid || !id) return
  void router.push(`/projects/${encodeURIComponent(pid)}/assets/testcases/${encodeURIComponent(id)}`)
}

function openCreateDefect(item: CaseRunItem) {
  const pid = projectId.value
  const rid = runId.value
  if (!pid || !rid) return
  void router.push({
    path: `/projects/${encodeURIComponent(pid)}/defects`,
    query: {
      runId: rid,
      caseRunId: String(item.caseRunId || '').trim(),
      testcaseId: String(item.testcaseId || '').trim(),
      errorMessage: String(item.errorMessage || '').trim()
    }
  })
}

async function handleCreateIntegrationIssue() {
  const pid = projectId.value
  const rid = runId.value
  if (!pid || !rid) return
  createIssueError.value = ''
  createIssueSuccess.value = ''

  const provider = issueProvider.value
  const title = issueTitle.value.trim()
  const description = issueDescription.value.trim()
  if (!title) {
    createIssueError.value = 'Issue 标题不能为空'
    return
  }
  if (!description) {
    createIssueError.value = 'Issue 描述不能为空'
    return
  }

  const payload: {
    provider: IntegrationIssueProvider
    runId: string
    title: string
    description: string
    url?: string
    projectKey?: string
    issueType?: string
    config?: Record<string, unknown>
    credentials?: Record<string, unknown>
    executeRequest?: boolean
    timeoutSeconds?: number
  } = {
    provider,
    runId: rid,
    title,
    description
  }

  const normalizedUrl = issueUrl.value.trim()
  if (normalizedUrl) payload.url = normalizedUrl
  const normalizedProjectKey = issueProjectKey.value.trim()
  const normalizedIssueType = issueType.value.trim()
  if (normalizedProjectKey) payload.projectKey = normalizedProjectKey
  if (normalizedIssueType) payload.issueType = normalizedIssueType

  if (provider === 'JIRA') {
    const baseUrl = jiraBaseUrl.value.trim()
    const email = jiraEmail.value.trim()
    const token = jiraToken.value.trim()
    const projectKey = normalizedProjectKey
    const issueTypeText = normalizedIssueType
    if (!baseUrl || !email || !token || !projectKey || !issueTypeText) {
      createIssueError.value = '请完整填写 Jira 的 baseUrl、email、token、projectKey、issueType'
      return
    }
    payload.config = { baseUrl, projectKey, issueType: issueTypeText }
    payload.credentials = { email, token }
    payload.projectKey = projectKey
    payload.issueType = issueTypeText
    if (!payload.url) payload.url = baseUrl
  } else if (provider === 'ZENTAO') {
    const baseUrl = zentaoBaseUrl.value.trim()
    const product = zentaoProduct.value.trim()
    const token = zentaoToken.value.trim()
    if (!baseUrl || !product || !token) {
      createIssueError.value = '请完整填写 Zentao 的 baseUrl、product、token'
      return
    }
    payload.config = { baseUrl, product }
    payload.credentials = { token }
    if (!payload.url) payload.url = baseUrl
  } else {
    payload.config = {}
    payload.credentials = {}
  }
  if (issueExecuteRequest.value && provider !== 'GENERIC') {
    payload.executeRequest = true
    payload.timeoutSeconds = 10
    payload.config = { ...(payload.config || {}), realCreateEnabled: true }
  }

  creatingIssue.value = true
  try {
    await createIntegrationIssue(pid, payload)
    createIssueSuccess.value = 'Issue 创建请求已提交'
    await loadIssueLinks()
    showToast(createIssueSuccess.value)
  } catch (error) {
    createIssueError.value = error instanceof Error ? error.message : 'Issue 创建失败'
    showToast(createIssueError.value, 'error')
  } finally {
    creatingIssue.value = false
  }
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
              :disabled="!runDetail?.suiteId"
              @click="openRelatedSuite"
            >
              打开关联套件
            </button>
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
              class="h-[32px] rounded-[10px] border border-black/10 px-[12px] text-[13px] leading-[18px] text-[#717182] disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="isGeneratingRetrospective || isLoading"
              @click="handleGenerateRetrospectiveDraft"
            >
              {{ isGeneratingRetrospective ? '生成中...' : '一键生成复盘草稿' }}
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

        <div class="rounded-[12px] border border-black/10 bg-white px-[16px] py-[12px]">
          <div class="mb-[8px] text-[13px] font-medium leading-[18px] text-[#0A0A0A]">外部 Issue</div>
          <div class="grid grid-cols-1 gap-[8px] md:grid-cols-2">
            <label class="text-[12px] leading-[16px] text-[#717182]">
              provider
              <select v-model="issueProvider" class="mt-[4px] h-[32px] w-full rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] text-[#0A0A0A]">
                <option value="JIRA">JIRA</option>
                <option value="ZENTAO">ZENTAO</option>
                <option value="GENERIC">GENERIC</option>
              </select>
            </label>
            <label class="text-[12px] leading-[16px] text-[#717182]">
              runId
              <input :value="runId" disabled class="mt-[4px] h-[32px] w-full rounded-[8px] border border-black/10 bg-[rgba(236,236,240,0.3)] px-[8px] text-[12px] text-[#0A0A0A]" />
            </label>
            <label class="text-[12px] leading-[16px] text-[#717182] md:col-span-2">
              title
              <input v-model="issueTitle" class="mt-[4px] h-[32px] w-full rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] text-[#0A0A0A]" />
            </label>
            <label class="text-[12px] leading-[16px] text-[#717182] md:col-span-2">
              description
              <textarea v-model="issueDescription" class="mt-[4px] h-[72px] w-full rounded-[8px] border border-black/10 bg-white px-[8px] py-[6px] text-[12px] text-[#0A0A0A]" />
            </label>
            <label class="text-[12px] leading-[16px] text-[#717182]">
              projectKey
              <input v-model="issueProjectKey" class="mt-[4px] h-[32px] w-full rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] text-[#0A0A0A]" />
            </label>
            <label class="text-[12px] leading-[16px] text-[#717182]">
              issueType
              <input v-model="issueType" class="mt-[4px] h-[32px] w-full rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] text-[#0A0A0A]" />
            </label>
            <label class="text-[12px] leading-[16px] text-[#717182] md:col-span-2">
              url
              <input v-model="issueUrl" class="mt-[4px] h-[32px] w-full rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] text-[#0A0A0A]" />
            </label>
            <label class="flex items-center gap-[8px] text-[12px] leading-[16px] text-[#717182] md:col-span-2">
              <input v-model="issueExecuteRequest" type="checkbox" class="h-[14px] w-[14px]" />
              真实创建外部缺陷
            </label>
          </div>

          <div v-if="issueProvider === 'JIRA'" class="mt-[8px] grid grid-cols-1 gap-[8px] md:grid-cols-2">
            <label class="text-[12px] leading-[16px] text-[#717182]">
              jira baseUrl
              <input v-model="jiraBaseUrl" class="mt-[4px] h-[32px] w-full rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] text-[#0A0A0A]" />
            </label>
            <label class="text-[12px] leading-[16px] text-[#717182]">
              jira email
              <input v-model="jiraEmail" class="mt-[4px] h-[32px] w-full rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] text-[#0A0A0A]" />
            </label>
            <label class="text-[12px] leading-[16px] text-[#717182] md:col-span-2">
              jira token
              <input v-model="jiraToken" type="password" class="mt-[4px] h-[32px] w-full rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] text-[#0A0A0A]" />
            </label>
          </div>

          <div v-if="issueProvider === 'ZENTAO'" class="mt-[8px] grid grid-cols-1 gap-[8px] md:grid-cols-2">
            <label class="text-[12px] leading-[16px] text-[#717182]">
              zentao baseUrl
              <input v-model="zentaoBaseUrl" class="mt-[4px] h-[32px] w-full rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] text-[#0A0A0A]" />
            </label>
            <label class="text-[12px] leading-[16px] text-[#717182]">
              zentao product
              <input v-model="zentaoProduct" class="mt-[4px] h-[32px] w-full rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] text-[#0A0A0A]" />
            </label>
            <label class="text-[12px] leading-[16px] text-[#717182] md:col-span-2">
              zentao token
              <input v-model="zentaoToken" type="password" class="mt-[4px] h-[32px] w-full rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] text-[#0A0A0A]" />
            </label>
          </div>

          <div class="mt-[8px] flex items-center gap-[8px]">
            <button
              type="button"
              class="h-[32px] rounded-[8px] bg-[#155DFC] px-[12px] text-[12px] leading-[16px] text-white disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="creatingIssue"
              @click="handleCreateIntegrationIssue"
            >
              {{ creatingIssue ? '提交中...' : '创建外部 Issue' }}
            </button>
            <span v-if="createIssueSuccess" class="text-[12px] leading-[16px] text-[#008236]">{{ createIssueSuccess }}</span>
            <span v-if="createIssueError" class="text-[12px] leading-[16px] text-[#E7000B]">{{ createIssueError }}</span>
          </div>

          <div class="mt-[10px] overflow-hidden rounded-[8px] border border-black/10">
            <div class="flex items-center justify-between border-b border-black/10 bg-[rgba(236,236,240,0.35)] px-3 py-2">
              <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">已关联 Issue</div>
              <button
                type="button"
                class="h-[24px] rounded-[6px] border border-black/10 bg-white px-2 text-[11px] leading-[14px] text-[#4A5565] disabled:cursor-not-allowed disabled:opacity-60"
                :disabled="issueLinksLoading"
                @click="loadIssueLinks"
              >
                {{ issueLinksLoading ? '刷新中...' : '刷新' }}
              </button>
            </div>
            <div v-if="issueLinksError" class="px-3 py-2 text-[12px] leading-[16px] text-[#E7000B]">{{ issueLinksError }}</div>
            <div v-else-if="issueLinksLoading" class="px-3 py-2 text-[12px] leading-[16px] text-[#717182]">加载中...</div>
            <div v-else-if="issueLinks.length === 0" class="px-3 py-2 text-[12px] leading-[16px] text-[#717182]">暂无关联 Issue</div>
            <div v-else class="divide-y divide-black/10">
              <div v-for="item in issueLinks" :key="item.id" class="grid grid-cols-[72px_minmax(0,1fr)_120px] gap-2 px-3 py-2 text-[12px] leading-[16px]">
                <div class="font-medium text-[#0A0A0A]">{{ item.provider }}</div>
                <div class="min-w-0">
                  <a v-if="item.url" :href="item.url" target="_blank" rel="noreferrer" class="truncate text-[#155DFC] underline">{{ item.issueKey || item.id }}</a>
                  <div v-else class="truncate text-[#0A0A0A]">{{ item.issueKey || item.id }}</div>
                  <div class="truncate text-[11px] text-[#717182]">run: {{ item.runId }}</div>
                </div>
                <div class="text-right text-[11px] text-[#717182]">{{ formatDateTime(item.createdAt) }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="overflow-hidden rounded-[12px] border border-black/10 bg-white">
          <div class="flex flex-wrap items-center justify-between gap-[8px] border-b border-black/10 px-[16px] py-[10px]">
            <div class="text-[13px] font-medium leading-[18px] text-[#0A0A0A]">Case Runs（{{ caseRunTotal }}）</div>
            <div class="flex items-center gap-[8px]">
              <select
                class="h-[28px] rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] leading-[16px] text-[#717182]"
                :value="caseRunStatusFilter"
                :disabled="isCaseRunsLoading"
                @change="handleCaseRunStatusChange"
              >
                <option value="ALL">全部状态</option>
                <option value="QUEUED">QUEUED</option>
                <option value="RUNNING">RUNNING</option>
                <option value="PASSED">PASSED</option>
                <option value="FAILED">FAILED</option>
                <option value="SKIPPED">SKIPPED</option>
              </select>
              <select
                class="h-[28px] rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] leading-[16px] text-[#717182]"
                :value="String(caseRunPageSize)"
                :disabled="isCaseRunsLoading"
                @change="handleCaseRunPageSizeChange"
              >
                <option value="20">20/页</option>
                <option value="50">50/页</option>
                <option value="100">100/页</option>
              </select>
              <button
                type="button"
                class="h-[28px] rounded-[8px] border border-black/10 px-[8px] text-[12px] leading-[16px] text-[#717182] disabled:cursor-not-allowed disabled:opacity-60"
                :disabled="caseRunPage <= 1 || isCaseRunsLoading"
                @click="goCaseRunPrevPage"
              >
                上一页
              </button>
              <div class="text-[12px] leading-[16px] text-[#717182]">{{ caseRunPage }}/{{ caseRunTotalPages }}</div>
              <button
                type="button"
                class="h-[28px] rounded-[8px] border border-black/10 px-[8px] text-[12px] leading-[16px] text-[#717182] disabled:cursor-not-allowed disabled:opacity-60"
                :disabled="caseRunPage >= caseRunTotalPages || isCaseRunsLoading"
                @click="goCaseRunNextPage"
              >
                下一页
              </button>
            </div>
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
                  <th class="px-[12px] py-[8px] text-left text-[12px] font-medium leading-[16px] text-[#717182]">关联对象</th>
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
                  <td class="px-[12px] py-[8px]">
                    <div class="flex items-center gap-[6px]">
                      <button
                        type="button"
                        class="h-[28px] rounded-[8px] border border-black/10 px-[10px] text-[12px] leading-[16px] text-[#155DFC] disabled:cursor-not-allowed disabled:text-[#717182] disabled:opacity-60"
                        :disabled="!item.testcaseId"
                        @click="openCaseDetail(item.testcaseId)"
                      >
                        打开用例
                      </button>
                      <button
                        type="button"
                        class="h-[28px] rounded-[8px] border border-black/10 px-[10px] text-[12px] leading-[16px] text-[#155DFC] disabled:cursor-not-allowed disabled:text-[#717182] disabled:opacity-60"
                        :disabled="!item.caseRunId"
                        @click="openCreateDefect(item)"
                      >
                        新建缺陷
                      </button>
                    </div>
                  </td>
                </tr>
                <tr v-if="!caseRuns.length">
                  <td colspan="7" class="px-[12px] py-[16px] text-center text-[12px] leading-[16px]" :class="caseRunsError ? 'text-[#E7000B]' : 'text-[#717182]'">
                    {{ isCaseRunsLoading ? 'case-runs 加载中...' : caseRunsError || '暂无 case-runs 数据' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
