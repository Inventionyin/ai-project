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

function resolveTabFromRoute(raw: unknown): ReportsViewTab {
  const tab = String(raw || '').trim().toLowerCase()
  if (tab === 'trend' || tab === 'single' || tab === 'performance' || tab === 'ui') return tab
  return 'single'
}

watch(
  () => route.query.tab,
  (value) => {
    activeView.value = resolveTabFromRoute(value)
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
      <ReportsToolbar />
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
        <ReportsSingleControls />
        <ReportsSingleReportCard />
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
