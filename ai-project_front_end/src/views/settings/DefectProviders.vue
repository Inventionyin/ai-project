<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  listDefectProviders,
  createDefectProvider,
  deleteDefectProvider,
  type DefectProviderConfigDetail,
  type DefectProviderCreatePayload
} from '@/lib/api/defectProviders'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || '').trim())

const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const saveError = ref('')
const successMessage = ref('')

const providers = ref<DefectProviderConfigDetail[]>([])
const showAddModal = ref(false)

const providerOptions = [
  { value: 'JIRA', label: 'Jira' },
  { value: 'ZENTAO', label: '禅道 (Zentao)' },
  { value: 'TEAMBITION', label: 'Teambition' }
]

const form = ref<DefectProviderCreatePayload>({
  provider: 'JIRA',
  name: '',
  baseUrl: '',
  apiToken: '',
  username: '',
  projectKey: ''
})

function resetForm() {
  form.value = {
    provider: 'JIRA',
    name: '',
    baseUrl: '',
    apiToken: '',
    username: '',
    projectKey: ''
  }
}

function openAddModal() {
  resetForm()
  saveError.value = ''
  showAddModal.value = true
}

function closeAddModal() {
  showAddModal.value = false
  saveError.value = ''
}

async function loadProviders() {
  if (!projectId.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    providers.value = await listDefectProviders(projectId.value)
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!form.value.name.trim()) {
    saveError.value = '请输入配置名称'
    return
  }
  if (!form.value.baseUrl.trim()) {
    saveError.value = '请输入 Base URL'
    return
  }
  saving.value = true
  saveError.value = ''
  try {
    await createDefectProvider(projectId.value, form.value)
    successMessage.value = '创建成功'
    showAddModal.value = false
    await loadProviders()
    setTimeout(() => { successMessage.value = '' }, 3000)
  } catch (e: unknown) {
    saveError.value = e instanceof Error ? e.message : '创建失败'
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: string, name: string) {
  if (!confirm(`确定删除配置「${name}」吗？`)) return
  try {
    await deleteDefectProvider(projectId.value, id)
    successMessage.value = '删除成功'
    await loadProviders()
    setTimeout(() => { successMessage.value = '' }, 3000)
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '删除失败'
  }
}

function formatSyncTime(ts: number | null): string {
  if (!ts) return '从未同步'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

function syncStatusText(status: string): string {
  switch (status) {
    case 'IDLE': return '空闲'
    case 'SYNCING': return '同步中'
    case 'ERROR': return '错误'
    default: return status
  }
}

function syncStatusClass(status: string): string {
  switch (status) {
    case 'IDLE': return 'text-green-600 bg-green-50'
    case 'SYNCING': return 'text-blue-600 bg-blue-50'
    case 'ERROR': return 'text-red-600 bg-red-50'
    default: return 'text-gray-600 bg-gray-50'
  }
}

function providerLabel(provider: string): string {
  const opt = providerOptions.find(o => o.value === provider)
  return opt ? opt.label : provider
}

onMounted(loadProviders)
</script>

<template>
  <div class="p-6 max-w-[1200px] mx-auto">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-[#0A0A0A]">缺陷系统对接</h1>
        <p class="text-sm text-[rgba(10,10,10,0.5)] mt-1">配置 Jira、禅道、Teambition 等第三方缺陷管理系统的连接</p>
      </div>
      <button
        type="button"
        class="px-4 py-2 bg-[#155DFC] text-white rounded-lg text-sm font-medium hover:bg-[#0D47C4] transition-colors"
        @click="openAddModal"
      >
        添加配置
      </button>
    </div>

    <div v-if="errorMessage" class="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">{{ errorMessage }}</div>
    <div v-if="successMessage" class="mb-4 p-3 bg-green-50 text-green-600 rounded-lg text-sm">{{ successMessage }}</div>

    <div v-if="loading" class="text-center py-12 text-[rgba(10,10,10,0.5)]">加载中...</div>

    <div v-else-if="providers.length === 0" class="text-center py-16 bg-[#FAFAFA] rounded-xl border border-[#E5E5E5]">
      <div class="text-[rgba(10,10,10,0.4)] text-lg mb-2">暂无配置</div>
      <div class="text-[rgba(10,10,10,0.3)] text-sm">点击「添加配置」开始连接缺陷管理系统</div>
    </div>

    <div v-else class="grid gap-4">
      <div
        v-for="item in providers"
        :key="item.id"
        class="bg-white rounded-xl border border-[#E5E5E5] p-5 hover:shadow-sm transition-shadow"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <div class="flex items-center gap-3 mb-2">
              <span class="px-2 py-0.5 bg-[#F0F4FF] text-[#155DFC] rounded text-xs font-medium">
                {{ providerLabel(item.provider) }}
              </span>
              <span class="font-medium text-[#0A0A0A]">{{ item.name }}</span>
              <span
                v-if="!item.enabled"
                class="px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs"
              >已禁用</span>
            </div>
            <div class="text-sm text-[rgba(10,10,10,0.6)] mb-2">{{ item.baseUrl }}</div>
            <div class="flex items-center gap-4 text-xs text-[rgba(10,10,10,0.45)]">
              <span>
                状态：
                <span :class="syncStatusClass(item.syncStatus)" class="px-1.5 py-0.5 rounded">
                  {{ syncStatusText(item.syncStatus) }}
                </span>
              </span>
              <span>上次同步：{{ formatSyncTime(item.lastSyncAt) }}</span>
            </div>
            <div v-if="item.lastError" class="mt-2 text-xs text-red-500 bg-red-50 px-2 py-1 rounded">
              {{ item.lastError }}
            </div>
          </div>
          <button
            type="button"
            class="px-3 py-1.5 text-sm text-red-500 hover:bg-red-50 rounded-lg transition-colors"
            @click="handleDelete(item.id, item.name)"
          >
            删除
          </button>
        </div>
      </div>
    </div>

    <!-- Add Modal -->
    <Teleport to="body">
      <div
        v-if="showAddModal"
        class="fixed inset-0 z-50 flex items-center justify-center"
      >
        <div class="absolute inset-0 bg-black/30" @click="closeAddModal"></div>
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6">
          <h2 class="text-lg font-semibold text-[#0A0A0A] mb-4">添加缺陷系统配置</h2>

          <div v-if="saveError" class="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">{{ saveError }}</div>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-[#0A0A0A] mb-1">系统类型</label>
              <select
                v-model="form.provider"
                class="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
              >
                <option v-for="opt in providerOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-[#0A0A0A] mb-1">配置名称</label>
              <input
                v-model="form.name"
                type="text"
                placeholder="例如：生产环境 Jira"
                class="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-[#0A0A0A] mb-1">Base URL</label>
              <input
                v-model="form.baseUrl"
                type="text"
                placeholder="https://your-domain.atlassian.net"
                class="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-[#0A0A0A] mb-1">API Token</label>
              <input
                v-model="form.apiToken"
                type="password"
                placeholder="输入 API Token"
                class="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-[#0A0A0A] mb-1">用户名</label>
              <input
                v-model="form.username"
                type="text"
                placeholder="输入用户名（可选）"
                class="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-[#0A0A0A] mb-1">项目 Key</label>
              <input
                v-model="form.projectKey"
                type="text"
                placeholder="例如：PROJ"
                class="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
              />
            </div>
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button
              type="button"
              class="px-4 py-2 text-sm text-[rgba(10,10,10,0.7)] hover:bg-[#F5F5F5] rounded-lg transition-colors"
              @click="closeAddModal"
            >
              取消
            </button>
            <button
              type="button"
              class="px-4 py-2 bg-[#155DFC] text-white rounded-lg text-sm font-medium hover:bg-[#0D47C4] transition-colors disabled:opacity-50"
              :disabled="saving"
              @click="handleCreate"
            >
              {{ saving ? '创建中...' : '创建' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
