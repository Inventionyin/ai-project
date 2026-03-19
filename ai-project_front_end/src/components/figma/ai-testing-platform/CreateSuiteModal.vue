<script setup lang="ts">
import { reactive } from 'vue'

const { isOpen } = defineProps<{
  isOpen: boolean
  environments: {
    id: string
    name: string
  }[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'create', data: {
    name: string
    description: string
    defaultEnvironment: string
    timeoutSeconds: number
    concurrency: number
    retryCount: number
  }): void
}>()

const formData = reactive({
  name: '',
  description: '',
  defaultEnvironment: '',
  timeoutSeconds: 600,
  concurrency: 4,
  retryCount: 1
})

function handleClose() {
  emit('close')
}

function handleCreate() {
  emit('create', {
    name: formData.name,
    description: formData.description,
    defaultEnvironment: formData.defaultEnvironment,
    timeoutSeconds: Number(formData.timeoutSeconds),
    concurrency: Number(formData.concurrency),
    retryCount: Number(formData.retryCount)
  })
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
    <button class="absolute inset-0 bg-black/40" type="button" aria-label="Close" @click="handleClose" />

    <form
      class="relative max-h-[calc(100vh-32px)] w-full max-w-[calc(100vw-32px)] overflow-auto rounded-[16px] bg-white shadow-[0px_25px_50px_-12px_rgba(0,0,0,0.25)] sm:h-[457.33px] sm:w-[448px] sm:max-w-[448px]"
      @submit.prevent="handleCreate"
    >
      <div class="px-[24px] pt-[24px]">
        <div class="text-[16px] font-semibold leading-[24px] text-[#0A0A0A]">新建测试套件</div>
      </div>

      <div class="mt-[16px] flex flex-col gap-[16px] px-[24px]">
        <div class="flex flex-col gap-[6px]">
          <div class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">
            套件名称 <span class="text-[#FB2C36]">*</span>
          </div>
          <input
            v-model="formData.name"
            class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            placeholder="如：支付冒烟套件"
            type="text"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">描述</div>
          <textarea
            v-model="formData.description"
            class="h-[57.33px] w-full resize-none rounded-[10px] border border-black/10 bg-white px-[12px] py-[8px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">默认环境</div>
          <select
            v-model="formData.defaultEnvironment"
            class="h-[36px] w-full appearance-none rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
          >
            <option value="">请选择环境</option>
            <option v-for="environment in environments" :key="environment.id" :value="environment.id">
              {{ environment.name }}
            </option>
          </select>
        </div>

        <div class="grid grid-cols-1 gap-x-[12px] gap-y-[12px] sm:grid-cols-3">
          <div class="flex flex-col gap-[4px]">
            <div class="text-[12px] font-medium leading-[16px] text-[#717182]">超时(s)</div>
            <input
              v-model.number="formData.timeoutSeconds"
              class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[8px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              type="number"
              inputmode="numeric"
            />
          </div>

          <div class="flex flex-col gap-[4px]">
            <div class="text-[12px] font-medium leading-[16px] text-[#717182]">并发数</div>
            <input
              v-model.number="formData.concurrency"
              class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[8px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              type="number"
              inputmode="numeric"
            />
          </div>

          <div class="flex flex-col gap-[4px]">
            <div class="text-[12px] font-medium leading-[16px] text-[#717182]">重试次数</div>
            <input
              v-model.number="formData.retryCount"
              class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[8px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              type="number"
              inputmode="numeric"
            />
          </div>
        </div>
      </div>

      <div class="mt-[20px] flex gap-[8px] px-[24px] pb-[24px]">
        <button
          type="button"
          class="h-[36px] flex-1 rounded-[10px] border border-black/10 bg-white text-[14px] font-medium leading-[20px] text-[#0A0A0A]"
          @click="handleClose"
        >
          取消
        </button>
        <button
          type="submit"
          class="h-[36px] flex-1 rounded-[10px] bg-[#155DFC] text-[14px] font-medium leading-[20px] text-white"
        >
          创建
        </button>
      </div>
    </form>
  </div>
</template>
