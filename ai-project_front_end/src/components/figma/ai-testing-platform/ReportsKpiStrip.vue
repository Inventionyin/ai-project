<script setup lang="ts">
import ReportsKpiCard from '@/components/figma/ai-testing-platform/ReportsKpiCard.vue'
import kpiPassrate from '@/assets/figma/ai-testing-platform/reports-kpi-passrate.svg'
import kpiFailcount from '@/assets/figma/ai-testing-platform/reports-kpi-failcount.svg'
import kpiFlaky from '@/assets/figma/ai-testing-platform/reports-kpi-flaky.svg'
import kpiDuration from '@/assets/figma/ai-testing-platform/reports-kpi-duration.svg'

const cards = [
  {
    label: '平均通过率',
    value: '91.4%',
    delta: '+2.1% vs 上期',
    deltaColor: '#00A63E',
    iconBgColor: '#F0FDF4',
    iconSrc: kpiPassrate
  },
  {
    label: '平均失败数',
    value: '11次',
    delta: '-3次 vs 上期',
    deltaColor: '#00A63E',
    iconBgColor: '#FEF2F2',
    iconSrc: kpiFailcount
  },
  {
    label: '不稳定率',
    value: '2.0%',
    delta: '-0.8% vs 上期',
    deltaColor: '#00A63E',
    iconBgColor: '#FEFCE8',
    iconSrc: kpiFlaky
  },
  {
    label: '平均耗时',
    value: '11.5min',
    delta: '-0.9min vs 上期',
    deltaColor: '#00A63E',
    iconBgColor: '#FAF5FF',
    iconSrc: kpiDuration
  }
] as const
</script>

<template>
  <div class="flex flex-wrap gap-[16px]">
    <ReportsKpiCard v-for="card in cards" :key="card.label" v-bind="card" />
  </div>
</template>
