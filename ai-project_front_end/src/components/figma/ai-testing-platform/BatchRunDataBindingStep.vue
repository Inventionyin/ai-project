<script setup lang="ts">
import BatchRunStepIndicator from '@/components/figma/ai-testing-platform/BatchRunStepIndicator.vue'
import BatchRunDataBindingTable, { type BatchRunDataBindingRow } from '@/components/figma/ai-testing-platform/BatchRunDataBindingTable.vue'
import infoIcon from '@/assets/figma/ai-testing-platform/batch-run-info-icon.svg'

defineProps<{
  rows: BatchRunDataBindingRow[]
  errorsById?: Record<string, string>
}>()

const emit = defineEmits<{
  (e: 'update-row-override', payload: { id: string; overrideParamsText: string }): void
}>()
</script>

<template>
  <div class="flex w-full flex-col gap-[20px]">
    <BatchRunStepIndicator :active-step="2" />

    <div class="flex w-full flex-col gap-[12px]">
      <BatchRunDataBindingTable :rows="rows" :errors-by-id="errorsById" @update-row-override="emit('update-row-override', $event)" />

      <div class="relative h-[33.33px] w-full max-w-[615.33px] rounded-[10px] border border-black/10 bg-[rgba(236,236,240,0.3)]">
        <img :src="infoIcon" alt="" class="absolute left-[12.67px] top-[10.67px] h-[12px] w-[12px]" />
        <div class="absolute left-[32.67px] top-[8.67px] h-[16px] w-[300px] text-[12px] leading-[16px] text-[#717182]">
          参数覆盖为可选项，未填写时将使用绑定配置的默认参数执行
        </div>
      </div>
    </div>
  </div>
</template>
