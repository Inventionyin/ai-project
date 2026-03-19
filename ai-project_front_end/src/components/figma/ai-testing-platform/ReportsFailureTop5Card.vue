<script setup lang="ts">
import barChartGrid from '@/assets/figma/ai-testing-platform/reports-barchart-grid.svg'
import barChartBars from '@/assets/figma/ai-testing-platform/reports-barchart-bars.svg'

const labels = [
  { text: '支付-微信支付回调验签', top: 'top-[0px]' },
  { text: '商品库存扣减-并发场景', top: 'top-[24px]' },
  { text: '取消订单-超时自动取消', top: 'top-[48px]' },
  { text: '用户登录-异常手机号', top: 'top-[72px]' },
  { text: '退款-部分退款计算错误', top: 'top-[96px]' }
] as const

const xAxis = [
  { label: '0', left: 'left-[0px]' },
  { label: '2', left: 'left-[76.5px]' },
  { label: '4', left: 'left-[153px]' },
  { label: '6', left: 'left-[229.5px]' },
  { label: '8', left: 'left-[306px]' }
] as const
</script>

<template>
  <section
    class="w-full rounded-[14px] border border-black/10 bg-white px-[20.67px] pt-[20.67px] pb-[0.67px] md:h-[237.33px]"
  >
    <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">失败 Top 5</div>

    <div class="mt-[16px] w-full overflow-x-auto">
      <div class="relative h-[160px] w-[446px]">
        <div class="absolute left-[22px] top-[5px] h-[120px] w-[113px]">
          <div class="absolute right-0 top-0 h-full w-[1px] bg-[#666666]" />
          <div
            v-for="item in labels"
            :key="item.text"
            class="absolute right-[8px] h-[12px] w-[105px] text-right text-[10px] leading-[12px] text-[#666666]"
            :class="item.top"
          >
            {{ item.text }}
          </div>
        </div>

        <img :src="barChartGrid" alt="" class="absolute left-[135px] top-[5px] h-[120px] w-[306px]" />
        <img :src="barChartBars" alt="" class="absolute left-[135px] top-[9px] h-[112px] w-[306px]" />

        <div class="absolute left-[131.5px] top-[125px] h-[17.1px] w-[313px]">
          <div
            v-for="item in xAxis"
            :key="item.label"
            class="absolute top-0 h-[12px] w-[7px] text-center text-[10px] leading-[12px] text-[#666666]"
            :class="item.left"
          >
            {{ item.label }}
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
