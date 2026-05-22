<script setup lang="ts">
import runsDuration from '@/assets/figma/ai-testing-platform/runs-duration.svg'
import runsRowActions from '@/assets/figma/ai-testing-platform/runs-row-actions.svg'
import runsStatusCancel from '@/assets/figma/ai-testing-platform/runs-status-cancel.svg'
import runsStatusFail from '@/assets/figma/ai-testing-platform/runs-status-fail.svg'
import runsStatusPass from '@/assets/figma/ai-testing-platform/runs-status-pass.svg'
import runsStatusRunning from '@/assets/figma/ai-testing-platform/runs-status-running.svg'
import runsTriggerCicd from '@/assets/figma/ai-testing-platform/runs-trigger-cicd.svg'
import runsTriggerManual from '@/assets/figma/ai-testing-platform/runs-trigger-manual.svg'
import runsTriggerSchedule from '@/assets/figma/ai-testing-platform/runs-trigger-schedule.svg'

type TriggerType = '手动' | 'CI/CD' | '定时' | '未知'
type RunStatus = '通过' | '失败' | '执行中' | '排队中' | '已取消'

export type RunRow = {
  runId: string
  trigger: TriggerType
  suiteName: string
  suiteSummary: string
  environment: string
  status: RunStatus
  passRate: string
  passRateColor: string
  startedAt: string
  duration: string
  createdBy: string
}

defineProps<{
  rows: RunRow[]
}>()

const emit = defineEmits<{
  (e: 'open-run', runId: string): void
}>()

function triggerMeta(type: TriggerType) {
  if (type === '手动') return { icon: runsTriggerManual, color: '#155DFC' }
  if (type === 'CI/CD') return { icon: runsTriggerCicd, color: '#9810FA' }
  if (type === '定时') return { icon: runsTriggerSchedule, color: '#F54900' }
  return { icon: runsTriggerManual, color: '#717182' }
}

function statusMeta(status: RunStatus) {
  if (status === '通过') return { icon: runsStatusPass, bg: '#DCFCE7', color: '#008236', width: '40px' }
  if (status === '失败') return { icon: runsStatusFail, bg: '#FFE2E2', color: '#E7000B', width: '40px' }
  if (status === '执行中') return { icon: runsStatusRunning, bg: '#DBEAFE', color: '#155DFC', width: '52px' }
  if (status === '排队中') return { icon: runsStatusRunning, bg: '#DBEAFE', color: '#155DFC', width: '52px' }
  return { icon: runsStatusCancel, bg: '#F3F4F6', color: '#6A7282', width: '52px' }
}

const rowMinHeight = '104.67px'
</script>

