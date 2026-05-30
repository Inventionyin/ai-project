<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ReportsToolbar from '@/components/figma/ai-testing-platform/ReportsToolbar.vue'
import ReportsViewTabs, { type ReportsViewTab } from '@/components/figma/ai-testing-platform/ReportsViewTabs.vue'
import ReportsKpiStrip from '@/components/figma/ai-testing-platform/ReportsKpiStrip.vue'
import ReportsTrendCard from '@/components/figma/ai-testing-platform/ReportsTrendCard.vue'
import ReportsFailureTop5Card from '@/components/figma/ai-testing-platform/ReportsFailureTop5Card.vue'
import ReportsDimensionAnalysisCard from '@/components/figma/ai-testing-platform/ReportsDimensionAnalysisCard.vue'
import ReportsSingleControls from '@/components/figma/ai-testing-platform/ReportsSingleControls.vue'
import ReportsSingleReportCard from '@/components/figma/ai-testing-platform/ReportsSingleReportCard.vue'
import ReportsPerformanceControls from '@/components/figma/ai-testing-platform/ReportsPerformanceControls.vue'
import ReportsPerformanceReportCard from '@/components/figma/ai-testing-platform/ReportsPerformanceReportCard.vue'
import ReportsUiTestControls from '@/components/figma/ai-testing-platform/ReportsUiTestControls.vue'
import ReportsUiTestReportCard from '@/components/figma/ai-testing-platform/ReportsUiTestReportCard.vue'
import {
  fetchPerformanceReportDetail,
  fetchProjectPerformanceReports,
  fetchProjectUiTestReports,
  fetchUiTestReportDetail,
  type PerformanceReportDetail,
  type PerformanceReportListItem,
  type UiTestReportDetail,
  type UiTestReportListItem
} from '@/lib/aiTestingPlatformApi'

type FailurePayload = {
  title: string
  message: string
  tag: string
}

const route = useRoute()
const router = useRouter()
const projectId = computed(() => String(route.params.projectId || ''))
const activeView = ref<ReportsViewTab>('single')
const performanceItems = ref<PerformanceReportListItem[]>([])
const selectedPerformanceReportId = ref('')
const performanceDetail = ref<PerformanceReportDetail | null>(null)
const performanceLoading = ref(false)
const performanceDetailLoading = ref(false)
const performanceErrorText = ref('')
const uiReportItems = ref<UiTestReportListItem[]>([])
const selectedUiReportRunId = ref('')
const uiReportDetail = ref<UiTestReportDetail | null>(null)
const uiReportLoading = ref(false)
const uiReportDetailLoading = ref(false)
const uiReportErrorText = ref('')
const actionMessage = ref('')

function setActionMessage(message: string) {
  actionMessage.value = message
}

