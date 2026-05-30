<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import modalClose from '@/assets/figma/ai-testing-platform/modal-close.svg'
import { importTestcases, type TestCaseImportData } from '@/lib/aiTestingPlatformApi'

const props = defineProps<{
  isOpen: boolean
  projectId: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'imported', data: TestCaseImportData): void
}>()

const file = ref<File | null>(null)
const isUploading = ref(false)
const result = ref<TestCaseImportData | null>(null)

const fileLabel = computed(() => {
  if (!file.value) return '未选择文件'
  const size = file.value.size
  const kb = Math.round(size / 1024)
  return `${file.value.name}（${kb} KB）`
})

function showToast(message: string, type: 'success' | 'error' = 'success') {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, type } }))
}

function reset() {
  file.value = null
  isUploading.value = false
  result.value = null
}

watch(
  () => props.isOpen,
  (open) => {
    if (open) reset()
  }
)

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0] || null
  if (!f) {
    file.value = null
    return
  }
  const name = String(f.name || '').toLowerCase()
  if (!name.endsWith('.csv') && !name.endsWith('.xlsx')) {
    showToast('仅支持 CSV/XLSX 文件', 'error')
    input.value = ''
    file.value = null
    return
  }
  file.value = f
}

async function handleImport() {
  if (!file.value) {
    showToast('请选择 CSV/XLSX 文件', 'error')
    return
  }
  isUploading.value = true
  try {
    const data = await importTestcases({ projectId: props.projectId, file: file.value, mode: 'partial' })
    result.value = data
    emit('imported', data)
    if (data.failedCount === 0) {
      emit('close')
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : '导入失败'
    showToast(msg, 'error')
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50">
    <button class="absolute inset-0 bg-black/40" type="button" aria-label="Close" @click="emit('close')" />

    <div class="absolute inset-y-0 right-0 z-10 flex h-full w-full max-w-[560px] flex-col bg-white px-[24px] pb-[24px] pt-[24px] shadow-[-10px_0_30px_-12px_rgba(0,0,0,0.3)]">
      <div class="flex items-center justify-between">
        <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">导入用例</div>
        <button type="button" class="h-[18px] w-[18px]" aria-label="Close" @click="emit('close')">
          <img :src="modalClose" alt="" class="h-full w-full" />
        </button>
      </div>

      <div class="mt-[20px] flex-1 overflow-auto">
        <div class="flex flex-col gap-[12px]">
          <div class="flex flex-col gap-[6px]">
            <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
              选择文件 <span class="text-[#FB2C36]">*</span>
            </div>
            <div class="flex items-center gap-[10px]">
              <label class="inline-flex h-[32px] cursor-pointer items-center rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A]">
                <input class="hidden" type="file" accept=".csv,.xlsx" @change="onFileChange" />
                选择文件
              </label>
              <div class="text-[12px] leading-[16px] text-[#717182]">{{ fileLabel }}</div>
            </div>
            <div class="text-[12px] leading-[16px] text-[#717182]">支持 CSV / XLSX；表头需与模板一致</div>
          </div>

          <div v-if="result" class="rounded-[12px] border border-black/10 bg-[#FAFAFC] p-[12px]">
            <div class="text-[13px] leading-[18px] text-[#0A0A0A]">
              已导入 {{ result.importedCount }} 条，失败 {{ result.failedCount }} 条
            </div>
            <div v-if="result.failedCount > 0" class="mt-[10px] max-h-[260px] overflow-auto rounded-[10px] border border-black/10 bg-white">
              <div
                v-for="(err, i) in result.errors"
                :key="`${err.rowNumber}-${i}`"
                class="border-b border-black/5 px-[10px] py-[8px] text-[12px] leading-[16px] text-[#0A0A0A]"
              >
                第 {{ err.rowNumber }} 行：{{ err.message }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="mt-[16px] flex items-center justify-end gap-[10px]">
        <button
          type="button"
          class="h-[32px] rounded-[10px] border border-black/10 bg-white px-[14px] text-[14px] font-medium leading-[20px] text-[#0A0A0A]"
          :disabled="isUploading"
          @click="emit('close')"
        >
          取消
        </button>
        <button
          type="button"
          class="h-[32px] rounded-[10px] bg-[#155DFC] px-[14px] text-[14px] font-medium leading-[20px] text-white disabled:cursor-not-allowed disabled:bg-black/20"
          :disabled="isUploading"
          @click="handleImport"
        >
          {{ isUploading ? '导入中...' : '确定' }}
        </button>
      </div>
    </div>
  </div>
</template>