<template>
  <div class="w-full overflow-x-auto">
    <div class="w-full min-w-[920px]">
      <div
        class="grid grid-cols-[minmax(72px,0.9fr)_minmax(90px,1fr)_minmax(220px,2.4fr)_minmax(140px,1.2fr)_minmax(120px,1.1fr)_minmax(110px,1fr)_minmax(170px,1.5fr)_minmax(110px,1fr)_minmax(110px,1fr)_minmax(92px,0.9fr)] border-b border-black/10 bg-[rgba(236,236,240,0.3)]"
      >
        <div class="flex h-[56.33px] items-center px-[16px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]" style="font-family: Consolas">
            Run ID
          </div>
        </div>
        <div class="flex h-[56.33px] items-center px-[16px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]">触发方式</div>
        </div>
        <div class="flex h-[56.33px] items-center px-[16px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]">套件</div>
        </div>
        <div class="flex h-[56.33px] items-center px-[16px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]">环境</div>
        </div>
        <div class="flex h-[56.33px] items-center px-[16px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]">状态</div>
        </div>
        <div class="flex h-[56.33px] items-center px-[16px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]">通过率</div>
        </div>
        <div class="flex h-[56.33px] items-center px-[16px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]">开始时间</div>
        </div>
        <div class="flex h-[56.33px] items-center px-[16px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]">耗时</div>
        </div>
        <div class="flex h-[56.33px] items-center px-[16px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]">创建人</div>
        </div>
        <div class="h-[56.33px]" />
      </div>

      <div class="border-b border-black/10 bg-white">
        <div
          v-for="row in rows"
          :key="row.runId"
          class="grid grid-cols-[minmax(72px,0.9fr)_minmax(90px,1fr)_minmax(220px,2.4fr)_minmax(140px,1.2fr)_minmax(120px,1.1fr)_minmax(110px,1fr)_minmax(170px,1.5fr)_minmax(110px,1fr)_minmax(110px,1fr)_minmax(92px,0.9fr)] border-b border-black/10 last:border-b-0"
          :style="{ minHeight: rowMinHeight }"
        >
          <div class="flex items-center px-[16px] py-[12.33px]">
            <button
              type="button"
              class="w-full truncate text-left text-[12px] font-medium leading-[16px] text-[#155DFC]"
              style="font-family: Consolas"
              @click="emit('open-run', row.runId)"
            >
              {{ row.runId }}
            </button>
          </div>

          <div class="flex items-center px-[16px] py-[12.33px]">
            <div class="flex items-center gap-[4px]">
              <img :src="triggerMeta(row.trigger).icon" alt="" class="h-[12px] w-[12px] shrink-0" />
              <div class="truncate text-[12px] leading-[16px]" :style="{ color: triggerMeta(row.trigger).color }">
                {{ row.trigger }}
              </div>
            </div>
          </div>

          <div class="flex min-h-full flex-col justify-between px-[16px] py-[12.33px]">
            <div class="truncate text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
              {{ row.suiteName }}
            </div>
            <div class="truncate text-[12px] leading-[16px] text-[#717182]">{{ row.suiteSummary }}</div>
          </div>

          <div class="flex items-center px-[16px] py-[12.33px]">
            <div class="inline-flex max-w-full items-center rounded-[4px] bg-[#ECECF0] px-[8px] py-[2px] text-[12px] leading-[16px] text-[#0A0A0A]" style="font-family: Consolas">
              <span class="truncate">{{ row.environment }}</span>
            </div>
          </div>

          <div class="flex items-center px-[16px] py-[12.33px]">
            <div
              class="inline-flex h-[36px] items-center gap-[4px] rounded-full"
              :style="{ width: statusMeta(row.status).width, background: statusMeta(row.status).bg }"
            >
              <img :src="statusMeta(row.status).icon" alt="" class="ml-[8px] h-[11px] w-auto shrink-0" />
              <div class="truncate pr-[8px] text-[12px] font-medium leading-[16px]" :style="{ color: statusMeta(row.status).color }">
                {{ row.status }}
              </div>
            </div>
          </div>

          <div class="flex items-center justify-end px-[16px] py-[12.33px]">
            <div class="truncate text-right text-[12px] font-medium leading-[16px]" :style="{ color: row.passRateColor }">
              {{ row.passRate }}
            </div>
          </div>

          <div class="flex items-center px-[16px] py-[12.33px]">
            <div class="truncate text-[12px] leading-[16px] text-[#717182]">{{ row.startedAt }}</div>
          </div>

          <div class="flex items-center px-[16px] py-[12.33px]">
            <div class="flex items-center gap-[4px]">
              <img :src="runsDuration" alt="" class="h-[11px] w-auto shrink-0" />
              <div class="truncate text-[12px] leading-[16px] text-[#717182]">{{ row.duration }}</div>
            </div>
          </div>

          <div class="flex items-center px-[16px] py-[12.33px]">
            <div class="truncate text-[12px] leading-[16px] text-[#717182]">{{ row.createdBy }}</div>
          </div>

          <div class="flex items-center px-[16px] py-[12.33px]">
            <button type="button" class="h-[28px] w-[92px] shrink-0">
              <img :src="runsRowActions" alt="" class="h-full w-full" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
