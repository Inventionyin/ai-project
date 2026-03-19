<script setup lang="ts">
import { inject, ref } from 'vue'
import filterSearch from '@/assets/figma/ai-testing-platform/filter-search.svg'
import headerPlus from '@/assets/figma/ai-testing-platform/header-plus.svg'
import runsFilter from '@/assets/figma/ai-testing-platform/runs-filter.svg'
import runsRefresh from '@/assets/figma/ai-testing-platform/runs-refresh.svg'
import RunsTable, { type RunRow } from '@/components/figma/ai-testing-platform/RunsTable.vue'

const openCreateRun = inject<() => void>('aiTestingPlatformOpenCreateRun', () => {})

const rows = ref<RunRow[]>([
  {
    runId: 'R-001',
    trigger: '手动',
    suiteName: '支付冒烟套件',
    suiteSummary: '12/12 通过',
    environment: 'staging',
    status: '通过',
    passRate: '100%',
    passRateColor: '#00A63E',
    startedAt: '2024-03-14 14:30:00',
    duration: '2m 15s',
    createdBy: '张三'
  },
  {
    runId: 'R-002',
    trigger: 'CI/CD',
    suiteName: '订单全量回归',
    suiteSummary: '75/86 通过',
    environment: 'development',
    status: '失败',
    passRate: '87.2%',
    passRateColor: '#D08700',
    startedAt: '2024-03-14 12:00:00',
    duration: '18m 45s',
    createdBy: 'CI/CD Bot'
  },
  {
    runId: 'R-003',
    trigger: '定时',
    suiteName: '用户核心路径',
    suiteSummary: '18/24 通过',
    environment: 'staging',
    status: '执行中',
    passRate: '75%',
    passRateColor: '#FB2C36',
    startedAt: '2024-03-14 15:00:00',
    duration: '3m 21s',
    createdBy: '定时任务'
  },
  {
    runId: 'R-004',
    trigger: '手动',
    suiteName: '支付冒烟套件',
    suiteSummary: '0/12 通过',
    environment: 'production',
    status: '已取消',
    passRate: '-',
    passRateColor: '#717182',
    startedAt: '2024-03-13 18:00:00',
    duration: '1m 0s',
    createdBy: '王五'
  },
  {
    runId: 'R-005',
    trigger: 'CI/CD',
    suiteName: '订单全量回归',
    suiteSummary: '83/86 通过',
    environment: 'development',
    status: '通过',
    passRate: '96.5%',
    passRateColor: '#00A63E',
    startedAt: '2024-03-13 10:00:00',
    duration: '22m 0s',
    createdBy: 'CI/CD Bot'
  }
])
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)] md:pr-[16.67px]">
    <div class="flex flex-col gap-[16px] px-[16px] pt-[16px] md:px-[24px] md:pt-[24px]">
      <div class="flex items-center justify-between gap-[16px]">
        <div class="flex flex-col gap-[2px]">
          <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">运行记录</div>
          <div class="text-[14px] leading-[20px] text-[#717182]">共 5 次运行</div>
        </div>

        <div class="flex items-center gap-[8px]">
          <button
            type="button"
            class="flex h-[32px] items-center gap-[6px] rounded-[10px] border border-black/10 bg-transparent px-[12px]"
          >
            <img :src="runsRefresh" alt="" class="h-[13px] w-[13px]" />
            <span class="text-[14px] leading-[20px] text-[#717182]"> 刷新</span>
          </button>

          <button type="button" class="relative h-[32px] w-[100px] rounded-[10px] bg-[#155DFC]" @click="openCreateRun">
            <img :src="headerPlus" alt="" class="absolute left-[12px] top-[9px] h-[14px] w-[14px]" />
            <span class="absolute left-[32px] top-[6.33px] text-[14px] font-medium leading-[20px] text-white">
              新建执行
            </span>
          </button>
        </div>
      </div>

      <div class="flex flex-col gap-[12px] md:flex-row md:items-center md:justify-between">
        <div class="flex flex-wrap items-center gap-[8px]">
          <img :src="runsFilter" alt="" class="h-[13px] w-[13px]" />

          <button type="button" class="h-[28px] rounded-full border border-black/10 px-[12px] text-[12px] font-medium leading-[16px] text-[#717182]">
            通过
          </button>
          <button type="button" class="h-[28px] rounded-full border border-black/10 px-[12px] text-[12px] font-medium leading-[16px] text-[#717182]">
            失败
          </button>
          <button type="button" class="h-[28px] rounded-full border border-black/10 px-[12px] text-[12px] font-medium leading-[16px] text-[#717182]">
            执行中
          </button>
          <button type="button" class="h-[28px] rounded-full border border-black/10 px-[12px] text-[12px] font-medium leading-[16px] text-[#717182]">
            排队中
          </button>
          <button type="button" class="h-[28px] rounded-full border border-black/10 px-[12px] text-[12px] font-medium leading-[16px] text-[#717182]">
            已取消
          </button>
        </div>

        <div class="relative h-[32px] w-full max-w-[224px] rounded-[10px] border border-black/10 bg-white">
          <img :src="filterSearch" alt="" class="absolute left-[10px] top-[8.5px] h-[15px] w-[15px]" />
          <input
            class="h-full w-full rounded-[10px] bg-transparent pl-[32px] pr-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none placeholder:text-[#0A0A0A]"
            placeholder="搜索套件名..."
          />
        </div>
      </div>

      <section class="w-full overflow-hidden rounded-[14px] border border-black/10 bg-white">
        <RunsTable :rows="rows" />
      </section>
    </div>
  </div>
</template>
