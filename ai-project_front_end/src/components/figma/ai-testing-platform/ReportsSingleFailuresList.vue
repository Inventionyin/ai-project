<script setup lang="ts">
import { computed, ref } from 'vue'
import failuresIcon from '@/assets/figma/ai-testing-platform/reports-single-failures.svg'
import ReportsSingleFailureRow from '@/components/figma/ai-testing-platform/ReportsSingleFailureRow.vue'

defineEmits<{
  createDefect: [payload: { title: string; message: string; tag: string }]
}>()

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
  },
  {
    title: '优惠券叠加-互斥规则',
    message: 'coupon conflict expected true but got false',
    tag: 'ASSERT'
  },
  {
    title: '订单退款-原路退回',
    message: 'refund status expected SUCCESS but got PENDING',
    tag: 'ASSERT'
  },
  {
    title: '会员积分-支付后入账',
    message: 'points expected 120 but got 0',
    tag: 'ASSERT'
  },
  {
    title: '发票申请-企业抬头校验',
    message: 'taxNo validation failed',
    tag: 'VALIDATE'
  },
  {
    title: '购物车合并-跨端登录',
    message: 'cart items expected 6 but got 4',
    tag: 'ASSERT'
  },
  {
    title: '物流轨迹-签收状态同步',
    message: 'tracking status expected SIGNED but got SHIPPING',
    tag: 'SYNC'
  },
  {
    title: '风控拦截-高频下单',
    message: 'risk decision expected BLOCK but got PASS',
    tag: 'ASSERT'
  },
  {
    title: '消息通知-支付成功短信',
    message: 'sms send timeout after 5000ms',
    tag: 'TIMEOUT'
  }
] as const

const isExpanded = ref(false)
const visibleRows = computed(() => (isExpanded.value ? rows : rows.slice(0, 3)))
</script>

<template>
  <section class="w-full">
    <div class="flex items-center gap-[8px]">
      <img :src="failuresIcon" alt="" class="h-[14px] w-[14px]" />
      <div class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">失败用例（11）</div>
    </div>

    <div class="mt-[12px] flex flex-col gap-[8px]">
      <ReportsSingleFailureRow v-for="item in visibleRows" :key="item.title" v-bind="item" @create-defect="$emit('createDefect', $event)" />
    </div>

    <button
      type="button"
      class="mt-[16px] w-full rounded-[8px] py-[4px] text-center text-[16px] font-medium leading-[24px] text-[#155DFC] hover:bg-[#EFF6FF] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#155DFC]"
      @click="isExpanded = !isExpanded"
    >
      {{ isExpanded ? '收起失败用例' : '查看全部 11 条失败' }}
    </button>
  </section>
</template>
