<script setup lang="ts">
import workersRefresh from '@/assets/figma/ai-testing-platform-workers/workers-refresh.svg'
import workersRegister from '@/assets/figma/ai-testing-platform-workers/workers-register.svg'
import WorkerCard from '@/components/figma/ai-testing-platform/WorkerCard.vue'

const stats = [
  { value: '2', label: '在线 Workers', valueColor: '#00A63E', bg: '#F0FDF4' },
  { value: '16', label: '总并发槽位', valueColor: '#155DFC', bg: '#EFF6FF' },
  { value: '6', label: '空闲槽位', valueColor: '#9810FA', bg: '#FAF5FF' }
]

const workers = [
  {
    name: 'worker-01',
    status: '在线',
    version: 'v1.2.0',
    capabilities: ['API'],
    slotsText: '2/4',
    slotsStateText: '空闲',
    cpuPercent: 65,
    cpuBarColor: '#FDC700',
    memPercent: 48,
    memBarColor: '#51A2FF',
    heartbeatText: '最近心跳：5s前'
  },
  {
    name: 'worker-02',
    status: '在线',
    version: 'v1.2.0',
    capabilities: ['API'],
    slotsText: '4/4',
    slotsStateText: '空闲',
    cpuPercent: 12,
    cpuBarColor: '#05DF72',
    memPercent: 23,
    memBarColor: '#51A2FF',
    heartbeatText: '最近心跳：3s前'
  },
  {
    name: 'worker-03',
    status: '离线',
    version: 'v1.1.0',
    capabilities: ['API', 'PERF'],
    slotsText: '0/8',
    slotsStateText: '空闲',
    heartbeatText: '最近心跳：5分钟前',
    isFaded: true,
    borderColor: '#FFC9C9'
  }
] as const
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)]">
    <div class="flex flex-col gap-[16px] px-[16px] pt-[16px] md:px-[24px] md:pt-[24px]">
      <div class="flex flex-col gap-[12px] md:flex-row md:items-center md:justify-between md:gap-0">
        <div class="flex flex-col gap-[2px]">
          <div class="text-[18px] font-semibold leading-[28px] text-[#0A0A0A]">Worker 管理</div>
          <div class="text-[14px] leading-[20px] text-[#717182]">执行节点状态与资源监控</div>
        </div>

        <div class="flex items-center gap-[8px]">
          <button
            type="button"
            class="relative h-[32px] w-[72.33px] rounded-[10px] border border-black/10 bg-transparent"
          >
            <img :src="workersRefresh" alt="" class="absolute left-[12.67px] top-[9.5px] h-[13px] w-[13px]" />
            <span class="absolute left-[29.67px] top-[6.33px] text-[14px] font-medium leading-[20px] text-[#717182]"> 刷新</span>
          </button>

          <button type="button" class="relative h-[32px] w-[124.89px] rounded-[10px] bg-[#155DFC]">
            <img :src="workersRegister" alt="" class="absolute left-[12px] top-[9px] h-[14px] w-[14px]" />
            <span class="absolute left-[30px] top-[6.33px] text-[14px] font-medium leading-[20px] text-white">
              注册 Worker
            </span>
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-[16px] md:grid-cols-3">
        <div
          v-for="item in stats"
          :key="item.label"
          class="h-[84px] w-full max-w-[325.33px] rounded-[14px] px-[16px] pt-[16px]"
          :style="{ background: item.bg }"
        >
          <div class="text-[24px] font-semibold leading-[32px]" :style="{ color: item.valueColor }">{{ item.value }}</div>
          <div class="mt-[4px] text-[12px] leading-[16px] text-[#717182]">{{ item.label }}</div>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-[16px] md:grid-cols-2 lg:grid-cols-3">
        <WorkerCard v-for="w in workers" :key="w.name" :data="w" />
      </div>
    </div>
  </div>
</template>
