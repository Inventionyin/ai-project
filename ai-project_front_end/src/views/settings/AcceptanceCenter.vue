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
import { onMounted, reactive, ref } from 'vue'
import { getAcceptanceReport, getAcceptanceSummary, type AcceptanceStatus, type AcceptanceSummary } from '@/lib/api/acceptance'

const loading = ref(false)
const error = ref('')
const reportMarkdown = ref('')
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

function formatTime(ts: number | null) {
  return ts ? new Date(ts * 1000).toLocaleString('zh-CN') : '-'
}

function projectIdFromPath() {
  const match = window.location.pathname.match(/\/projects\/([^/]+)\/settings\/acceptance/)
  return match?.[1] || ''
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
  const projectId = projectIdFromPath()
  if (!projectId) {
    error.value = '项目 ID 缺失'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const [summaryData, reportData] = await Promise.all([getAcceptanceSummary(projectId), getAcceptanceReport(projectId)])
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
