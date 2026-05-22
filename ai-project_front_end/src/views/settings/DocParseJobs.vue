<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-6">
    <div class="rounded-[14px] border border-black/10 bg-white p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <div class="text-[16px] font-semibold text-[#0A0A0A]">文档异步解析任务</div>
          <div class="text-[12px] text-[#717182] mt-1">管理大文档的异步解析任务，支持状态查询和失败重试</div>
        </div>
        <div class="flex gap-2">
          <select v-model="statusFilter" class="text-[12px] border border-black/10 rounded px-2 py-1">
            <option value="">全部状态</option>
            <option value="PENDING">等待中</option>
            <option value="RUNNING">运行中</option>
            <option value="SUCCESS">成功</option>
            <option value="FAILED">失败</option>
          </select>
          <button @click="load" class="text-[12px] px-3 py-1 bg-[#155DFC] text-white rounded hover:bg-blue-700">刷新</button>
        </div>
      </div>

      <div v-if="loading" class="text-center py-8 text-[12px] text-[#717182]">加载中...</div>
      <div v-else-if="jobs.length === 0" class="text-center py-8 text-[12px] text-[#717182]">暂无解析任务</div>
      <table v-else class="w-full text-[12px]">
        <thead>
          <tr class="border-b border-black/5">
            <th class="text-left py-2 px-2 text-[#717182] font-medium">任务ID</th>
            <th class="text-left py-2 px-2 text-[#717182] font-medium">文档ID</th>
            <th class="text-left py-2 px-2 text-[#717182] font-medium">状态</th>
            <th class="text-left py-2 px-2 text-[#717182] font-medium">尝试次数</th>
            <th class="text-left py-2 px-2 text-[#717182] font-medium">错误信息</th>
            <th class="text-left py-2 px-2 text-[#717182] font-medium">创建时间</th>
            <th class="text-left py-2 px-2 text-[#717182] font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="job in jobs" :key="job.id" class="border-b border-black/5 hover:bg-gray-50">
            <td class="py-2 px-2 font-mono text-[11px]">{{ job.id.slice(0, 8) }}...</td>
            <td class="py-2 px-2 font-mono text-[11px]">{{ job.docId.slice(0, 8) }}...</td>
            <td class="py-2 px-2">
              <span :class="statusClass(job.status)" class="px-2 py-0.5 rounded text-[11px]">{{ statusLabel(job.status) }}</span>
            </td>
            <td class="py-2 px-2">{{ job.attempts }} / {{ job.maxRetries }}</td>
            <td class="py-2 px-2 text-red-500 max-w-[200px] truncate">{{ job.errorMessage || '-' }}</td>
            <td class="py-2 px-2">{{ formatDate(job.createdAt) }}</td>
            <td class="py-2 px-2">
              <button v-if="job.status === 'FAILED'" @click="retry(job.id)" class="text-[11px] px-2 py-0.5 bg-orange-500 text-white rounded hover:bg-orange-600">重试</button>
            </td>
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
import { listDocParseJobs, retryDocParseJob, type DocParseJob } from '@/lib/api/docParseJobs'

const route = useRoute()
const projectId = route.params.projectId as string

const jobs = ref<DocParseJob[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const statusFilter = ref('')

const statusLabel = (s: string) => ({ PENDING: '等待中', RUNNING: '运行中', SUCCESS: '成功', FAILED: '失败' })[s] || s
const statusClass = (s: string) => ({
  PENDING: 'bg-yellow-100 text-yellow-700',
  RUNNING: 'bg-blue-100 text-blue-700',
  SUCCESS: 'bg-green-100 text-green-700',
  FAILED: 'bg-red-100 text-red-700',
})[s] || 'bg-gray-100'

const formatDate = (ts: number) => new Date(ts * 1000).toLocaleString('zh-CN')

async function load() {
  loading.value = true
  try {
    const res = await listDocParseJobs(projectId, page.value, pageSize.value, statusFilter.value || undefined)
    jobs.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function retry(jobId: string) {
  await retryDocParseJob(projectId, jobId)
  await load()
}

onMounted(load)
</script>
