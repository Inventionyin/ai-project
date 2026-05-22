<script setup lang="ts">
import { reactive } from 'vue'
import modalClose28 from '@/assets/figma/ai-testing-platform/modal-close-28.svg'
import modalDescIcon from '@/assets/figma/ai-testing-platform/modal-desc-icon.svg'
import modalCreateIcon from '@/assets/figma/ai-testing-platform/modal-create-icon.svg'

defineProps<{
  isOpen: boolean
  collectionName: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'create', payload: { name: string; description: string }): void
}>()

const formData = reactive({
  name: '',
  description: ''
})

function handleClose() {
  emit('close')
}

function handleCreate() {
  emit('create', { name: formData.name, description: formData.description })
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
    <button class="absolute inset-0 bg-black/40" type="button" aria-label="Close" @click="handleClose" />

    <div class="relative max-h-[calc(100vh-32px)] w-full max-w-[calc(100vw-32px)] overflow-hidden rounded-[16px] border border-black/10 bg-white shadow-[0px_25px_50px_-12px_rgba(0,0,0,0.25)] sm:h-[326px] sm:w-[448px] sm:max-h-[326px] sm:max-w-[448px]">
      <div class="flex h-[60.67px] items-center justify-between border-b border-black/10 px-[24px]">
        <div class="flex items-center gap-[10px]">
          <div class="flex h-[28px] w-[28px] items-center justify-center rounded-[10px] bg-[#FEF9C2]">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path
                d="M4.66667 5.83333L5.25 4.705C5.3134 4.57907 5.40989 4.47276 5.52908 4.39743C5.64827 4.32209 5.7857 4.28055 5.92667 4.27734H10.1117M10.1117 4.27734C10.2306 4.27714 10.3479 4.30414 10.4547 4.35631C10.5615 4.40848 10.6549 4.48443 10.7277 4.57833C10.8006 4.67222 10.8509 4.78148 10.875 4.89787C10.8991 5.01427 10.8961 5.13461 10.8664 5.24967L10.267 7.58333C10.2236 7.75112 10.1255 7.89964 9.98809 8.00533C9.8507 8.11103 9.682 8.16775 9.50867 8.16667H3.88833C3.68225 8.16667 3.484 8.08479 3.33824 7.93903C3.19248 7.79327 3.1106 7.59502 3.1106 7.38894V2.33333C3.1106 2.12725 3.19248 1.929 3.33824 1.78324C3.484 1.63748 3.68225 1.5556 3.88833 1.5556H5.40556C5.5357 1.55433 5.66396 1.5857 5.7788 1.64685C5.89364 1.708 5.99132 1.79697 6.06288 1.90567L6.37767 2.37233C6.44847 2.47983 6.54486 2.5681 6.6582 2.6292C6.77155 2.6903 6.89828 2.7223 7.027 2.72233H9.33333C9.53941 2.72233 9.73767 2.80421 9.88343 2.94997C10.0292 3.09573 10.111 3.29398 10.111 3.50006V4.27734Z"
                stroke="#D08700"
                stroke-width="1.16667"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </div>
          <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">
            新建文件夹· {{ collectionName }}
          </div>
        </div>

        <button type="button" class="flex h-[28px] w-[28px] items-center justify-center rounded-[10px]" aria-label="Close" @click="handleClose">
          <img :src="modalClose28" alt="" class="h-[28px] w-[28px]" />
        </button>
      </div>

      <div class="flex max-h-[calc(100vh-32px-60.67px)] flex-col gap-[16px] overflow-auto px-[24px] pt-[24px] sm:h-[calc(326px-60.67px)] sm:max-h-none">
        <div class="flex flex-col gap-[6px]">
          <div class="relative h-[16px]">
            <span class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">文件夹名称</span>
            <span class="ml-[4px] text-[12px] font-medium leading-[16px] text-[#FB2C36]">*</span>
          </div>
          <input
            v-model="formData.name"
            class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            placeholder="例：用户鉴权接口"
            type="text"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="flex items-center gap-[6px]">
            <img :src="modalDescIcon" alt="" class="h-[12px] w-[12px]" />
            <span class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">描述</span>
            <span class="text-[12px] leading-[16px] text-[#717182]">（可选）</span>
          </div>
          <textarea
            v-model="formData.description"
            class="h-[63.33px] w-full resize-none rounded-[10px] border border-black/10 bg-white px-[12px] py-[8px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            placeholder="描述该文件夹包含的接口类型..."
          />
        </div>

        <div class="flex items-center justify-end gap-[8px] border-t border-black/10 pt-[16px]">
          <button
            type="button"
            class="h-[32px] w-[61.33px] rounded-[10px] border border-black/10 bg-white text-[14px] font-medium leading-[20px] text-[#717182]"
            @click="handleClose"
          >
            取消
          </button>
          <button
            type="button"
            class="relative h-[32px] w-[129px] rounded-[10px] bg-[#F0B100] text-[14px] font-medium leading-[20px] text-white"
            @click="handleCreate"
          >
            <img :src="modalCreateIcon" alt="" class="absolute left-[20px] top-1/2 -translate-y-1/2 h-[13px] w-[13px]" />
            <span class="absolute left-[39px] top-[6.33px]">创建文件夹</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
