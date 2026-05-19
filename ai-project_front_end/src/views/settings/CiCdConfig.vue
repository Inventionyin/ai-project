<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { authHeader, requestJson } from '@/lib/api/client'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || route.params.id || '').trim())

const pipelines = ref<any[]>([])
const loading = ref(false)
const error = ref('')

async function load() {
  if (!projectId.value) return
  loading.value = true
  error.value = ''
  try {
    const data = await requestJson<any>(`/api/projects/${encodeURIComponent(projectId.value)}/devops/pipelines?projectId=${projectId.value}`, {
      method: 'GET', headers: authHeader(),
    })
    pipelines.value = Array.isArray(data) ? data : data?.items || []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(projectId, load)
</script>

<template>
  <div class="p-6">
    <div class="mb-6">
      <h1 class="text-[20px] font-semibold">CI/CD 配置中心</h1>
      <p class="mt-1 text-[14px] text-[#717182]">管理 CI/CD 流水线集成（共 {{ pipelines.length }} 条）</p>
    </div>

    <div v-if="error" class="mb-4 rounded bg-red-50 p-3 text-[13px] text-red-600">{{ error }}</div>
    <div v-if="loading" class="py-8 text-center text-[14px] text-[#717182]">加载中...</div>

    <div v-else-if="pipelines.length === 0" class="py-12 text-center text-[14px] text-[#717182]">
      暂无流水线配置。可在「DevOps 流水线」页面创建。
    </div>

    <div v-else class="space-y-3">
      <div v-for="p in pipelines" :key="p.id" class="rounded-[10px] border border-black/10 p-4">
        <div class="flex items-center justify-between">
          <h3 class="text-[14px] font-medium">{{ p.name }}</h3>
          <span class="rounded-full px-2 py-0.5 text-[12px] font-medium" :class="p.enabled !== false ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'">
            {{ p.enabled !== false ? '已启用' : '已禁用' }}
          </span>
        </div>
        <p class="mt-1 text-[12px] text-[#717182]">
          Provider: {{ p.provider }} | Repo: {{ p.repo || '-' }} | Workflow: {{ p.workflowFile || '-' }}
        </p>
      </div>
    </div>
  </div>
</template>
