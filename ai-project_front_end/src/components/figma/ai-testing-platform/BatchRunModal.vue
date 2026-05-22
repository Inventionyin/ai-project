<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import BatchRunModalHeader from '@/components/figma/ai-testing-platform/BatchRunModalHeader.vue'
import BatchRunStepIndicator from '@/components/figma/ai-testing-platform/BatchRunStepIndicator.vue'
import BatchRunCaseBindingTable, { type BatchRunCaseRow } from '@/components/figma/ai-testing-platform/BatchRunCaseBindingTable.vue'
import BatchRunDataBindingStep from '@/components/figma/ai-testing-platform/BatchRunDataBindingStep.vue'
import BatchRunExecutionParamsStep from '@/components/figma/ai-testing-platform/BatchRunExecutionParamsStep.vue'
import BatchRunModalFooter from '@/components/figma/ai-testing-platform/BatchRunModalFooter.vue'
import { fetchApiTargets, fetchBindingsByTestcaseIds, fetchProjectEnvironments, type ApiTarget, type BatchRunFormState } from '@/lib/aiTestingPlatformApi'

const props = defineProps<{
  isOpen: boolean
  selectedCount: number
  projectId: string
  rows?: BatchRunCaseRow[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'next'): void
  (e: 'prev'): void
  (e: 'execute', payload: { formState: BatchRunFormState; idempotencyKey: string }): void
  (e: 'apply-all'): void
}>()

function showToast(message: string, type: 'success' | 'error' = 'success') {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, type } }))
}

const currentStep = ref<1 | 2 | 3>(1)
const localRows = ref<BatchRunCaseRow[]>([])
const overrideParamsTextById = ref<Record<string, string>>({})
const overrideErrorsById = ref<Record<string, string>>({})
const envId = ref('')
const environments = ref<Array<{ id: string; name: string; baseUrl: string }>>([])
const concurrency = ref(5)
const stopOnFailure = ref(false)
const notifyOnFail = ref(false)
const idempotencyKey = ref('')
const bindingsByCaseId = ref<Record<string, Array<{ value: string; label: string }>>>({})
const apiTargetById = ref<Record<string, ApiTarget>>({})

const boundCount = computed(() => localRows.value.filter((row) => String(row.bindingId || '').trim().length > 0).length)

const dataBindingRows = computed(() => {
  const map = overrideParamsTextById.value
  return localRows.value.map((row) => ({
    id: row.id,
    title: row.title,
    priority: row.priority,
    overrideParamsText: map[row.id] || ''
  }))
})

