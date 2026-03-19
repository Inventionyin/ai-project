<script setup lang="ts">
import failuresIcon from '@/assets/figma/ai-testing-platform/reports-single-failures.svg'
import ReportsSingleFailureRow from '@/components/figma/ai-testing-platform/ReportsSingleFailureRow.vue'

const rows = [
  {
    title: '支付-微信支付回调验签',
    message: 'statusCode expected 200 but got 500',
    tag: 'ASSERT'
  },
  {
    title: '取消订单-超时自动取消',
    message: 'Request timeout after 10000ms',
    tag: 'TIMEOUT'
  },
  {
    title: '商品库存扣减-并发场景',
    message: 'inventory count expected 98 but got 102',
    tag: 'ASSERT'
  }
] as const
</script>

<template>
  <section class="w-full">
    <div class="flex items-center gap-[8px]">
      <img :src="failuresIcon" alt="" class="h-[14px] w-[14px]" />
      <div class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">失败用例（11）</div>
    </div>

    <div class="mt-[12px] flex flex-col gap-[8px]">
      <ReportsSingleFailureRow v-for="item in rows" :key="item.title" v-bind="item" />
    </div>

    <button type="button" class="mt-[16px] w-full text-center text-[16px] font-medium leading-[24px] text-[#155DFC]">
      查看全部 11 条失败
    </button>
  </section>
</template>
