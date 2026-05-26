<script setup lang="ts">
import reportsSingleShare from '@/assets/figma/ai-testing-platform/reports-single-share.svg'
import ReportsSingleStatsRow from '@/components/figma/ai-testing-platform/ReportsSingleStatsRow.vue'
import ReportsSingleFailuresList from '@/components/figma/ai-testing-platform/ReportsSingleFailuresList.vue'

defineEmits<{
  share: []
  createDefect: [payload: { title: string; message: string; tag: string }]
}>()
</script>

<template>
  <section class="w-full rounded-[14px] border border-black/10 bg-white px-[20.67px] pt-[20.67px] pb-[0.67px]">
    <div class="flex flex-wrap items-start justify-between gap-[12px]">
      <div class="min-w-0">
        <div class="flex items-center gap-[8px]">
          <div class="text-[16px] font-semibold leading-[24px] text-[#0A0A0A]">R-002 测试报告</div>
          <div class="h-[20px] rounded-full bg-[#FFE2E2] px-[8px] text-[12px] leading-[20px] text-[#E7000B]">失败</div>
        </div>
        <div class="mt-[4px] truncate text-[12px] leading-[16px] text-[#717182]">
          订单全量回归 · development · 2024-03-14 12:00:00 · CI/CD 触发
        </div>
      </div>

      <button
        type="button"
        class="flex h-[24px] items-center gap-[4px] rounded-[4px] px-[4px] hover:bg-[#EFF6FF] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#155DFC]"
        @click="$emit('share')"
      >
        <img :src="reportsSingleShare" alt="" class="h-[12px] w-[12px]" />
        <span class="text-[12px] font-medium leading-[16px] text-[#155DFC]">分享链接</span>
      </button>
    </div>

    <div class="mt-[20px]">
      <ReportsSingleStatsRow />
    </div>

    <div class="mt-[20px]">
      <ReportsSingleFailuresList @create-defect="$emit('createDefect', $event)" />
    </div>
  </section>
</template>
