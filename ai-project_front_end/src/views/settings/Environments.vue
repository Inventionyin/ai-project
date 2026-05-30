<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  createEnvironment,
  deleteEnvironment,
  listEnvironments,
  updateEnvironment,
  type EnvironmentPublic,
  type EnvironmentUpsertPayload,
  type HealthCheckConfig
} from '@/lib/api/environments'
import { confirmAction } from '@/lib/ui/confirm'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || '').trim())

const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const saveError = ref('')
const successMessage = ref('')

const environments = ref<EnvironmentPublic[]>([])
const selectedId = ref('')
const mode = ref<'create' | 'edit'>('create')

const form = ref({
  name: '',
  baseUrl: '',
  variablesJson: '{}',
  secretsJson: '{}',
  healthCheckEnabled: false,
  healthUrl: '',
  healthTimeoutMs: 3000,
  healthExpectedStatus: 200
})

const selectedEnvironment = computed(() => environments.value.find((item: EnvironmentPublic) => item.id === selectedId.value) || null)

function resetForm() {
  form.value = {
    name: '',
    baseUrl: '',
    variablesJson: '{}',
    secretsJson: '{}',
    healthCheckEnabled: false,
    healthUrl: '',
    healthTimeoutMs: 3000,
    healthExpectedStatus: 200
  }
}

function applyEnvironment(env: EnvironmentPublic) {
  mode.value = 'edit'
  selectedId.value = env.id
  form.value = {
    name: env.name,
    baseUrl: env.baseUrl,
    variablesJson: JSON.stringify(env.variables || {}, null, 2),
    secretsJson: '{}',
    healthCheckEnabled: Boolean(env.healthCheck),
    healthUrl: env.healthCheck?.url || '',
    healthTimeoutMs: env.healthCheck?.timeoutMs || 3000,
    healthExpectedStatus: env.healthCheck?.expectedStatus || 200
  }
}

function startCreate() {
  mode.value = 'create'
  selectedId.value = ''
  saveError.value = ''
  successMessage.value = ''
  resetForm()
}

