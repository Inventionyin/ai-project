<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { authHeader, requestJson } from '@/lib/api/client'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || route.params.id || '').trim())

const stats = ref<{ total: number; byStatus: Record<string, number> }>({ total: 0, byStatus: {} })
const loading = ref(false)
const error = ref('')

const statusLabels: Record<string, string> = {
  QUEUED: '排队中',
  SENDING: '发送中',
  SUCCEEDED: '已成功',
  FAILED: '已失败',
}

const statusColors: Record<string, string> = {
  QUEUED: 'bg-yellow-100 text-yellow-700',
  SENDING: 'bg-blue-100 text-blue-700',
  SUCCEEDED: 'bg-green-100 text-green-700',
  FAILED: 'bg-red-100 text-red-700',
}

async function loadStats() {
  if (!projectId.value) return
  loading.value = true
  error.value = ''
  try {
    stats.value = await requestJson<any>(`/projects/${encodeURIComponent(projectId.value)}/integrations/outbox/stats?projectId=${projectId.value}`, {
      method: 'GET',
      headers: authHeader(),
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
watch(projectId, loadStats)
</script>

<template>
  <div class="p-6">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-[20px] font-semibold text-[#0A0A0A]">任务队列监控</h1>
        <p class="mt-1 text-[14px] text-[#717182]">通知出站队列状态</p>
      </div>
      <button class="rounded border border-black/10 px-3 py-1.5 text-[13px] text-[#717182] hover:bg-[#F3F4F6]" @click="loadStats">刷新</button>
    </div>

    <div v-if="error" class="mb-4 rounded bg-red-50 p-3 text-[13px] text-red-600">{{ error }}</div>
    <div v-if="loading" class="py-8 text-center text-[14px] text-[#717182]">加载中...</div>

    <template v-else>
      <div class="mb-6 rounded-[10px] border border-black/10 p-6">
        <div class="text-[32px] font-bold text-[#0A0A0A]">{{ stats.total }}</div>
        <div class="text-[14px] text-[#717182]">总任务数</div>
      </div>

      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div v-for="(count, status) in stats.byStatus" :key="status" class="rounded-[10px] border border-black/10 p-4">
          <div class="flex items-center gap-2">
            <span class="inline-block rounded-full px-2 py-0.5 text-[12px] font-medium" :class="statusColors[status] || 'bg-gray-100 text-gray-700'">
              {{ statusLabels[status] || status }}
            </span>
          </div>
          <div class="mt-2 text-[24px] font-semibold text-[#0A0A0A]">{{ count }}</div>
        </div>
      </div>

      <div v-if="Object.keys(stats.byStatus).length === 0" class="py-12 text-center text-[14px] text-[#717182]">暂无任务数据</div>
    </template>
  </div>
</template>
