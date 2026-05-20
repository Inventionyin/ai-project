<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-6">
    <div class="rounded-[14px] border border-black/10 bg-white p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <div class="text-[16px] font-semibold text-[#0A0A0A]">安全审计日志</div>
          <div class="text-[12px] text-[#717182] mt-1">查看关键操作的审计记录，敏感信息已自动脱敏</div>
        </div>
        <div class="flex gap-2">
          <input v-model="moduleFilter" placeholder="模块筛选" class="text-[12px] border border-black/10 rounded px-2 py-1 w-32" />
          <input v-model="actionFilter" placeholder="操作筛选" class="text-[12px] border border-black/10 rounded px-2 py-1 w-32" />
          <button @click="load" class="text-[12px] px-3 py-1 bg-[#155DFC] text-white rounded hover:bg-blue-700">查询</button>
        </div>
      </div>

      <div v-if="loading" class="text-center py-8 text-[12px] text-[#717182]">加载中...</div>
      <div v-else-if="logs.length === 0" class="text-center py-8 text-[12px] text-[#717182]">暂无审计记录</div>
      <table v-else class="w-full text-[12px]">
        <thead>
          <tr class="border-b border-black/5">
            <th class="text-left py-2 px-2 text-[#717182] font-medium">时间</th>
            <th class="text-left py-2 px-2 text-[#717182] font-medium">模块</th>
            <th class="text-left py-2 px-2 text-[#717182] font-medium">操作</th>
            <th class="text-left py-2 px-2 text-[#717182] font-medium">资源类型</th>
            <th class="text-left py-2 px-2 text-[#717182] font-medium">资源ID</th>
            <th class="text-left py-2 px-2 text-[#717182] font-medium">摘要</th>
            <th class="text-left py-2 px-2 text-[#717182] font-medium">用户</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id" class="border-b border-black/5 hover:bg-gray-50">
            <td class="py-2 px-2">{{ formatDate(log.createdAt) }}</td>
            <td class="py-2 px-2">{{ log.module || '-' }}</td>
            <td class="py-2 px-2"><span class="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-[11px]">{{ log.action }}</span></td>
            <td class="py-2 px-2">{{ log.resourceType }}</td>
            <td class="py-2 px-2 font-mono text-[11px]">{{ log.resourceId.slice(0, 8) }}...</td>
            <td class="py-2 px-2 max-w-[200px] truncate">{{ log.summary || '-' }}</td>
            <td class="py-2 px-2 font-mono text-[11px]">{{ log.userId ? log.userId.slice(0, 8) + '...' : '-' }}</td>
          </tr>
        </tbody>
      </table>

      <div v-if="total > pageSize" class="flex justify-center gap-2 mt-4">
        <button @click="page > 1 && (page--, load())" :disabled="page <= 1" class="text-[12px] px-3 py-1 border rounded disabled:opacity-50">上一页</button>
        <span class="text-[12px] py-1">{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
        <button @click="page * pageSize < total && (page++, load())" :disabled="page * pageSize >= total" class="text-[12px] px-3 py-1 border rounded disabled:opacity-50">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { requestJson, authHeader } from '@/lib/api/client'

const route = useRoute()
const projectId = route.params.projectId as string

interface AuditLog {
  id: string
  projectId: string | null
  userId: string | null
  module: string | null
  action: string
  resourceType: string
  resourceId: string
  summary: string | null
  detail: Record<string, unknown>
  createdAt: number
}

const logs = ref<AuditLog[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const moduleFilter = ref('')
const actionFilter = ref('')

const formatDate = (ts: number) => new Date(ts * 1000).toLocaleString('zh-CN')

async function load() {
  loading.value = true
  try {
    const params = new URLSearchParams({ page: String(page.value), pageSize: String(pageSize.value) })
    if (moduleFilter.value) params.set('module', moduleFilter.value)
    if (actionFilter.value) params.set('action', actionFilter.value)
    const res = await requestJson<{ page: number; pageSize: number; total: number; items: AuditLog[] }>(
      `/api/projects/${projectId}/security/audit-logs?${params}`,
      { method: 'GET', headers: authHeader() },
    )
    logs.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