function parseJsonObject(label: string, source: string) {
  const text = String(source || '').trim() || '{}'
  let value: unknown
  try {
    value = JSON.parse(text)
  } catch {
    throw new Error(`${label} 不是合法 JSON`)
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${label} 必须是 JSON 对象`)
  }
  const entries = Object.entries(value as Record<string, unknown>)
  const mapped = entries.reduce<Record<string, string>>((acc, [key, val]) => {
    acc[String(key)] = String(val ?? '')
    return acc
  }, {})
  return mapped
}

function buildPayload(): EnvironmentUpsertPayload {
  const name = form.value.name.trim()
  const baseUrl = form.value.baseUrl.trim()
  if (!name) throw new Error('环境名称不能为空')
  if (!baseUrl) throw new Error('Base URL 不能为空')

  const variables = parseJsonObject('变量', form.value.variablesJson)
  const secrets = parseJsonObject('密钥', form.value.secretsJson)

  let healthCheck: HealthCheckConfig | null = null
  if (form.value.healthCheckEnabled) {
    const url = form.value.healthUrl.trim()
    if (!url) throw new Error('健康检查 URL 不能为空')
    healthCheck = {
      url,
      timeoutMs: Math.max(1, Math.min(60000, Math.floor(Number(form.value.healthTimeoutMs) || 3000))),
      expectedStatus: Math.max(100, Math.min(599, Math.floor(Number(form.value.healthExpectedStatus) || 200)))
    }
  }

  return { name, baseUrl, variables, secrets, healthCheck }
}

async function loadEnvironments() {
  if (!projectId.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    environments.value = await listEnvironments(projectId.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载环境失败'
  } finally {
    loading.value = false
  }
}

async function submit() {
  saveError.value = ''
  successMessage.value = ''
  saving.value = true
  try {
    const payload = buildPayload()
    if (mode.value === 'create') {
      const created = await createEnvironment(projectId.value, payload)
      await loadEnvironments()
      applyEnvironment(created)
      successMessage.value = '环境创建成功'
    } else {
      if (!selectedId.value) throw new Error('请选择要编辑的环境')
      const updated = await updateEnvironment(projectId.value, selectedId.value, payload)
      await loadEnvironments()
      applyEnvironment(updated)
      successMessage.value = '环境更新成功'
    }
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function removeEnv(env: EnvironmentPublic) {
  const ok = await confirmAction(`确认删除环境「${env.name}」吗？`)
  if (!ok) return
  saveError.value = ''
  successMessage.value = ''
  try {
    await deleteEnvironment(projectId.value, env.id)
    if (selectedId.value === env.id) startCreate()
    await loadEnvironments()
    successMessage.value = '环境删除成功'
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : '删除失败'
  }
}

onMounted(async () => {
  startCreate()
  await loadEnvironments()
})
</script>

<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-4 md:p-6">
    <div class="grid grid-cols-1 gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
      <section class="rounded-[12px] border border-black/10 bg-white p-4">
        <div class="flex items-center justify-between">
          <h2 class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">环境列表</h2>
          <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px]" @click="startCreate">新建环境</button>
        </div>

        <div v-if="loading" class="mt-4 text-[12px] text-[#717182]">加载中...</div>
        <div v-else-if="errorMessage" class="mt-4 rounded-[8px] border border-[#FB2C36]/30 bg-[#FEF2F2] p-2 text-[12px] text-[#B91C1C]">
          {{ errorMessage }}
        </div>
        <div v-else-if="environments.length === 0" class="mt-4 rounded-[8px] border border-dashed border-black/10 p-4 text-[12px] text-[#717182]">
          暂无环境，请先创建。
        </div>

        <div v-else class="mt-4 space-y-2">
          <div
            v-for="env in environments"
            :key="env.id"
            class="rounded-[8px] border p-3"
            :class="selectedId === env.id ? 'border-[#155DFC] bg-[#EFF6FF]' : 'border-black/10 bg-white'"
          >
            <div class="flex items-start justify-between gap-2">
              <button class="min-w-0 flex-1 text-left" @click="applyEnvironment(env)">
                <div class="truncate text-[13px] font-medium text-[#0A0A0A]">{{ env.name }}</div>
                <div class="mt-1 truncate text-[12px] text-[#717182]">{{ env.baseUrl }}</div>
                <div class="mt-1 text-[11px] text-[#717182]">secretKeys: {{ env.secretKeys.join(', ') || '-' }}</div>
              </button>
              <button class="rounded-[6px] border border-[#FB2C36]/30 px-2 py-1 text-[11px] text-[#B91C1C]" @click="removeEnv(env)">删除</button>
            </div>
          </div>
        </div>
      </section>

      <section class="rounded-[12px] border border-black/10 bg-white p-4">
        <h2 class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">
          {{ mode === 'create' ? '新建环境' : `编辑环境 · ${selectedEnvironment?.name || ''}` }}
        </h2>

        <div class="mt-4 grid grid-cols-1 gap-3">
          <label class="text-[12px] text-[#717182]">
            名称
            <input v-model="form.name" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
          </label>

          <label class="text-[12px] text-[#717182]">
            Base URL
            <input v-model="form.baseUrl" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A] outline-none" />
          </label>

          <label class="text-[12px] text-[#717182]">
            Variables (JSON 对象)
            <textarea v-model="form.variablesJson" rows="6" class="mt-1 w-full rounded-[8px] border border-black/10 p-3 text-[12px] text-[#0A0A0A] outline-none" />
          </label>

          <label class="text-[12px] text-[#717182]">
            Secrets (JSON 对象，输入时可见)
            <textarea v-model="form.secretsJson" rows="4" class="mt-1 w-full rounded-[8px] border border-black/10 p-3 text-[12px] text-[#0A0A0A] outline-none" />
          </label>

          <label class="flex items-center gap-2 text-[12px] text-[#0A0A0A]">
            <input v-model="form.healthCheckEnabled" type="checkbox" class="h-4 w-4 accent-[#155DFC]" />
            启用健康检查
          </label>

          <div v-if="form.healthCheckEnabled" class="grid grid-cols-1 gap-3 rounded-[8px] border border-black/10 bg-[#FAFAFA] p-3 md:grid-cols-3">
            <label class="text-[12px] text-[#717182] md:col-span-3">
              Health URL
              <input v-model="form.healthUrl" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none" />
            </label>
            <label class="text-[12px] text-[#717182]">
              Timeout(ms)
              <input v-model.number="form.healthTimeoutMs" type="number" min="1" max="60000" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none" />
            </label>
            <label class="text-[12px] text-[#717182]">
              Expected Status
              <input v-model.number="form.healthExpectedStatus" type="number" min="100" max="599" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none" />
            </label>
          </div>
        </div>

        <div v-if="saveError" class="mt-4 rounded-[8px] border border-[#FB2C36]/30 bg-[#FEF2F2] p-2 text-[12px] text-[#B91C1C]">{{ saveError }}</div>
        <div v-if="successMessage" class="mt-4 rounded-[8px] border border-[#00A63E]/30 bg-[#F0FDF4] p-2 text-[12px] text-[#166534]">{{ successMessage }}</div>

        <div class="mt-4 flex items-center gap-2">
          <button
            class="h-9 rounded-[8px] bg-[#155DFC] px-4 text-[13px] font-medium text-white disabled:opacity-60"
            :disabled="saving"
            @click="submit"
          >
            {{ saving ? '保存中...' : mode === 'create' ? '创建环境' : '保存修改' }}
          </button>
          <button class="h-9 rounded-[8px] border border-black/10 px-4 text-[13px]" @click="startCreate">重置为新建</button>
        </div>
      </section>
    </div>
  </div>
</template>
