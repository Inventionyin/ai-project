<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchAiJobs, fetchAuditLogs, type AiJobRecord, type AuditLogRecord } from '@/lib/api/platformRecords'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || '').trim())

const loading = ref(false)
const errorMessage = ref('')
const aiJobs = ref<AiJobRecord[]>([])
const auditLogs = ref<AuditLogRecord[]>([])

function formatDateTime(value?: number | null) {
  if (!value) return '-'
  const timestamp = value < 1_000_000_000_000 ? value * 1000 : value
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('zh-CN', { hour12: false })
}

const aiStatusSummary = computed(() => {
  const counter = aiJobs.value.reduce<Record<string, number>>((acc, row) => {
    const key = String(row.status || 'UNKNOWN').toUpperCase()
    acc[key] = (acc[key] || 0) + 1
    return acc
  }, {})
  return Object.entries(counter)
})

const auditTypeSummary = computed(() => {
  const counter = auditLogs.value.reduce<Record<string, number>>((acc, row) => {
    const key = String(row.module || 'UNKNOWN')
    acc[key] = (acc[key] || 0) + 1
    return acc
  }, {})
  return Object.entries(counter)
})

async function loadRecords() {
  if (!projectId.value) {
    aiJobs.value = []
    auditLogs.value = []
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const [jobs, logs] = await Promise.all([
      fetchAiJobs(projectId.value, { page: 1, pageSize: 20 }),
      fetchAuditLogs(projectId.value, { page: 1, pageSize: 20 })
    ])
    aiJobs.value = jobs
    auditLogs.value = logs
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载平台记录失败'
  } finally {
    loading.value = false
  }
}

watch(projectId, () => {
  void loadRecords()
}, { immediate: true })
</script>

<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-4 md:p-6">
    <div class="flex items-center justify-between">
      <h1 class="text-[16px] font-semibold leading-[24px] text-[#0A0A0A]">平台记录</h1>
      <button class="h-9 rounded-[8px] bg-[#155DFC] px-4 text-[13px] font-medium text-white disabled:opacity-60" :disabled="loading" @click="loadRecords">
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </div>

    <div v-if="errorMessage" class="mt-4 rounded-[8px] border border-[#FB2C36]/30 bg-[#FEF2F2] px-3 py-2 text-[12px] text-[#B91C1C]">
      {{ errorMessage }}
    </div>

    <div class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
      <section class="rounded-[10px] border border-black/10 bg-white p-4">
        <div class="flex items-center justify-between">
          <h2 class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">AI 任务</h2>
          <span class="text-[12px] text-[#717182]">最近执行 {{ aiJobs.length }}</span>
        </div>

        <div class="mt-3 flex flex-wrap gap-2">
          <span v-for="[status, count] in aiStatusSummary" :key="status" class="rounded-[8px] border border-black/10 bg-[#FAFAFA] px-2 py-1 text-[11px] text-[#4A4A56]">
            {{ status }} {{ count }}
          </span>
          <span v-if="aiStatusSummary.length === 0" class="text-[12px] text-[#717182]">暂无状态摘要</span>
        </div>

        <div v-if="loading" class="mt-4 text-[12px] text-[#717182]">加载中...</div>
        <div v-else-if="aiJobs.length === 0" class="mt-4 rounded-[8px] border border-dashed border-black/10 p-4 text-[12px] text-[#717182]">暂无记录</div>
        <div v-else class="mt-4 overflow-auto rounded-[8px] border border-black/10">
          <table class="min-w-full text-left text-[12px] text-[#0A0A0A]">
            <thead class="bg-[#FAFAFA] text-[#717182]">
              <tr>
                <th class="px-3 py-2 font-medium">任务类型</th>
                <th class="px-3 py-2 font-medium">状态</th>
                <th class="px-3 py-2 font-medium">触发来源</th>
                <th class="px-3 py-2 font-medium">摘要</th>
                <th class="px-3 py-2 font-medium">创建时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in aiJobs" :key="item.id" class="border-t border-black/10">
                <td class="px-3 py-2">{{ item.jobType || '-' }}</td>
                <td class="px-3 py-2">{{ item.status || '-' }}</td>
                <td class="px-3 py-2">{{ item.triggerSource || '-' }}</td>
                <td class="max-w-[220px] truncate px-3 py-2">{{ item.summary || '-' }}</td>
                <td class="px-3 py-2">{{ formatDateTime(item.createdAt) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="rounded-[10px] border border-black/10 bg-white p-4">
        <div class="flex items-center justify-between">
          <h2 class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">审计日志</h2>
          <span class="text-[12px] text-[#717182]">最近执行 {{ auditLogs.length }}</span>
        </div>

        <div class="mt-3 flex flex-wrap gap-2">
          <span v-for="[type, count] in auditTypeSummary" :key="type" class="rounded-[8px] border border-black/10 bg-[#FAFAFA] px-2 py-1 text-[11px] text-[#4A4A56]">
            {{ type }} {{ count }}
          </span>
          <span v-if="auditTypeSummary.length === 0" class="text-[12px] text-[#717182]">暂无类型摘要</span>
        </div>

        <div v-if="loading" class="mt-4 text-[12px] text-[#717182]">加载中...</div>
        <div v-else-if="auditLogs.length === 0" class="mt-4 rounded-[8px] border border-dashed border-black/10 p-4 text-[12px] text-[#717182]">暂无记录</div>
        <div v-else class="mt-4 overflow-auto rounded-[8px] border border-black/10">
          <table class="min-w-full text-left text-[12px] text-[#0A0A0A]">
            <thead class="bg-[#FAFAFA] text-[#717182]">
              <tr>
                <th class="px-3 py-2 font-medium">模块</th>
                <th class="px-3 py-2 font-medium">动作</th>
                <th class="px-3 py-2 font-medium">资源</th>
                <th class="px-3 py-2 font-medium">摘要</th>
                <th class="px-3 py-2 font-medium">创建时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in auditLogs" :key="item.id" class="border-t border-black/10">
                <td class="px-3 py-2">{{ item.module || '-' }}</td>
                <td class="px-3 py-2">{{ item.action || '-' }}</td>
                <td class="px-3 py-2">{{ item.resourceType || '-' }}</td>
                <td class="max-w-[220px] truncate px-3 py-2">{{ item.summary || item.resourceId || '-' }}</td>
                <td class="px-3 py-2">{{ formatDateTime(item.createdAt) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>
