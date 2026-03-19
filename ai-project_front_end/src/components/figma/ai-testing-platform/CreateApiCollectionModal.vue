<script setup lang="ts">
import { reactive } from 'vue'
import modalCollectionIcon from '@/assets/figma/ai-testing-platform/modal-collection-icon.svg'
import modalClose28 from '@/assets/figma/ai-testing-platform/modal-close-28.svg'
import modalDescIcon from '@/assets/figma/ai-testing-platform/modal-desc-icon.svg'
import modalBaseUrlIcon from '@/assets/figma/ai-testing-platform/modal-baseurl-icon.svg'
import modalAuthIcon from '@/assets/figma/ai-testing-platform/modal-auth-icon.svg'
import modalCreateIcon from '@/assets/figma/ai-testing-platform/modal-create-icon.svg'

type AuthType = 'Bearer' | 'Basic' | 'API Key' | '无'

defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'create', payload: { name: string; description: string; baseUrl: string; defaultAuthType: AuthType }): void
}>()

const formData = reactive({
  name: '',
  description: '',
  baseUrl: '',
  defaultAuthType: 'Bearer' as AuthType
})

function handleClose() {
  emit('close')
}

function handleCreate() {
  emit('create', {
    name: formData.name,
    description: formData.description,
    baseUrl: formData.baseUrl,
    defaultAuthType: formData.defaultAuthType
  })
}

function authButtonClass(value: AuthType) {
  if (formData.defaultAuthType === value) {
    return 'bg-[#155DFC] border-[#155DFC] shadow-[0px_1px_2px_-1px_rgba(0,0,0,0.1),0px_1px_3px_0px_rgba(0,0,0,0.1)] text-white'
  }
  return 'bg-white border-black/10 text-[#717182]'
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
    <button class="absolute inset-0 bg-black/40" type="button" aria-label="Close" @click="handleClose" />

    <div class="relative max-h-[calc(100vh-32px)] w-full max-w-[calc(100vw-32px)] overflow-hidden rounded-[16px] border border-black/10 bg-white shadow-[0px_25px_50px_-12px_rgba(0,0,0,0.25)] sm:h-[486px] sm:w-[512px] sm:max-h-[486px] sm:max-w-[512px]">
      <div class="flex h-[60.67px] items-center justify-between border-b border-black/10 px-[24px]">
        <div class="flex items-center gap-[10px]">
          <img :src="modalCollectionIcon" alt="" class="h-[28px] w-[28px]" />
          <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">新建接口集合</div>
        </div>
        <button type="button" class="flex h-[28px] w-[28px] items-center justify-center rounded-[10px]" aria-label="Close" @click="handleClose">
          <img :src="modalClose28" alt="" class="h-[28px] w-[28px]" />
        </button>
      </div>

      <div class="flex max-h-[calc(100vh-32px-60.67px)] flex-col gap-[20px] overflow-auto px-[24px] pt-[24px] sm:h-[calc(486px-60.67px)] sm:max-h-none">
        <div class="flex flex-col gap-[6px]">
          <div class="relative h-[16px]">
            <span class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">集合名称</span>
            <span class="ml-[4px] text-[12px] font-medium leading-[16px] text-[#FB2C36]">*</span>
          </div>
          <input
            v-model="formData.name"
            class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            placeholder="例：支付服务 API v3"
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
            placeholder="简要描述该集合的用途..."
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="flex items-center gap-[6px]">
            <img :src="modalBaseUrlIcon" alt="" class="h-[12px] w-[12px]" />
            <span class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">Base URL</span>
            <span class="text-[12px] leading-[16px] text-[#717182]">（可选）</span>
          </div>
          <input
            v-model="formData.baseUrl"
            class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            placeholder="https://api.example.com 或 {{baseUrl}}"
            type="text"
            style="font-family: Consolas"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="flex items-center gap-[6px]">
            <img :src="modalAuthIcon" alt="" class="h-[12px] w-[12px]" />
            <span class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">默认鉴权类型</span>
          </div>
          <div class="flex h-[32px] w-full gap-[8px]">
            <button
              type="button"
              class="h-[32px] w-[109.67px] rounded-[10px] border text-[12px] font-medium leading-[16px]"
              :class="authButtonClass('Bearer')"
              @click="formData.defaultAuthType = 'Bearer'"
            >
              Bearer
            </button>
            <button
              type="button"
              class="h-[32px] w-[109.67px] rounded-[10px] border text-[12px] font-medium leading-[16px]"
              :class="authButtonClass('Basic')"
              @click="formData.defaultAuthType = 'Basic'"
            >
              Basic
            </button>
            <button
              type="button"
              class="h-[32px] w-[109.67px] rounded-[10px] border text-[12px] font-medium leading-[16px]"
              :class="authButtonClass('API Key')"
              @click="formData.defaultAuthType = 'API Key'"
            >
              API Key
            </button>
            <button
              type="button"
              class="h-[32px] w-[109.67px] rounded-[10px] border text-[12px] font-medium leading-[16px]"
              :class="authButtonClass('无')"
              @click="formData.defaultAuthType = '无'"
            >
              无
            </button>
          </div>
        </div>

        <div class="flex items-center justify-end gap-[8px] border-t border-black/10 pt-[20px]">
          <button
            type="button"
            class="h-[32px] w-[61.33px] rounded-[10px] border border-black/10 bg-white text-[14px] font-medium leading-[20px] text-[#717182]"
            @click="handleClose"
          >
            取消
          </button>
          <button
            type="button"
            class="relative h-[32px] w-[115px] rounded-[10px] bg-[#155DFC] text-[14px] font-medium leading-[20px] text-white"
            @click="handleCreate"
          >
            <img :src="modalCreateIcon" alt="" class="absolute left-[20px] top-1/2 -translate-y-1/2 h-[13px] w-[13px]" />
            <span class="absolute left-[39px] top-[6.33px]">创建集合</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
