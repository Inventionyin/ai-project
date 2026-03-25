<script setup lang="ts">
import reportsTabTrend from '@/assets/figma/ai-testing-platform/reports-tab-trend.svg'
import reportsTabSingle from '@/assets/figma/ai-testing-platform/reports-tab-single.svg'

export type ReportsViewTab = 'trend' | 'single' | 'performance'

const modelValue = defineModel<ReportsViewTab>({ required: true })
</script>

<template>
  <div class="flex w-full items-center gap-[4px] border-b border-black/10">
    <button
      type="button"
      class="relative h-[46px] w-[111px]"
      :class="modelValue === 'trend' ? 'border-b-[2px] border-[#155DFC]' : 'border-b-[2px] border-transparent'"
      @click="modelValue = 'trend'"
    >
      <img :src="reportsTabTrend" alt="" class="absolute left-[16px] top-[14.5px] h-[15px] w-[15px]" />
      <span
        class="absolute left-[39px] top-[12.33px] text-[14px] font-medium leading-[20px]"
        :class="modelValue === 'trend' ? 'text-[#155DFC]' : 'text-[#717182]'"
      >
        趋势看板
      </span>
    </button>

    <button
      type="button"
      class="relative h-[46px] w-[111px]"
      :class="modelValue === 'single' ? 'border-b-[2px] border-[#155DFC]' : 'border-b-[2px] border-transparent'"
      @click="modelValue = 'single'"
    >
      <img :src="reportsTabSingle" alt="" class="absolute left-[16px] top-[14.5px] h-[15px] w-[15px]" />
      <span
        class="absolute left-[39px] top-[12.33px] text-[14px] font-medium leading-[20px]"
        :class="modelValue === 'single' ? 'text-[#155DFC]' : 'text-[#717182]'"
      >
        单次报告
      </span>
    </button>

    <button
      type="button"
      class="relative h-[46px] w-[136px]"
      :class="modelValue === 'performance' ? 'border-b-[2px] border-[#155DFC]' : 'border-b-[2px] border-transparent'"
      @click="modelValue = 'performance'"
    >
      <img :src="reportsTabSingle" alt="" class="absolute left-[16px] top-[14.5px] h-[15px] w-[15px]" />
      <span
        class="absolute left-[39px] top-[12.33px] text-[14px] font-medium leading-[20px]"
        :class="modelValue === 'performance' ? 'text-[#155DFC]' : 'text-[#717182]'"
      >
        性能报告
      </span>
    </button>
  </div>
</template>
