<script setup lang="ts">
import reportsExport from '@/assets/figma/ai-testing-platform/reports-export.svg'

defineEmits<{
  export: []
}>()
</script>

<template>
  <div class="flex items-center justify-between">
    <div class="flex flex-col gap-[2px]">
      <div class="text-[18px] font-semibold leading-[28px] text-[#0A0A0A]">报告中心</div>
      <div class="text-[14px] leading-[20px] text-[#717182]">质量趋势与单次报告</div>
    </div>

    <button
      type="button"
      class="relative h-[32px] w-[100.33px] rounded-[10px] border border-black/10 bg-transparent hover:bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#155DFC]"
      @click="$emit('export')"
    >
      <img :src="reportsExport" alt="" class="absolute left-[12.67px] top-[9.5px] h-[13px] w-[13px]" />
      <span class="absolute left-[29.67px] top-[6.33px] text-[14px] font-medium leading-[20px] text-[#717182]">
        导出报告
      </span>
    </button>
  </div>
</template>
