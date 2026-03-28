<script setup lang="ts">
import { ref } from 'vue'
import lineChartPlot from '@/assets/figma/ai-testing-platform/reports-linechart-plot.svg'
import lineChartOverlay from '@/assets/figma/ai-testing-platform/reports-linechart-overlay.svg'

type MetricKey = 'passRate' | 'failCount' | 'flakyRate' | 'avgDuration'
type RangeKey = '7d' | '14d' | '30d'

const activeMetric = ref<MetricKey>('passRate')
const activeRange = ref<RangeKey>('7d')

const metricButtons = [
  { key: 'passRate', label: '通过率', width: 'w-[60px]' },
  { key: 'failCount', label: '失败数', width: 'w-[60px]' },
  { key: 'flakyRate', label: '不稳定率', width: 'w-[72px]' },
  { key: 'avgDuration', label: '平均耗时', width: 'flex-1' }
] as const

const rangeButtons = [
  { key: '7d', label: '7天', width: 'w-[39.04px]' },
  { key: '14d', label: '14天', width: 'w-[46.08px]' },
  { key: '30d', label: '30天', width: 'w-[46.08px]' }
] as const

const xAxis = [
  { label: '03-03', left: 'left-[0px]', width: 'w-[33px]', tickLeft: 'left-[16.5px]' },
  { label: '03-05', left: 'left-[146.67px]', width: 'w-[33px]', tickLeft: 'left-[16.5px]' },
  { label: '03-07', left: 'left-[293.83px]', width: 'w-[32px]', tickLeft: 'left-[16px]' },
  { label: '03-09', left: 'left-[440px]', width: 'w-[33px]', tickLeft: 'left-[16.5px]' },
  { label: '03-11', left: 'left-[588.17px]', width: 'w-[30px]', tickLeft: 'left-[15px]' },
  { label: '03-13', left: 'left-[733.83px]', width: 'w-[32px]', tickLeft: 'left-[16px]' },
  { label: '03-14', left: 'left-[870.22px]', width: 'w-[32px]', tickLeft: 'left-[26.28px]' }
] as const

const yAxis = [
  { label: '100%', top: 'top-[0px]', width: 'w-[28px]' },
  { label: '75%', top: 'top-[41.75px]', width: 'w-[22px]' },
  { label: '50%', top: 'top-[86.75px]', width: 'w-[23px]' },
  { label: '25%', top: 'top-[131.75px]', width: 'w-[23px]' },
  { label: '0%', top: 'top-[176.75px]', width: 'w-[16px]' }
] as const
</script>

<template>
  <section
    class="w-full rounded-[14px] border border-black/10 bg-white px-[20.67px] pt-[20.67px] pb-[0.67px]"
  >
    <div class="flex items-center justify-between">
      <div class="flex h-[28px] w-[288px] items-center gap-[8px]">
        <button
          v-for="item in metricButtons"
          :key="item.key"
          type="button"
          class="h-[28px] rounded-[10px] px-[12px] text-[12px] font-medium leading-[16px]"
          :class="[
            item.width,
            activeMetric === item.key
              ? 'bg-[#3B82F6] text-white'
              : 'bg-transparent text-[#717182]'
          ]"
          @click="activeMetric = item.key"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="flex h-[24px] w-[139.21px] items-center gap-[4px]">
        <button
          v-for="item in rangeButtons"
          :key="item.key"
          type="button"
          class="h-[24px] rounded-[4px] px-[10px] text-[12px] font-medium leading-[16px]"
          :class="[item.width, activeRange === item.key ? 'bg-[#155DFC] text-white' : 'bg-transparent text-[#717182]']"
          @click="activeRange = item.key"
        >
          {{ item.label }}
        </button>
      </div>
    </div>

    <div class="mt-[16px] w-full overflow-x-auto">
      <div class="relative h-[220px] w-[950px]">
        <img :src="lineChartPlot" alt="" class="absolute left-[65px] top-[5px] h-[180px] w-[880px]" />
        <img
          :src="lineChartOverlay"
          alt=""
          class="absolute left-[61px] top-[11.62px] h-[20.6px] w-[888px]"
        />

        <div class="absolute left-[48.5px] top-[185px] h-[17.81px] w-[902.22px]">
          <div
            v-for="item in xAxis"
            :key="item.label"
            class="absolute top-0 h-[17.81px]"
            :class="[item.left, item.width]"
          >
            <div class="absolute top-0 h-[6px] w-[1px] bg-[#666666]" :class="item.tickLeft" />
            <div class="absolute left-0 top-[4.81px] w-full text-center text-[11px] leading-[13px] text-[#666666]">
              {{ item.label }}
            </div>
          </div>
        </div>

        <div class="absolute left-[29px] top-[1.15px] h-[189.75px] w-[36px]">
          <div class="absolute right-0 top-[3.85px] h-[180px] w-[1px] bg-[#666666]" />
          <div
            v-for="item in yAxis"
            :key="item.label"
            class="absolute right-0 h-[13px]"
            :class="[item.top, item.width]"
          >
            <div class="absolute right-0 top-[7px] h-[1px] w-[6px] bg-[#666666]" />
            <div class="absolute right-[6px] top-0 text-right text-[11px] leading-[13px] text-[#666666]">
              {{ item.label }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
