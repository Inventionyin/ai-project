<script setup lang="ts">
import { ref } from 'vue'
import chevronDownSmall from '@/assets/figma/ai-testing-platform/chevron-down-small.svg'
import reportsSingleDetail from '@/assets/figma/ai-testing-platform/reports-single-detail.svg'

const selectedReport = ref('R-002')

const options = [
  { label: 'R-001 测试报告', value: 'R-001' },
  { label: 'R-002 测试报告', value: 'R-002' },
  { label: 'R-003 测试报告', value: 'R-003' }
] as const
</script>

<template>
  <div class="flex flex-wrap items-center gap-[12px]">
    <div class="relative h-[32px] w-full max-w-[280px]">
      <select
        v-model="selectedReport"
        class="h-full w-full appearance-none rounded-[10px] border border-black/10 bg-white px-[12px] pr-[36px] text-[14px] leading-[20px] text-[#717182] outline-none"
      >
        <option v-for="item in options" :key="item.value" :value="item.value">
          {{ item.label }}
        </option>
      </select>
      <img :src="chevronDownSmall" alt="" class="pointer-events-none absolute right-[12px] top-1/2 h-[13px] w-[13px] -translate-y-1/2" />
    </div>

    <button type="button" class="flex h-[32px] items-center gap-[6px] rounded-[10px] border border-black/10 bg-white px-[12px]">
      <img :src="reportsSingleDetail" alt="" class="h-[13px] w-[13px]" />
      <span class="text-[14px] font-medium leading-[20px] text-[#717182]">查看详情</span>
    </button>
  </div>
</template>