function resetState() {
  currentStep.value = 1
  localRows.value = (props.rows ?? []).map((row) => ({ ...row }))
  overrideParamsTextById.value = {}
  overrideErrorsById.value = {}
  envId.value = ''
  environments.value = []
  bindingsByCaseId.value = {}
  apiTargetById.value = {}
  concurrency.value = 5
  stopOnFailure.value = false
  notifyOnFail.value = false
  idempotencyKey.value = `ik_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

async function loadBindingsAndEnvironments() {
  const caseIds = localRows.value.map((r) => r.id)
  if (!props.projectId || !caseIds.length) return

  try {
    const [targets, envs, bindingsMap] = await Promise.all([
      fetchApiTargets(props.projectId),
      fetchProjectEnvironments(props.projectId),
      fetchBindingsByTestcaseIds(caseIds)
    ])
    apiTargetById.value = Array.isArray(targets)
      ? targets.reduce<Record<string, ApiTarget>>((acc, item) => {
          if (!item?.id) return acc
          acc[item.id] = item
          return acc
        }, {})
      : {}
    environments.value = Array.isArray(envs) ? envs : []
    envId.value = environments.value[0]?.id || ''

    const byCaseId: Record<string, Array<{ value: string; label: string }>> = {}
    for (const id of caseIds) {
      const bindings = bindingsMap[id] || []
      byCaseId[id] = bindings
        .filter((b) => b && typeof b.id === 'string' && b.id.trim().length > 0)
        .map((b) => {
          const apiTarget = b.apiTargetId ? apiTargetById.value[b.apiTargetId] : undefined
          const apiSummary = apiTarget?.name || apiTarget?.baseUrl || b.apiTargetId || '未关联接口目标'
          const datasetSummary = b.datasetName || b.datasetId || '无数据集'
          const label = `${b.name} · ${apiSummary} · ${datasetSummary}`
          return { value: b.id, label }
        })
    }
    bindingsByCaseId.value = byCaseId
  } catch (error) {
    showToast(error instanceof Error ? error.message : '加载绑定配置/环境失败', 'error')
  }
}

watch(
  () => props.isOpen,
  (isOpen) => {
    if (!isOpen) return
    resetState()
    void loadBindingsAndEnvironments()
  },
  { immediate: true }
)

function updateRowBinding(payload: { id: string; bindingId: string }) {
  const next = localRows.value.map((row) => (row.id === payload.id ? { ...row, bindingId: payload.bindingId } : row))
  localRows.value = next
}

function updateRowOverride(payload: { id: string; overrideParamsText: string }) {
  overrideParamsTextById.value = { ...overrideParamsTextById.value, [payload.id]: payload.overrideParamsText }
}

function nextStep() {
  if (currentStep.value === 1) {
    const missing = localRows.value.filter((row) => !String(row.bindingId || '').trim()).length
    if (missing > 0) {
      showToast(`还有 ${missing} 条用例未选择绑定配置`, 'error')
      return
    }
    currentStep.value = 2
    emit('next')
    return
  }
  if (currentStep.value === 2) {
    const nextErrors: Record<string, string> = {}
    for (const row of localRows.value) {
      const text = String(overrideParamsTextById.value[row.id] || '').trim()
      if (!text) continue
      try {
        JSON.parse(text)
      } catch {
        nextErrors[row.id] = '参数覆盖需为合法 JSON'
      }
    }
    overrideErrorsById.value = nextErrors
    const errorCount = Object.keys(nextErrors).length
    if (errorCount > 0) {
      showToast(`参数覆盖需为合法 JSON：${errorCount} 条用例`, 'error')
      return
    }
    currentStep.value = 3
    emit('next')
    return
  }
  emit('next')
}

function prevStep() {
  if (currentStep.value === 3) {
    currentStep.value = 2
    emit('prev')
    return
  }
  if (currentStep.value === 2) {
    currentStep.value = 1
    emit('prev')
  }
}

function executeRun() {
  const pid = String(props.projectId || '').trim()
  if (!pid) return
  const selectedEnvId = String(envId.value || '').trim()
  if (!selectedEnvId) {
    showToast('请选择执行环境', 'error')
    return
  }
  const missing = localRows.value.filter((row) => !String(row.bindingId || '').trim()).length
  if (missing > 0) {
    showToast(`还有 ${missing} 条用例未选择绑定配置`, 'error')
    currentStep.value = 1
    return
  }

  const items = localRows.value.map((row) => {
    const text = String(overrideParamsTextById.value[row.id] || '').trim()
    if (!text) {
      return { testcaseId: row.id, bindingId: row.bindingId }
    }
    return { testcaseId: row.id, bindingId: row.bindingId, overrideParams: JSON.parse(text) }
  })

  emit('execute', {
    formState: {
      projectId: pid,
      envId: selectedEnvId,
      triggerType: 'MANUAL',
      meta: { source: 'BatchRunModal', notifyOnFail: notifyOnFail.value },
      concurrency: concurrency.value,
      stopOnFailure: stopOnFailure.value,
      items
    },
    idempotencyKey: idempotencyKey.value
  })
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.isOpen) {
    emit('close')
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
    <div class="absolute inset-0 bg-black/40" @click="emit('close')"></div>

    <div
      class="relative w-[calc(100vw-32px)] max-w-[672px] overflow-hidden rounded-[16px] bg-white shadow-[0px_25px_50px_-12px_rgba(0,0,0,0.25)]"
      style="height: min(483.59px, calc(100vh - 32px))"
    >
      <BatchRunModalHeader :selected-count="selectedCount" :bound-count="boundCount" @close="emit('close')" />

      <div class="w-full overflow-y-auto" style="height: min(340.26px, calc(100vh - 74.67px - 68.67px - 32px))">
        <div class="flex h-full w-full flex-col pl-[20px] pr-[20px] pt-[16px] md:pr-[36.67px]">
          <div v-if="currentStep === 1" class="flex h-full w-full flex-col">
            <div class="mt-[16px] shrink-0">
              <BatchRunStepIndicator :active-step="currentStep" />
            </div>
            <div class="mt-[20px] min-h-0 flex-1">
              <BatchRunCaseBindingTable
                class="h-full"
                :rows="localRows"
                :options-by-case-id="bindingsByCaseId"
                @update-row-binding="updateRowBinding"
              />
            </div>
          </div>

          <div v-else-if="currentStep === 2" class="w-full">
            <BatchRunDataBindingStep :rows="dataBindingRows" :errors-by-id="overrideErrorsById" @update-row-override="updateRowOverride" />
          </div>

          <div v-else class="w-full">
            <BatchRunExecutionParamsStep
              :env-id="envId"
              :environments="environments"
              :concurrency="concurrency"
              :stop-on-failure="stopOnFailure"
              :notify-on-fail="notifyOnFail"
              :idempotency-key="idempotencyKey"
              @update:env-id="envId = $event"
              @update:concurrency="concurrency = $event"
              @update:stop-on-failure="stopOnFailure = $event"
              @update:notify-on-fail="notifyOnFail = $event"
            />
          </div>
        </div>
      </div>

      <BatchRunModalFooter
        :step="currentStep"
        :execute-count="selectedCount"
        @cancel="emit('close')"
        @next="nextStep"
        @prev="prevStep"
        @execute="executeRun"
      />
    </div>
  </div>
</template>
