<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-6">
    <div class="rounded-[14px] border border-black/10 bg-white p-6">
      <div class="mb-4 flex items-start justify-between gap-4">
        <div>
          <div class="text-[16px] font-semibold text-[#0A0A0A]">运维健康</div>
          <div class="mt-1 text-[12px] text-[#717182]">查看核心运行指标与处置建议</div>
        </div>
        <button class="rounded border border-black/10 px-3 py-1 text-[12px] text-[#0A0A0A]" @click="load">刷新</button>
      </div>

      <div class="mb-4 flex flex-wrap items-center gap-2 text-[12px]">
        <span class="text-[#717182]">总体状态</span>
        <span class="rounded px-2 py-0.5 font-medium" :class="tagClass(summary.overallStatus)">{{ statusLabel(summary.overallStatus) }}</span>
        <span class="text-[#717182]">生成时间</span>
        <span class="text-[#0A0A0A]">{{ formatTime(summary.generatedAt) }}</span>
      </div>

      <div v-if="loading" class="py-8 text-center text-[12px] text-[#717182]">加载中...</div>
      <div v-else-if="error" class="rounded border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">{{ error }}</div>
      <div v-else-if="summary.checks.length === 0" class="py-8 text-center text-[12px] text-[#717182]">暂无检查项</div>
      <table v-else class="w-full table-fixed text-[12px]">
        <thead>
          <tr class="border-b border-black/5">
            <th class="w-[180px] px-2 py-2 text-left font-medium text-[#717182]">检查项</th>
            <th class="w-[100px] px-2 py-2 text-left font-medium text-[#717182]">状态</th>
            <th class="w-[160px] px-2 py-2 text-left font-medium text-[#717182]">指标</th>
            <th class="px-2 py-2 text-left font-medium text-[#717182]">详情</th>
            <th class="w-[260px] px-2 py-2 text-left font-medium text-[#717182]">建议</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in summary.checks" :key="item.key" class="border-b border-black/5 align-top">
            <td class="px-2 py-2 text-[#0A0A0A]">{{ item.name }}</td>
            <td class="px-2 py-2">
              <span class="rounded px-2 py-0.5 text-[11px] font-medium" :class="tagClass(item.status)">{{ statusLabel(item.status) }}</span>
            </td>
            <td class="break-all px-2 py-2 text-[#0A0A0A]">{{ item.metric }}</td>
            <td class="px-2 py-2 text-[#474747]">{{ item.detail }}</td>
            <td class="px-2 py-2 text-[#474747]">{{ item.recommendation }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { getOpsHealthSummary, type OpsHealthLevel, type OpsHealthSummary } from '@/lib/api/ops'

const loading = ref(false)
const error = ref('')
const summary = reactive<OpsHealthSummary>({
  overallStatus: 'ready',
  generatedAt: null,
  checks: [],
})

function tagClass(status: OpsHealthLevel) {
  if (status === 'blocked') return 'bg-red-100 text-red-700'
  if (status === 'warn') return 'bg-amber-100 text-amber-700'
  return 'bg-emerald-100 text-emerald-700'
}

function statusLabel(status: OpsHealthLevel) {
  if (status === 'blocked') return '阻塞'
  if (status === 'warn') return '警告'
  return '就绪'
}

function formatTime(ts: number | null) {
  return ts ? new Date(ts * 1000).toLocaleString('zh-CN') : '-'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await getOpsHealthSummary()
    summary.overallStatus = data.overallStatus
    summary.generatedAt = data.generatedAt
    summary.checks = data.checks
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
