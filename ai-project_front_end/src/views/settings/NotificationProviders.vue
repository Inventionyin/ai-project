<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { authHeader, requestJson } from '@/lib/api/client'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || route.params.id || '').trim())

const providers = ref<any[]>([])
const loading = ref(false)
const error = ref('')
const showAdd = ref(false)
const newProvider = ref({ channel: 'WEBHOOK', name: '', target: '', enabled: true })
const saving = ref(false)

const channelOptions = [
  { value: 'WEBHOOK', label: 'Webhook' },
  { value: 'EMAIL', label: '邮件' },
  { value: 'DINGTALK', label: '钉钉' },
  { value: 'FEISHU', label: '飞书' },
  { value: 'SLACK', label: 'Slack' },
]

async function load() {
  if (!projectId.value) return
  loading.value = true
  error.value = ''
  try {
    const data = await requestJson<any>(`/api/projects/${encodeURIComponent(projectId.value)}/integrations/notifications?projectId=${projectId.value}`, {
      method: 'GET', headers: authHeader(),
    })
    providers.value = Array.isArray(data) ? data : data?.items || []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleAdd() {
  if (!newProvider.value.name.trim()) return
  saving.value = true
  try {
    await requestJson<any>(`/api/projects/${encodeURIComponent(projectId.value)}/integrations/notifications`, {
      method: 'POST',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify(newProvider.value),
    })
    showAdd.value = false
    newProvider.value = { channel: 'WEBHOOK', name: '', target: '', enabled: true }
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '创建失败'
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: string) {
  if (!confirm('确定删除此通知配置？')) return
  try {
    await requestJson<any>(`/api/projects/${encodeURIComponent(projectId.value)}/integrations/notifications/${id}`, {
      method: 'DELETE', headers: authHeader(),
    })
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  }
}

onMounted(load)
watch(projectId, load)
</script>

<template>
  <div class="p-6">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-[20px] font-semibold">通知 Provider 配置</h1>
        <p class="mt-1 text-[14px] text-[#717182]">配置邮件、钉钉、飞书、Slack、Webhook 通知渠道</p>
      </div>
      <button class="rounded-[8px] bg-[#155DFC] px-4 py-2 text-[14px] font-medium text-white" @click="showAdd = true">添加 Provider</button>
    </div>

    <div v-if="error" class="mb-4 rounded bg-red-50 p-3 text-[13px] text-red-600">{{ error }}</div>
    <div v-if="loading" class="py-8 text-center text-[14px] text-[#717182]">加载中...</div>

    <div v-else-if="providers.length === 0" class="py-12 text-center text-[14px] text-[#717182]">暂无通知配置</div>

    <div v-else class="space-y-3">
      <div v-for="p in providers" :key="p.id" class="flex items-center justify-between rounded-[10px] border border-black/10 p-4">
        <div>
          <h3 class="text-[14px] font-medium">{{ p.name || p.target }}</h3>
          <p class="mt-1 text-[12px] text-[#717182]">渠道: {{ p.channel }} | 目标: {{ p.target || '-' }}</p>
        </div>
        <div class="flex items-center gap-2">
          <span class="rounded-full px-2 py-0.5 text-[12px] font-medium" :class="p.enabled !== false ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'">
            {{ p.enabled !== false ? '已启用' : '已禁用' }}
          </span>
          <button class="text-[12px] text-red-500" @click="handleDelete(p.id)">删除</button>
        </div>
      </div>
    </div>

    <!-- Add Modal -->
    <div v-if="showAdd" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div class="w-[420px] rounded-[12px] bg-white p-6 shadow-lg">
        <h2 class="mb-4 text-[16px] font-semibold">添加通知 Provider</h2>
        <div class="mb-3">
          <label class="mb-1 block text-[12px] font-medium text-[#717182]">渠道类型</label>
          <select v-model="newProvider.channel" class="w-full rounded border border-black/10 px-3 py-2 text-[13px]">
            <option v-for="c in channelOptions" :key="c.value" :value="c.value">{{ c.label }}</option>
          </select>
        </div>
        <div class="mb-3">
          <label class="mb-1 block text-[12px] font-medium text-[#717182]">名称</label>
          <input v-model="newProvider.name" type="text" class="w-full rounded border border-black/10 px-3 py-2 text-[13px]" placeholder="例如: 生产环境告警" />
        </div>
        <div class="mb-4">
          <label class="mb-1 block text-[12px] font-medium text-[#717182]">目标地址</label>
          <input v-model="newProvider.target" type="text" class="w-full rounded border border-black/10 px-3 py-2 text-[13px]" placeholder="Webhook URL / 邮箱 / 群 ID" />
        </div>
        <div class="flex justify-end gap-2">
          <button class="rounded border border-black/10 px-4 py-2 text-[13px]" @click="showAdd = false">取消</button>
          <button class="rounded bg-[#155DFC] px-4 py-2 text-[13px] text-white disabled:opacity-50" :disabled="!newProvider.name.trim() || saving" @click="handleAdd">
            {{ saving ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
