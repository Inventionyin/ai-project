<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { authHeader, requestJson } from '@/lib/api/client'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || route.params.id || '').trim())

const notifications = ref<any[]>([])
const loading = ref(false)
const error = ref('')

const channelLabels: Record<string, string> = {
  WEBHOOK: 'Webhook',
  EMAIL: '邮件',
  SLACK: 'Slack',
  DINGTALK: '钉钉',
  FEISHU: '飞书',
}

async function load() {
  if (!projectId.value) return
  loading.value = true
  error.value = ''
  try {
    const data = await requestJson<any>(`/projects/${encodeURIComponent(projectId.value)}/integrations/notifications?projectId=${projectId.value}`, {
      method: 'GET',
      headers: authHeader(),
    })
    notifications.value = Array.isArray(data) ? data : data?.items || []
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
      <h1 class="text-[20px] font-semibold text-[#0A0A0A]">告警规则</h1>
      <p class="mt-1 text-[14px] text-[#717182]">配置通知和告警规则（共 {{ notifications.length }} 条）</p>
    </div>

    <div v-if="error" class="mb-4 rounded bg-red-50 p-3 text-[13px] text-red-600">{{ error }}</div>
    <div v-if="loading" class="py-8 text-center text-[14px] text-[#717182]">加载中...</div>

    <div v-else-if="notifications.length === 0" class="py-12 text-center text-[14px] text-[#717182]">
      暂无告警规则。可在「集成配置」页面创建通知规则。
    </div>

    <div v-else class="space-y-3">
      <div v-for="n in notifications" :key="n.id" class="flex items-center justify-between rounded-[10px] border border-black/10 p-4">
        <div>
          <h3 class="text-[14px] font-medium text-[#0A0A0A]">{{ n.name || n.target || '未命名规则' }}</h3>
          <p class="mt-1 text-[12px] text-[#717182]">
            <span class="mr-3">渠道: {{ channelLabels[n.channel] || n.channel }}</span>
            <span>目标: {{ n.target || '-' }}</span>
          </p>
        </div>
        <span
          class="rounded-full px-2 py-0.5 text-[12px] font-medium"
          :class="n.enabled !== false ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
        >
          {{ n.enabled !== false ? '已启用' : '已禁用' }}
        </span>
      </div>
    </div>
  </div>
</template>
