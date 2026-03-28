<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import modalClose from '@/assets/figma/ai-testing-platform/modal-close.svg'
import { createTestcaseBinding, deleteTestcaseBinding, fetchApiTargets, fetchTestcaseBindings, updateTestcaseBinding, type ApiTarget, type TestcaseBinding } from '@/lib/aiTestingPlatformApi'

const props = defineProps<{
  isOpen: boolean
  testcaseId: string
  testcaseTitle: string
  projectId: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'changed'): void
}>()

function showToast(message: string, type: 'success' | 'error' = 'success') {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, type } }))
}

type EditableBinding = TestcaseBinding & { _isNew?: boolean; _isSaving?: boolean; _isDeleting?: boolean }

const isLoading = ref(false)
const loadError = ref('')
const apiTargets = ref<ApiTarget[]>([])
const bindings = ref<EditableBinding[]>([])

const apiTargetOptions = computed(() => {
  const list = Array.isArray(apiTargets.value) ? apiTargets.value : []
  return list
    .filter((t) => t && typeof t.id === 'string' && t.id.trim().length > 0)
    .map((t) => ({
      id: t.id,
      label: t.name || (t.method && t.path ? `${t.method} ${t.path}` : t.id.slice(0, 8))
    }))
})

async function loadData() {
  const id = String(props.testcaseId || '').trim()
  if (!id) return

  isLoading.value = true
  loadError.value = ''
  try {
    const [targets, list] = await Promise.all([fetchApiTargets(props.projectId), fetchTestcaseBindings(id)])
    apiTargets.value = Array.isArray(targets) ? targets : []
    bindings.value = Array.isArray(list)
      ? list.map((b) => ({ ...b, _isNew: false, _isSaving: false, _isDeleting: false }))
      : []
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '加载失败'
    apiTargets.value = []
    bindings.value = []
  } finally {
    isLoading.value = false
  }
}

watch(
  () => props.isOpen,
  (open) => {
    if (!open) return
    void loadData()
  },
  { immediate: true }
)

function close() {
  emit('close')
}

function addBinding() {
  const testcaseId = String(props.testcaseId || '').trim()
  if (!testcaseId) return
  bindings.value.unshift({
    id: `new_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`,
    name: '',
    apiTargetId: null,
    datasetId: null,
    datasetName: null,
    _isNew: true,
    _isSaving: false,
    _isDeleting: false
  })
}

function removeLocal(index: number) {
  if (index < 0 || index >= bindings.value.length) return
  bindings.value.splice(index, 1)
}

async function saveBinding(item: EditableBinding) {
  const testcaseId = String(props.testcaseId || '').trim()
  const name = String(item.name || '').trim()
  if (!name) {
    showToast('绑定名称不能为空', 'error')
    return
  }
  if (item._isSaving) return

  item._isSaving = true
  try {
    if (item._isNew) {
      const created = await createTestcaseBinding(testcaseId, {
        name,
        apiTargetId: item.apiTargetId || null,
        datasetId: item.datasetId || null,
        datasetName: item.datasetName || null,
        params: item.params || null,
        priority: Number.isFinite(Number(item.priority)) ? Number(item.priority) : null,
        enabled: item.enabled !== false
      })
      const idx = bindings.value.findIndex((b) => b.id === item.id)
      if (idx >= 0) {
        bindings.value[idx] = { ...created, _isNew: false, _isSaving: false, _isDeleting: false }
      }
    } else {
      const version = Number(item.version)
      if (!Number.isFinite(version)) {
        showToast('绑定版本缺失，请刷新后重试', 'error')
        return
      }
      const updated = await updateTestcaseBinding(item.id, {
        name,
        apiTargetId: item.apiTargetId || null,
        datasetId: item.datasetId || null,
        datasetName: item.datasetName || null,
        params: item.params || null,
        priority: Number.isFinite(Number(item.priority)) ? Number(item.priority) : null,
        enabled: item.enabled !== false,
        version
      })
      const idx = bindings.value.findIndex((b) => b.id === item.id)
      if (idx >= 0) {
        bindings.value[idx] = { ...bindings.value[idx], ...updated, _isNew: false, _isSaving: false }
      }
    }
    showToast('已保存')
    emit('changed')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '保存失败', 'error')
  } finally {
    item._isSaving = false
  }
}

