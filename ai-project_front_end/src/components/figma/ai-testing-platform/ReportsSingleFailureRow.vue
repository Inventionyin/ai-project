<script setup lang="ts">
import failureRowIcon from '@/assets/figma/ai-testing-platform/reports-single-failure-row.svg'

defineProps<{
  title: string
  message: string
  tag: string
}>()

defineEmits<{
  createDefect: [payload: { title: string; message: string; tag: string }]
}>()
</script>

<template>
  <div
    class="flex flex-wrap items-start gap-x-[12px] gap-y-[10px] rounded-[10px] border border-[#FFC9C9] bg-[rgba(254,242,242,0.4)] px-[12.67px] py-[12.67px]"
  >
    <img :src="failureRowIcon" alt="" class="mt-[2px] h-[13px] w-[13px] shrink-0" />

    <div class="min-w-0 flex-1">
      <div class="truncate text-[12px] font-medium leading-[16px] text-[#0A0A0A]">{{ title }}</div>
      <div class="mt-[2px] truncate text-[12px] leading-[16px] text-[#E7000B] font-mono">{{ message }}</div>
    </div>

    <div class="flex items-center gap-[8px]">
      <div class="h-[20px] rounded-[4px] bg-[#FFE2E2] px-[8px] text-[12px] leading-[16px] text-[#E7000B]">
        {{ tag }}
      </div>
      <button
        type="button"
        class="h-[24px] rounded-[4px] border border-[#FFA2A2] px-[8px] text-[12px] font-medium leading-[24px] text-[#E7000B] hover:bg-[#FEE2E2] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#E7000B]"
        @click="$emit('createDefect', { title, message, tag })"
      >
        创建缺陷
      </button>
    </div>
  </div>
</template>