function downloadTextFile(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function formatDateTime(value?: number | null) {
  if (!value) return '-'
  const timestamp = value < 1_000_000_000_000 ? value * 1000 : value
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('zh-CN', { hour12: false })
}

function buildSingleReportExport() {
  return [
    '# R-002 测试报告',
    '',
    '- 结果：失败',
    '- 范围：订单全量回归',
    '- 环境：development',
    '- 触发：CI/CD 触发',
    '',
    '## 失败摘要',
    '',
    '- 支付-微信支付回调验签：statusCode expected 200 but got 500',
    '- 取消订单-超时自动取消：Request timeout after 10000ms',
    '- 商品库存扣减-并发场景：inventory count expected 98 but got 102'
  ].join('\n')
}

function exportSingleReport() {
  downloadTextFile('R-002-test-report.md', buildSingleReportExport())
  setActionMessage('R-002 测试报告已导出')
}

function buildTrendReportExport() {
  return [
    '# 趋势报告',
    '',
    `- 视图：趋势分析`,
    `- 导出时间：${formatDateTime(Date.now())}`,
    '',
    '## 内容范围',
    '',
    '- 质量趋势概览',
    '- 失败 Top 5',
    '- 维度分析',
    '',
    '请结合页面中的图表与分析卡片查看最新结果。'
  ].join('\n')
}

function buildPerformanceReportExport(detail: PerformanceReportDetail) {
  return [
    `# 性能报告 - ${detail.name}`,
    '',
    `- 报告 ID：${detail.id}`,
    `- 状态：${detail.status}`,
    `- 创建时间：${formatDateTime(detail.createdAt)}`,
    `- 持续时间：${detail.duration}`,
    `- VU：${detail.vus}`,
    `- TPS：${detail.tps}`,
    `- 平均响应时间：${detail.avgResponseMs} ms`,
    `- P95 响应时间：${detail.p95ResponseMs} ms`,
    `- 成功率：${detail.successRate}%`,
    '',
    '## 资源概况',
    '',
    `- CPU 平均/峰值：${detail.resources.cpuAvg}% / ${detail.resources.cpuMax}%`,
    `- 内存平均/峰值：${detail.resources.memoryAvg}% / ${detail.resources.memoryMax}%`,
    `- IO 读/写：${detail.resources.ioReadMb} MB / ${detail.resources.ioWriteMb} MB`,
    '',
    '## 断言结果',
    '',
    ...detail.asserts.map((item) => `- ${item.apiName}: passed ${item.passed}, failed ${item.failed}`)
  ].join('\n')
}

function buildUiReportExport(detail: UiTestReportDetail) {
  return [
    `# UI 测试报告 - ${detail.pageId}`,
    '',
    `- Run ID：${detail.runId}`,
    `- 结果：${detail.result}`,
    `- 状态：${detail.status}`,
    `- 断言级别：${detail.assertLevel}`,
    `- 开始时间：${formatDateTime(detail.startedAt)}`,
    `- 结束时间：${formatDateTime(detail.finishedAt)}`,
    `- Spec：${detail.specPath}`,
    '',
    '## 汇总',
    '',
    `- 总数：${detail.summary.total}`,
    `- 通过：${detail.summary.passed}`,
    `- 失败：${detail.summary.failed}`,
    `- 跳过：${detail.summary.skipped}`,
    `- 耗时：${detail.summary.durationMs} ms`,
    '',
    '## 失败用例',
    '',
    ...(detail.failedCases.length
      ? detail.failedCases.map((item) => `- ${item.title}: ${item.error}`)
      : ['- 无失败用例'])
  ].join('\n')
}

function viewSingleReportDetail() {
  document.getElementById('single-report-detail')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  setActionMessage('已定位到 R-002 测试报告详情')
}

async function shareSingleReport() {
  const shareUrl = `${window.location.origin}${router.resolve({ path: route.path, query: { ...route.query, tab: 'single', reportId: 'R-002' } }).href}`
  try {
    await navigator.clipboard?.writeText(shareUrl)
    setActionMessage('分享链接已复制')
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = shareUrl
    textarea.setAttribute('readonly', 'true')
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    document.body.appendChild(textarea)
    textarea.select()
    const copied = document.execCommand('copy')
    textarea.remove()
    setActionMessage(copied ? '分享链接已复制' : `分享链接：${shareUrl}`)
  }
}

function createDefectFromFailure(payload: FailurePayload) {
  void router.push({
    path: `/projects/${encodeURIComponent(projectId.value)}/defects`,
    query: {
      title: `失败用例缺陷：${payload.title}`,
      description: `报告 R-002 中发现失败用例：${payload.title}\n错误信息：${payload.message}\n失败类型：${payload.tag}`,
      errorMessage: payload.message,
      severity: payload.tag === 'TIMEOUT' ? 'P1' : 'P2',
      sourceReportId: 'R-002'
    }
  })
}

function resolveDefaultViewFromRoute(path: string): ReportsViewTab {
  const normalized = String(path || '').trim().toLowerCase()
  if (normalized.includes('/automation/ui')) return 'ui'
  if (normalized.includes('/automation/performance')) return 'performance'
  return 'single'
}

function resolveViewFromRoute(rawTab: unknown, path: string): ReportsViewTab {
  const tab = String(rawTab || '').trim().toLowerCase()
  if (tab === 'trend' || tab === 'single' || tab === 'performance' || tab === 'ui') return tab
  return resolveDefaultViewFromRoute(path)
}

const toolbarCopy = computed(() => {
  if (activeView.value === 'trend') {
    return {
      title: '报告中心',
      subtitle: '质量趋势、失败分布与维度分析'
    }
  }
  if (activeView.value === 'performance') {
    return {
      title: '性能自动化',
      subtitle: '性能基线、吞吐趋势与压测详情'
    }
  }
  if (activeView.value === 'ui') {
    return {
      title: 'UI自动化',
      subtitle: 'UI 自动化结果、失败截图与回放'
    }
  }
  return {
    title: '报告中心',
    subtitle: '单次执行结果与失败明细'
  }
})

const exportLabel = computed(() => {
  if (activeView.value === 'trend') return '导出趋势报告'
  if (activeView.value === 'performance') return '导出性能报告'
  if (activeView.value === 'ui') return '导出UI报告'
  return '导出报告'
})

const exportDisabled = computed(() => {
  if (activeView.value === 'performance') return !performanceDetail.value
  if (activeView.value === 'ui') return !uiReportDetail.value
  return false
})

function exportCurrentReport() {
  if (activeView.value === 'trend') {
    downloadTextFile('trend-report-summary.md', buildTrendReportExport())
    setActionMessage('趋势报告已导出')
    return
  }
  if (activeView.value === 'performance') {
    if (!performanceDetail.value) {
      setActionMessage('暂无可导出的性能报告')
      return
    }
    downloadTextFile(`performance-report-${performanceDetail.value.id}.md`, buildPerformanceReportExport(performanceDetail.value))
    setActionMessage(`性能报告已导出：${performanceDetail.value.name}`)
    return
  }
  if (activeView.value === 'ui') {
    if (!uiReportDetail.value) {
      setActionMessage('暂无可导出的 UI 报告')
      return
    }
    downloadTextFile(`ui-test-report-${uiReportDetail.value.runId}.md`, buildUiReportExport(uiReportDetail.value))
    setActionMessage(`UI 报告已导出：${uiReportDetail.value.pageId}`)
    return
  }
  exportSingleReport()
}

watch(
  [() => route.query.tab, () => route.path],
  ([tab, path]) => {
    activeView.value = resolveViewFromRoute(tab, path)
  },
  { immediate: true }
)

watch(
  () => route.query.uiRunId,
  (value) => {
    const runId = String(value || '').trim()
    if (!runId) return
    selectedUiReportRunId.value = runId
    if (activeView.value === 'ui' && !uiReportLoading.value) {
      void loadUiReportDetail(runId)
    }
  },
  { immediate: true }
)

watch(activeView, (value) => {
  const current = String(route.query.tab || '').trim().toLowerCase()
  if (current === value) return
  router.replace({
    query: {
      ...route.query,
      tab: value
    }
  })
})

async function loadPerformanceReports() {
  if (!projectId.value) return
  performanceLoading.value = true
  performanceErrorText.value = ''
  try {
    const items = await fetchProjectPerformanceReports(projectId.value, 1, 50)
    performanceItems.value = items
    if (!items.length) {
      selectedPerformanceReportId.value = ''
      performanceDetail.value = null
      return
    }
    if (!items.some((item) => item.id === selectedPerformanceReportId.value)) {
      selectedPerformanceReportId.value = items[0].id
    }
    await loadPerformanceReportDetail(selectedPerformanceReportId.value)
  } catch (error) {
    performanceItems.value = []
    performanceDetail.value = null
    performanceErrorText.value = error instanceof Error ? error.message : '加载性能报告失败'
  } finally {
    performanceLoading.value = false
  }
}

async function loadPerformanceReportDetail(reportId: string) {
  const id = String(reportId || '').trim()
  if (!id) {
    performanceDetail.value = null
    return
  }
  performanceDetailLoading.value = true
  performanceErrorText.value = ''
  try {
    performanceDetail.value = await fetchPerformanceReportDetail(id)
  } catch (error) {
    performanceDetail.value = null
    performanceErrorText.value = error instanceof Error ? error.message : '加载性能报告详情失败'
  } finally {
    performanceDetailLoading.value = false
  }
}

async function loadUiReports() {
  if (!projectId.value) return
  uiReportLoading.value = true
  uiReportErrorText.value = ''
  try {
    const runIdFromRoute = String(route.query.uiRunId || '').trim()
    const items = await fetchProjectUiTestReports(projectId.value, 1, 50)
    uiReportItems.value = items
    if (!items.length) {
      selectedUiReportRunId.value = ''
      uiReportDetail.value = null
      return
    }
    if (runIdFromRoute && items.some((item) => item.runId === runIdFromRoute)) {
      selectedUiReportRunId.value = runIdFromRoute
    } else if (!items.some((item) => item.runId === selectedUiReportRunId.value)) {
      selectedUiReportRunId.value = items[0].runId
    }
    await loadUiReportDetail(selectedUiReportRunId.value)
  } catch (error) {
    uiReportItems.value = []
    uiReportDetail.value = null
    uiReportErrorText.value = error instanceof Error ? error.message : '加载 UI 测试报告失败'
  } finally {
    uiReportLoading.value = false
  }
}

async function loadUiReportDetail(runId: string) {
  const id = String(runId || '').trim()
  if (!id) {
    uiReportDetail.value = null
    return
  }
  uiReportDetailLoading.value = true
  uiReportErrorText.value = ''
  try {
    uiReportDetail.value = await fetchUiTestReportDetail(id)
  } catch (error) {
    uiReportDetail.value = null
    uiReportErrorText.value = error instanceof Error ? error.message : '加载 UI 测试报告详情失败'
  } finally {
    uiReportDetailLoading.value = false
  }
}

watch(selectedPerformanceReportId, (value) => {
  void loadPerformanceReportDetail(value)
})

watch(selectedUiReportRunId, (value) => {
  void loadUiReportDetail(value)
})

watch(
  () => activeView.value,
  (value) => {
    if (value === 'performance' && !performanceItems.value.length && !performanceLoading.value) {
      void loadPerformanceReports()
    }
    if (value === 'ui' && !uiReportItems.value.length && !uiReportLoading.value) {
      void loadUiReports()
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)] md:pr-[16.67px]">
    <div class="flex flex-col gap-[16px] px-[16px] pt-[16px] md:px-[24px] md:pt-[24px]">
      <ReportsToolbar
        :title="toolbarCopy.title"
        :subtitle="toolbarCopy.subtitle"
        :export-label="exportLabel"
        :export-disabled="exportDisabled"
        @export="exportCurrentReport"
      />
      <div
        v-if="actionMessage"
        role="status"
        class="rounded-[8px] border border-[#BFDBFE] bg-[#EFF6FF] px-[12px] py-[8px] text-[13px] leading-[18px] text-[#155DFC]"
      >
        {{ actionMessage }}
      </div>
      <ReportsViewTabs v-model="activeView" />

      <div v-if="activeView === 'trend'" class="flex flex-col gap-[16px]">
        <ReportsKpiStrip />
        <ReportsTrendCard />

        <div class="flex flex-col gap-[16px] md:flex-row">
          <ReportsFailureTop5Card class="md:w-[487.67px]" />
          <ReportsDimensionAnalysisCard class="md:w-[487.67px]" />
        </div>
      </div>

      <div v-else-if="activeView === 'single'" class="flex flex-col gap-[16px]">
        <ReportsSingleControls @view-detail="viewSingleReportDetail" />
        <div id="single-report-detail">
          <ReportsSingleReportCard @share="shareSingleReport" @create-defect="createDefectFromFailure" />
        </div>
      </div>

      <div v-else-if="activeView === 'performance'" class="flex flex-col gap-[16px]">
        <ReportsPerformanceControls
          v-model="selectedPerformanceReportId"
          :items="performanceItems"
          :loading="performanceLoading"
          @refresh="loadPerformanceReports"
        />
        <ReportsPerformanceReportCard
          :report="performanceDetail"
          :loading="performanceLoading || performanceDetailLoading"
          :error-text="performanceErrorText"
        />
      </div>

      <div v-else class="flex flex-col gap-[16px]">
        <ReportsUiTestControls
          v-model="selectedUiReportRunId"
          :items="uiReportItems"
          :loading="uiReportLoading"
          @refresh="loadUiReports"
        />
        <ReportsUiTestReportCard
          :report="uiReportDetail"
          :loading="uiReportLoading || uiReportDetailLoading"
          :error-text="uiReportErrorText"
        />
      </div>
    </div>
  </div>
</template>
