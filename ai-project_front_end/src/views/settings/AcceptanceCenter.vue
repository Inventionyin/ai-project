<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-6">
    <div class="rounded-[14px] border border-black/10 bg-white p-6">
      <div class="mb-4 flex items-start justify-between gap-4">
        <div>
          <div class="text-[16px] font-semibold text-[#0A0A0A]">生产验收中心</div>
          <div class="mt-1 text-[12px] text-[#717182]">查看验收状态、外部系统连通性与报告预览</div>
        </div>
        <button class="rounded border border-black/10 px-3 py-1 text-[12px] text-[#0A0A0A]" @click="load">刷新</button>
      </div>

      <div class="mb-4 flex flex-wrap items-center gap-2 text-[12px]">
        <span class="text-[#717182]">总体状态</span>
        <span class="rounded px-2 py-0.5 font-medium" :class="tagClass(summary.overallStatus)">{{ statusLabel(summary.overallStatus) }}</span>
        <span class="rounded px-2 py-0.5 font-medium" :class="decisionClass">{{ stageDecisionLabel }}</span>
        <span class="text-[#717182]">评分</span>
        <span class="text-[#0A0A0A]">{{ summary.score ?? '-' }}</span>
        <span class="text-[#717182]">生成时间</span>
        <span class="text-[#0A0A0A]">{{ formatTime(summary.generatedAt) }}</span>
      </div>

      <div v-if="loading" class="py-8 text-center text-[12px] text-[#717182]">加载中...</div>
      <div v-else-if="error" class="rounded border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">{{ error }}</div>
      <div v-else class="space-y-4">
        <div>
          <div class="mb-2 text-[13px] font-medium text-[#0A0A0A]">检查项</div>
          <table v-if="summary.checks.length" class="w-full table-fixed text-[12px]">
            <thead>
              <tr class="border-b border-black/5">
                <th class="w-[220px] px-2 py-2 text-left font-medium text-[#717182]">检查项</th>
                <th class="w-[100px] px-2 py-2 text-left font-medium text-[#717182]">状态</th>
                <th class="px-2 py-2 text-left font-medium text-[#717182]">详情</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in summary.checks" :key="item.key" class="border-b border-black/5 align-top">
                <td class="px-2 py-2 text-[#0A0A0A]">{{ item.name }}</td>
                <td class="px-2 py-2">
                  <span class="rounded px-2 py-0.5 text-[11px] font-medium" :class="tagClass(item.status)">{{ statusLabel(item.status) }}</span>
                </td>
                <td class="px-2 py-2 text-[#474747]">{{ item.detail }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="rounded bg-[#F7F8FA] px-3 py-3 text-[12px] text-[#717182]">暂无检查项</div>
        </div>

        <div class="rounded border border-amber-200 bg-amber-50 px-3 py-3 text-[12px] leading-5 text-[#92400E]">
          <div class="font-medium text-[#78350F]">{{ stageDecisionLabel }}</div>
          <div class="mt-1">{{ stageDecisionDetail }}</div>
          <div v-if="isRealDataBlocked" class="mt-3 flex flex-wrap items-center gap-2">
            <RouterLink
              class="rounded border border-red-200 bg-white px-3 py-1 text-[12px] font-medium text-red-700 hover:bg-red-50"
              :to="defectsUrl"
            >
              查看未关闭缺陷
            </RouterLink>
            <RouterLink
              class="rounded border border-blue-200 bg-white px-3 py-1 text-[12px] font-medium text-blue-700 hover:bg-blue-50"
              :to="trialOperationUrl"
            >
              进入试运行治理
            </RouterLink>
          </div>
        </div>

        <div v-if="isRealDataBlocked" class="rounded border border-black/10 bg-[#FAFBFC] p-3">
          <div class="mb-2 text-[13px] font-medium text-[#0A0A0A]">阻塞治理概览</div>
          <div class="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <div v-for="item in blockingMetricCards" :key="item.label" class="rounded border border-black/5 bg-white px-3 py-2">
              <div class="text-[11px] text-[#717182]">{{ item.label }}</div>
              <div class="mt-1 text-[18px] font-semibold leading-6" :class="item.tone">{{ item.value }}</div>
            </div>
          </div>
        </div>

        <div>
          <div class="mb-2 text-[13px] font-medium text-[#0A0A0A]">外部系统</div>
          <table v-if="summary.externalSystems.length" class="w-full table-fixed text-[12px]">
            <thead>
              <tr class="border-b border-black/5">
                <th class="w-[220px] px-2 py-2 text-left font-medium text-[#717182]">系统</th>
                <th class="w-[100px] px-2 py-2 text-left font-medium text-[#717182]">状态</th>
                <th class="px-2 py-2 text-left font-medium text-[#717182]">详情</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in summary.externalSystems" :key="item.key" class="border-b border-black/5 align-top">
                <td class="px-2 py-2 text-[#0A0A0A]">{{ item.name }}</td>
                <td class="px-2 py-2">
                  <span class="rounded px-2 py-0.5 text-[11px] font-medium" :class="tagClass(item.status)">{{ statusLabel(item.status) }}</span>
                </td>
                <td class="px-2 py-2 text-[#474747]">
                  <div>{{ item.detail }}</div>
                  <div v-if="(item.missingFields || []).length" class="mt-1 text-[11px] text-[#B45309]">
                    缺少：{{ (item.missingFields || []).join('、') }}
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="rounded bg-[#F7F8FA] px-3 py-3 text-[12px] text-[#717182]">暂无外部系统数据</div>
        </div>

        <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div class="rounded border border-black/10 bg-[#FAFBFC] p-3">
            <div class="mb-2 text-[13px] font-medium text-[#0A0A0A]">核心指标</div>
            <div v-if="summary.metrics.length" class="space-y-1 text-[12px] text-[#374151]">
              <div v-for="item in summary.metrics" :key="item.key" class="flex items-center justify-between gap-3">
                <span class="truncate">{{ item.label }}</span>
                <span class="font-medium text-[#0A0A0A]">{{ item.value }}</span>
              </div>
            </div>
            <div v-else class="text-[12px] text-[#717182]">暂无指标</div>
          </div>

          <div class="rounded border border-black/10 bg-[#FAFBFC] p-3">
            <div class="mb-2 text-[13px] font-medium text-[#0A0A0A]">下一步</div>
            <ul v-if="summary.nextActions.length" class="list-disc space-y-1 pl-4 text-[12px] text-[#374151]">
              <li v-for="(action, index) in summary.nextActions" :key="`${index}-${action}`">{{ action }}</li>
            </ul>
            <div v-else class="text-[12px] text-[#717182]">暂无下一步建议</div>
          </div>
        </div>

        <div class="rounded border border-black/10 bg-[#FAFBFC]">
          <div class="flex items-center justify-between border-b border-black/10 px-3 py-2">
            <div class="text-[13px] font-medium text-[#0A0A0A]">报告预览</div>
            <button class="rounded border border-black/10 bg-white px-2 py-1 text-[12px] text-[#0A0A0A]" @click="copyReport">复制报告</button>
          </div>
          <pre class="max-h-[280px] overflow-auto whitespace-pre-wrap break-words px-3 py-3 text-[12px] leading-5 text-[#334155]">{{ reportMarkdown || '暂无报告内容' }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getAcceptanceReport, getAcceptanceSummary, type AcceptanceStatus, type AcceptanceSummary } from '@/lib/api/acceptance'

const loading = ref(false)
const error = ref('')
const reportMarkdown = ref('')
const projectId = ref('')
const summary = reactive<AcceptanceSummary>({
  overallStatus: 'ready',
  score: null,
  generatedAt: null,
  checks: [],
  externalSystems: [],
  metrics: [],
  nextActions: [],
})

function tagClass(status: AcceptanceStatus) {
  if (status === 'blocked') return 'bg-red-100 text-red-700'
  if (status === 'warn') return 'bg-amber-100 text-amber-700'
  return 'bg-emerald-100 text-emerald-700'
}

function statusLabel(status: AcceptanceStatus) {
  if (status === 'blocked') return '阻塞'
  if (status === 'warn') return '预警'
  return '就绪'
}

const checksByKey = computed(() => Object.fromEntries(summary.checks.map((item) => [item.key, item])))
const isRealDataBlocked = computed(() => checksByKey.value.realData?.status === 'blocked')
const isPlatformReady = computed(() =>
  checksByKey.value.externalSystems?.status === 'ready' && checksByKey.value.opsHealth?.status === 'ready'
)
const stageDecisionLabel = computed(() => {
  if (summary.overallStatus === 'ready') return '可进入正式验收'
  if (isRealDataBlocked.value && isPlatformReady.value) return '有条件放行评审'
  if (summary.overallStatus === 'blocked') return '阶段验收暂缓'
  return '谨慎通过评审'
})
const stageDecisionDetail = computed(() => {
  if (summary.overallStatus === 'ready') return '真实数据、外部系统和运维健康均已就绪。'
  if (isRealDataBlocked.value && isPlatformReady.value) return '外部系统联调与运维健康已就绪，当前仅真实数据缺陷/风险未闭环，适合输出阶段验收报告或有条件放行清单。'
  return '仍存在阻塞或预警项，请按下一步清单补齐证据后复跑验收。'
})
const decisionClass = computed(() => {
  if (summary.overallStatus === 'ready') return 'bg-emerald-100 text-emerald-700'
  if (isRealDataBlocked.value && isPlatformReady.value) return 'bg-blue-100 text-blue-700'
  if (summary.overallStatus === 'blocked') return 'bg-red-100 text-red-700'
  return 'bg-amber-100 text-amber-700'
})
const defectsUrl = computed(() => `/projects/${encodeURIComponent(projectId.value)}/defects?status=OPEN`)
const trialOperationUrl = computed(() => `/projects/${encodeURIComponent(projectId.value)}/trial-operation`)
const blockingMetricCards = computed(() => [
  { label: '未关闭缺陷', value: metricValue('defects'), tone: 'text-red-700' },
  { label: '风险提示', value: metricValue('riskHints'), tone: 'text-amber-700' },
  { label: '已执行用例', value: metricValue('executedCaseRuns'), tone: 'text-blue-700' },
])

function formatTime(ts: number | null) {
  return ts ? new Date(ts * 1000).toLocaleString('zh-CN') : '-'
}

function projectIdFromPath() {
  const match = window.location.pathname.match(/\/projects\/([^/]+)\/settings\/acceptance/)
  return match?.[1] || ''
}

function metricValue(key: string) {
  return summary.metrics.find((item) => item.key === key)?.value || '0'
}

function fallbackCopyText(text: string) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', 'true')
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  const copied = document.execCommand('copy')
  textarea.remove()
  if (!copied) throw new Error('copy-failed')
}

async function copyReport() {
  const text = reportMarkdown.value.trim()
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    try {
      fallbackCopyText(text)
    } catch {}
  }
}

async function load() {
  const pid = projectIdFromPath()
  projectId.value = pid
  if (!pid) {
    error.value = '项目 ID 缺失'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const [summaryData, reportData] = await Promise.all([getAcceptanceSummary(pid), getAcceptanceReport(pid)])
    summary.overallStatus = summaryData.overallStatus
    summary.score = summaryData.score
    summary.generatedAt = summaryData.generatedAt
    summary.checks = summaryData.checks
    summary.externalSystems = summaryData.externalSystems
    summary.metrics = summaryData.metrics
    summary.nextActions = summaryData.nextActions
    reportMarkdown.value = reportData.markdown
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
