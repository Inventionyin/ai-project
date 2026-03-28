<script setup lang="ts">
import workersCpu from '@/assets/figma/ai-testing-platform-workers/workers-cpu.svg'
import workersHeartbeat from '@/assets/figma/ai-testing-platform-workers/workers-heartbeat.svg'
import workersMem from '@/assets/figma/ai-testing-platform-workers/workers-mem.svg'
import workersOfflineBadge from '@/assets/figma/ai-testing-platform-workers/workers-offline-badge.svg'
import workersOfflineDot from '@/assets/figma/ai-testing-platform-workers/workers-offline-dot.svg'
import workersOnlineBadge from '@/assets/figma/ai-testing-platform-workers/workers-online-badge.svg'
import workersOnlineDot from '@/assets/figma/ai-testing-platform-workers/workers-online-dot.svg'
import workersSlots from '@/assets/figma/ai-testing-platform-workers/workers-slots.svg'

type WorkerStatus = '在线' | '离线'

type WorkerCardData = {
  name: string
  status: WorkerStatus
  version: string
  capabilities: readonly string[]
  slotsText: string
  slotsStateText: string
  cpuPercent?: number
  cpuBarColor?: string
  memPercent?: number
  memBarColor?: string
  heartbeatText: string
  isFaded?: boolean
  borderColor?: string
}

defineProps<{
  data: WorkerCardData
}>()

function clampPercent(value: number) {
  return Math.max(0, Math.min(100, value))
}
</script>

<template>
  <div
    class="w-full max-w-[325.33px] rounded-[14px] border border-black/10 bg-white px-[20.67px] pb-[0.67px] pt-[20.67px]"
    :style="{ opacity: data.isFaded ? 0.7 : 1, borderColor: data.borderColor || undefined }"
  >
    <div class="flex items-start justify-between">
      <div class="flex min-w-0 items-center gap-[10px]">
        <img
          :src="data.status === '在线' ? workersOnlineBadge : workersOfflineBadge"
          alt=""
          class="h-[36px] w-[36px] rounded-[10px]"
        />
        <div class="min-w-0">
          <div class="truncate text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">{{ data.name }}</div>
          <div class="mt-[2px] flex items-center gap-[4px]">
            <img :src="data.status === '在线' ? workersOnlineDot : workersOfflineDot" alt="" class="h-[11px] w-[11px]" />
            <div
              class="text-[12px] leading-[16px]"
              :style="{ color: data.status === '在线' ? '#00A63E' : '#FB2C36' }"
            >
              {{ data.status }}
            </div>
          </div>
        </div>
      </div>

      <div
        class="h-[20px] rounded-[4px] bg-[#ECECF0] px-[8px] py-[2px] text-[12px] leading-[16px] text-[#0A0A0A]"
        style="font-family: Consolas"
      >
        {{ data.version }}
      </div>
    </div>

    <div class="mt-[12px] grid grid-cols-2 gap-[16px]">
      <div class="h-[60px] rounded-[10px] bg-[rgba(236,236,240,0.4)] px-[10px] pt-[10px]">
        <div class="text-[12px] leading-[16px] text-[#717182]">能力</div>
        <div class="mt-[4px] flex flex-wrap gap-[4px]">
          <div
            v-for="cap in data.capabilities"
            :key="cap"
            class="h-[20px] rounded-[4px] bg-[#DBEAFE] px-[6px] py-[2px] text-[12px] leading-[16px] text-[#1447E6]"
          >
            {{ cap }}
          </div>
        </div>
      </div>

      <div class="h-[60px] rounded-[10px] bg-[rgba(236,236,240,0.4)] px-[10px] pt-[10px]">
        <div class="text-[12px] leading-[16px] text-[#717182]">槽位</div>
        <div class="mt-[4px] flex items-center gap-[4px]">
          <img :src="workersSlots" alt="" class="h-[12px] w-[12px]" />
          <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">{{ data.slotsText }}</div>
          <div class="text-[12px] leading-[16px] text-[#717182]">{{ data.slotsStateText }}</div>
        </div>
      </div>
    </div>

    <div v-if="typeof data.cpuPercent === 'number' && typeof data.memPercent === 'number'" class="mt-[12px] space-y-[8px]">
      <div class="space-y-[4px]">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-[4px] text-[12px] leading-[16px] text-[#717182]">
            <img :src="workersCpu" alt="" class="h-[11px] w-[11px]" />
            <span> CPU</span>
          </div>
          <div class="text-[12px] leading-[16px] text-[#0A0A0A]">{{ clampPercent(data.cpuPercent) }}%</div>
        </div>
        <div class="h-[6px] w-full overflow-hidden rounded-full bg-[#ECECF0]">
          <div
            class="h-full rounded-full"
            :style="{ width: `${clampPercent(data.cpuPercent)}%`, background: data.cpuBarColor || '#FDC700' }"
          />
        </div>
      </div>

      <div class="space-y-[4px]">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-[4px] text-[12px] leading-[16px] text-[#717182]">
            <img :src="workersMem" alt="" class="h-[11px] w-[11px]" />
            <span> MEM</span>
          </div>
          <div class="text-[12px] leading-[16px] text-[#0A0A0A]">{{ clampPercent(data.memPercent) }}%</div>
        </div>
        <div class="h-[6px] w-full overflow-hidden rounded-full bg-[#ECECF0]">
          <div
            class="h-full rounded-full"
            :style="{ width: `${clampPercent(data.memPercent)}%`, background: data.memBarColor || '#51A2FF' }"
          />
        </div>
      </div>
    </div>

    <div class="mt-[12px] flex items-center gap-[4px]">
      <img :src="workersHeartbeat" alt="" class="h-[11px] w-[11px]" />
      <div class="text-[12px] leading-[16px] text-[#717182]">{{ data.heartbeatText }}</div>
    </div>
  </div>
</template>