async function removeBinding(item: EditableBinding, index: number) {
  if (item._isDeleting) return
  if (item._isNew) {
    removeLocal(index)
    return
  }
  if (!window.confirm(`确认删除绑定「${item.name}」吗？`)) return
  item._isDeleting = true
  try {
    await deleteTestcaseBinding(item.id)
    removeLocal(index)
    showToast('已删除')
    emit('changed')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '删除失败', 'error')
  } finally {
    item._isDeleting = false
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.isOpen) {
    close()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})

const testcaseLabel = computed(() => String(props.testcaseTitle || '').trim() || String(props.testcaseId || '').slice(0, 8))
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
    <button class="absolute inset-0 bg-black/40" type="button" aria-label="Close" @click="close" />

    <div class="relative w-[calc(100vw-32px)] max-w-[672px] overflow-hidden rounded-[16px] bg-white shadow-[0px_25px_50px_-12px_rgba(0,0,0,0.25)]">
      <div class="flex h-[74.67px] w-full items-center justify-between border-b border-black/10 pl-[20px] pr-[20px]">
        <div class="flex flex-col gap-[2px]">
          <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">绑定配置管理</div>
          <div class="text-[12px] leading-[16px] text-[#717182]">
            {{ testcaseLabel }}
          </div>
        </div>

        <button type="button" class="h-[27px] w-[27px] rounded-[10px] px-[6px] pt-[6px] pb-0" @click="close">
          <img :src="modalClose" alt="" class="h-[15px] w-[15px]" />
        </button>
      </div>

      <div class="w-full overflow-y-auto p-[20px]" style="max-height: calc(100vh - 74.67px - 32px)">
        <div class="mb-[12px] flex items-center justify-between">
          <div class="text-[12px] leading-[16px] text-[#717182]">
            {{ isLoading ? '加载中…' : `共 ${bindings.length} 个绑定` }}
            <span v-if="loadError" class="ml-[8px] text-[#FB2C36]">{{ loadError }}</span>
          </div>
          <button type="button" class="h-[32px] rounded-[10px] bg-[#155DFC] px-[12px] text-[14px] font-medium leading-[20px] text-white" @click="addBinding">
            新增绑定
          </button>
        </div>

        <div class="flex flex-col gap-[10px]">
          <div
            v-for="(item, index) in bindings"
            :key="item.id"
            class="rounded-[14px] border border-black/10 bg-white p-[12px]"
          >
            <div class="grid grid-cols-1 gap-[10px] md:grid-cols-3">
              <div class="flex flex-col gap-[6px]">
                <div class="text-[12px] font-medium leading-[16px] text-[#717182]">名称 *</div>
                <input
                  v-model="item.name"
                  type="text"
                  class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
                  placeholder="例如：订单-默认绑定"
                />
              </div>

              <div class="flex flex-col gap-[6px]">
                <div class="text-[12px] font-medium leading-[16px] text-[#717182]">接口目标</div>
                <select
                  v-model="item.apiTargetId"
                  class="h-[36px] w-full appearance-none rounded-[10px] border border-black/10 bg-white px-[12px] pr-[36px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
                >
                  <option :value="null">未选择</option>
                  <option v-for="opt in apiTargetOptions" :key="opt.id" :value="opt.id">
                    {{ opt.label }}
                  </option>
                </select>
              </div>

              <div class="flex flex-col gap-[6px]">
                <div class="text-[12px] font-medium leading-[16px] text-[#717182]">数据集（可选）</div>
                <input
                  v-model="item.datasetName"
                  type="text"
                  class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
                  placeholder="例如：用户测试数据集"
                />
              </div>
            </div>

            <div class="mt-[12px] flex items-center justify-end gap-[8px]">
              <button
                type="button"
                class="h-[32px] rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] font-medium leading-[20px] text-[#0A0A0A]"
                :disabled="item._isSaving || item._isDeleting"
                @click="saveBinding(item)"
              >
                {{ item._isSaving ? '保存中…' : '保存' }}
              </button>
              <button
                type="button"
                class="h-[32px] rounded-[10px] border border-[#FB2C36]/30 bg-white px-[12px] text-[14px] font-medium leading-[20px] text-[#FB2C36]"
                :disabled="item._isSaving || item._isDeleting"
                @click="removeBinding(item, index)"
              >
                {{ item._isDeleting ? '删除中…' : '删除' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

