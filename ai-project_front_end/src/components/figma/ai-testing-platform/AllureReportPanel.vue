<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { deleteRunAllureReport, fetchProjectAllureReports, type RunAllureReportListItem } from '@/lib/aiTestingPlatformApi'
import { confirmAction } from '@/lib/ui/confirm'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => {
  const raw = route.params.projectId
  if (typeof raw === 'string') return raw.trim()
  if (Array.isArray(raw) && typeof raw[0] === 'string') return raw[0].trim()
  return ''
})

const runId = computed(() => {
  const raw = route.query.runId
  if (typeof raw === 'string') return raw.trim()
  if (Array.isArray(raw) && typeof raw[0] === 'string') return raw[0].trim()
  return ''
})

const reports = ref<RunAllureReportListItem[]>([])
const isLoadingReports = ref(false)
const deletingRunId = ref('')

const resolveApiBaseUrl = () => {
  const envBase = String(import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!envBase) return ''
  return envBase.endsWith('/') ? envBase.slice(0, -1) : envBase
}

function showToast(message: string, type: 'success' | 'error' = 'success') {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, type } }))
}

function formatDateTime(timestamp: number) {
  if (!Number.isFinite(timestamp) || timestamp <= 0) return '-'
  const date = new Date(timestamp * 1000)
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date)
}

function selectRunId(nextRunId: string) {
  const id = String(nextRunId || '').trim()
  if (!id) return
  if (id === runId.value) return
  router.replace({
    path: route.path,
    query: { ...route.query, runId: id }
  })
}

function clearRunId() {
  const query = { ...route.query } as any
  delete query.runId
  router.replace({
    path: route.path,
    query
  })
}

async function loadReports() {
  const pid = projectId.value
  if (!pid) {
    reports.value = []
    return
  }
  isLoadingReports.value = true
  try {
    reports.value = await fetchProjectAllureReports(pid, 1, 100)
  } catch {
    reports.value = []
  } finally {
    isLoadingReports.value = false
  }

  if (!runId.value) return
  if (reports.value.some((item) => item.runId === runId.value)) return
  if (reports.value.length) {
    selectRunId(reports.value[0].runId)
    return
  }
  clearRunId()
}

async function deleteReport(targetRunId: string) {
  const id = String(targetRunId || '').trim()
  if (!id) return
  const confirmed = await confirmAction('确定删除该报告吗？删除后不可恢复。')
  if (!confirmed) return
  deletingRunId.value = id
  try {
    await deleteRunAllureReport(id)
    showToast('报告已删除')
    await loadReports()
  } catch (error) {
    const message = error instanceof Error ? error.message : '删除报告失败'
    showToast(message, 'error')
  } finally {
    if (deletingRunId.value === id) deletingRunId.value = ''
  }
}

watch(
  projectId,
  () => {
    void loadReports()
  },
  { immediate: true }
)

watch(
  () => [runId.value, reports.value.length],
  () => {
    if (!runId.value && reports.value.length) {
      selectRunId(reports.value[0].runId)
    }
  },
  { immediate: true }
)

const iframeSrc = computed(() => {
  if (!runId.value) return ''
  const token = String(localStorage.getItem('accessToken') || '').trim()
  const base = resolveApiBaseUrl()
  const params = new URLSearchParams()
  if (token) params.set('access_token', token)
  const queryText = params.toString()
  const suffix = queryText ? `?${queryText}` : ''
  return `${base}/api/runs/${encodeURIComponent(runId.value)}/allure-report/${suffix}`
})
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)] md:pr-[16.67px]">
    <div class="flex gap-[12px] px-[16px] pt-[16px] md:px-[24px] md:pt-[24px]">
      <div class="w-[280px] flex-shrink-0">
        <div class="rounded-[12px] border border-black/10 bg-white px-[16px] py-[12px]">
          <div class="text-[16px] font-semibold leading-[24px] text-[#0A0A0A]">历史报告</div>
          <div class="mt-[8px]">
            <div v-if="isLoadingReports" class="text-[13px] leading-[20px] text-[#717182]">加载中...</div>
            <div v-else-if="!reports.length" class="text-[13px] leading-[20px] text-[#717182]">暂无历史报告</div>
            <div v-else class="flex max-h-[calc(100vh-176px)] flex-col gap-[6px] overflow-auto pr-[4px]">
              <div
                v-for="item in reports"
                :key="item.runId"
                class="flex items-start gap-[10px] rounded-[10px] border px-[12px] py-[10px] text-left transition-colors"
                :class="item.runId === runId ? 'border-[#BEDBFF] bg-[#EFF6FF]' : 'border-black/10 bg-white hover:bg-[#F8FAFC]'"
              >
                <button type="button" class="min-w-0 flex-1 text-left" @click="selectRunId(item.runId)">
                  <div class="truncate text-[13px] font-medium leading-[18px] text-[#0A0A0A]">
                    {{ formatDateTime(item.createdAt) }}
                  </div>
                  <div class="mt-[4px] truncate text-[12px] leading-[16px] text-[#717182]">
                    runId：{{ item.runId }}
                  </div>
                </button>
                <button
                  type="button"
                  class="rounded-[8px] border border-black/10 px-[10px] py-[6px] text-[12px] leading-[16px] text-[#991B1B] disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="Boolean(deletingRunId)"
                  @click.stop="deleteReport(item.runId)"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="min-w-0 flex-1">
        <div class="rounded-[12px] border border-black/10 bg-white px-[16px] py-[12px]">
          <div class="text-[16px] font-semibold leading-[24px] text-[#0A0A0A]">Allure报告</div>
          <div class="text-[12px] leading-[16px] text-[#717182]">{{ runId ? `runId：${runId}` : '暂无可展示的 Allure 报告' }}</div>
        </div>
        <div v-if="iframeSrc" class="mt-[12px] overflow-hidden rounded-[12px] border border-black/10 bg-white">
          <iframe
            :key="iframeSrc"
            :src="iframeSrc"
            class="h-[calc(100vh-176px)] w-full border-0"
            title="Allure报告"
            loading="lazy"
            referrerpolicy="same-origin"
          ></iframe>
        </div>
        <div v-else class="mt-[12px] rounded-[12px] border border-dashed border-black/10 bg-white px-[16px] py-[18px] text-[13px] leading-[20px] text-[#717182]">
          暂无可展示的 Allure 报告
        </div>
      </div>
    </div>
  </div>
</template>
