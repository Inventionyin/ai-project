<script setup lang="ts">
import suiteCardIcon from '@/assets/figma/ai-testing-platform/suite-card-icon.svg'
import suiteStatusPass from '@/assets/figma/ai-testing-platform/suite-status-pass.svg'
import suiteStatusFail from '@/assets/figma/ai-testing-platform/suite-status-fail.svg'
import suiteActionRun from '@/assets/figma/ai-testing-platform/suite-action-run.svg'
import suiteAction1 from '@/assets/figma/ai-testing-platform/suite-action-1.svg'
import suiteAction2 from '@/assets/figma/ai-testing-platform/suite-action-2.svg'

export type SuiteCardData = {
  id: string
  title: string
  owner: string
  status: 'pass' | 'fail'
  caseCount: string
  concurrency: string
  timeout: string
  retry: string
  environment: string
  defaultEnvId?: string | null
  lastRunAt: string
  metaRowHeight?: 16 | 32
}

const suiteActionArrange = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTMiIGhlaWdodD0iMTMiIHZpZXdCb3g9IjAgMCAxMyAxMyIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGcgY2xpcC1wYXRoPSJ1cmwoI2NsaXAwXzQ3XzE2NjQpIj4KPHBhdGggZD0iTTYuNjE5MTcgMS4wODMzNEg2LjM4MDgzQzYuMDkzNTIgMS4wODMzNCA1LjgxNzk3IDEuMTk3NDggNS42MTQ4IDEuNDAwNjRDNS40MTE2NCAxLjYwMzgxIDUuMjk3NSAxLjg3OTM2IDUuMjk3NSAyLjE2NjY4VjIuMjY0MThDNS4yOTczMSAyLjQ1NDE1IDUuMjQ3MTYgMi42NDA3NCA1LjE1MjA4IDIuODA1MjFDNS4wNTcwMSAyLjk2OTY5IDQuOTIwMzYgMy4xMDYyNyA0Ljc1NTgzIDMuMjAxMjZMNC41MjI5MiAzLjMzNjY4QzQuMzU4MjMgMy40MzE3NiA0LjE3MTQyIDMuNDgxODIgMy45ODEyNSAzLjQ4MTgyQzMuNzkxMDkgMy40ODE4MiAzLjYwNDI3IDMuNDMxNzYgMy40Mzk1OCAzLjMzNjY4TDMuMzU4MzMgMy4yOTMzNEMzLjEwOTc0IDMuMTQ5OTQgMi44MTQ0MSAzLjExMTA0IDIuNTM3MTcgMy4xODUxOEMyLjI1OTkyIDMuMjU5MzEgMi4wMjM0MiAzLjQ0MDQzIDEuODc5NTggMy42ODg3NkwxLjc2MDQyIDMuODk0NTlDMS42MTcwMiA0LjE0MzE4IDEuNTc4MTIgNC40Mzg1MiAxLjY1MjI1IDQuNzE1NzZDMS43MjYzOSA0Ljk5MyAxLjkwNzUgNS4yMjk1IDIuMTU1ODMgNS4zNzMzNEwyLjIzNzA4IDUuNDI3NTFDMi40MDA4MiA1LjUyMjA0IDIuNTM2OTYgNS42NTc3NyAyLjYzMTk5IDUuODIxMjFDMi43MjcwMSA1Ljk4NDY1IDIuNzc3NjEgNi4xNzAxMiAyLjc3ODc1IDYuMzU5MThWNi42MzU0M0MyLjc3OTUxIDYuODI2MzIgMi43Mjk4MSA3LjAxNDAzIDIuNjM0NjkgNy4xNzk1NEMyLjUzOTU3IDcuMzQ1MDQgMi40MDI0MSA3LjQ4MjQ4IDIuMjM3MDggNy41Nzc5M0wyLjE1NTgzIDcuNjI2NjhDMS45MDc1IDcuNzcwNTIgMS43MjYzOSA4LjAwNzAyIDEuNjUyMjUgOC4yODQyNkMxLjU3ODEyIDguNTYxNTEgMS42MTcwMiA4Ljg1Njg0IDEuNzYwNDIgOS4xMDU0M0wxLjg3OTU4IDkuMzExMjZDMi4wMjM0MiA5LjU1OTYgMi4yNTk5MiA5Ljc0MDcxIDIuNTM3MTcgOS44MTQ4NEMyLjgxNDQxIDkuODg4OTggMy4xMDk3NCA5Ljg1MDA4IDMuMzU4MzMgOS43MDY2OEwzLjQzOTU4IDkuNjYzMzRDMy42MDQyNyA5LjU2ODI2IDMuNzkxMDkgOS41MTgyIDMuOTgxMjUgOS41MTgyQzQuMTcxNDIgOS41MTgyIDQuMzU4MjMgOS41NjgyNiA0LjUyMjkyIDkuNjYzMzRMNC43NTU4MyA5Ljc5ODc2QzQuOTIwMzYgOS44OTM3NSA1LjA1NzAxIDEwLjAzMDMgNS4xNTIwOCAxMC4xOTQ4QzUuMjQ3MTYgMTAuMzU5MyA1LjI5NzMxIDEwLjU0NTkgNS4yOTc1IDEwLjczNThWMTAuODMzM0M1LjI5NzUgMTEuMTIwNyA1LjQxMTY0IDExLjM5NjIgNS42MTQ4IDExLjU5OTRDNS44MTc5NyAxMS44MDI1IDYuMDkzNTIgMTEuOTE2NyA2LjM4MDgzIDExLjkxNjdINi42MTkxN0M2LjkwNjQ5IDExLjkxNjcgNy4xODIwNCAxMS44MDI1IDcuMzg1MiAxMS41OTk0QzcuNTg4MzYgMTEuMzk2MiA3LjcwMjUgMTEuMTIwNyA3LjcwMjUgMTAuODMzM1YxMC43MzU4QzcuNzAyNyAxMC41NDU5IDcuNzUyODUgMTAuMzU5MyA3Ljg0NzkyIDEwLjE5NDhDNy45NDI5OSAxMC4wMzAzIDguMDc5NjQgOS44OTM3NSA4LjI0NDE3IDkuNzk4NzZMOC40NzcwOCA5LjY2MzM0QzguNjQxNzcgOS41NjgyNiA4LjgyODU5IDkuNTE4MiA5LjAxODc1IDkuNTE4MkM5LjIwODkyIDkuNTE4MiA5LjM5NTczIDkuNTY4MjYgOS41NjA0MiA5LjY2MzM0TDkuNjQxNjcgOS43MDY2OEM5Ljg5MDI2IDkuODUwMDggMTAuMTg1NiA5Ljg4ODk4IDEwLjQ2MjggOS44MTQ4NEMxMC43NDAxIDkuNzQwNzEgMTAuOTc2NiA5LjU1OTYgMTEuMTIwNCA5LjMxMTI2TDExLjIzOTYgOS4xMDAwMUMxMS4zODMgOC44NTE0MiAxMS40MjE5IDguNTU2MDkgMTEuMzQ3OCA4LjI3ODg0QzExLjI3MzYgOC4wMDE2IDExLjA5MjUgNy43NjUxIDEwLjg0NDIgNy42MjEyNkwxMC43NjI5IDcuNTc3OTNDMTAuNTk3NiA3LjQ4MjQ4IDEwLjQ2MDQgNy4zNDUwNCAxMC4zNjUzIDcuMTc5NTRDMTAuMjcwMiA3LjAxNDAzIDEwLjIyMDUgNi44MjYzMiAxMC4yMjEzIDYuNjM1NDNWNi4zNjQ1OUMxMC4yMjA1IDYuMTczNyAxMC4yNzAyIDUuOTg1OTkgMTAuMzY1MyA1LjgyMDQ5QzEwLjQ2MDQgNS42NTQ5OCAxMC41OTc2IDUuNTE3NTQgMTAuNzYyOSA1LjQyMjA5TDEwLjg0NDIgNS4zNzMzNEMxMS4wOTI1IDUuMjI5NSAxMS4yNzM2IDQuOTkzIDExLjM0NzggNC43MTU3NkMxMS40MjE5IDQuNDM4NTIgMTEuMzgzIDQuMTQzMTggMTEuMjM5NiAzLjg5NDU5TDExLjEyMDQgMy42ODg3NkMxMC45NzY2IDMuNDQwNDMgMTAuNzQwMSAzLjI1OTMxIDEwLjQ2MjggMy4xODUxOEMxMC4xODU2IDMuMTExMDQgOS44OTAyNiAzLjE0OTk0IDkuNjQxNjcgMy4yOTMzNEw5LjU2MDQyIDMuMzM2NjhDOS4zOTU3MyAzLjQzMTc2IDkuMjA4OTIgMy40ODE4MiA5LjAxODc1IDMuNDgxODJDOC44Mjg1OSAzLjQ4MTgyIDguNjQxNzcgMy40MzE3NiA4LjQ3NzA4IDMuMzM2NjhMOC4yNDQxNyAzLjIwMTI2QzguMDc5NjQgMy4xMDYyNyA3Ljk0Mjk5IDIuOTY5NjkgNy44NDc5MiAyLjgwNTIxQzcuNzUyODUgMi42NDA3NCA3LjcwMjcgMi40NTQxNSA3LjcwMjUgMi4yNjQxOFYyLjE2NjY4QzcuNzAyNSAxLjg3OTM2IDcuNTg4MzYgMS42MDM4MSA3LjM4NTIgMS40MDA2NEM3LjE4MjA0IDEuMTk3NDggNi45MDY0OSAxLjA4MzM0IDYuNjE5MTcgMS4wODMzNFoiIHN0cm9rZT0iIzcxNzE4MiIgc3Ryb2tlLXdpZHRoPSIxLjA4MzMzIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPHBhdGggZD0iTTYuNSA4LjEyNUM3LjM5NzQ2IDguMTI1IDguMTI1IDcuMzk3NDYgOC4xMjUgNi41QzguMTI1IDUuNjAyNTQgNy4zOTc0NiA0Ljg3NSA2LjUgNC44NzVDNS42MDI1NCA0Ljg3NSA0Ljg3NSA1LjYwMjU0IDQuODc1IDYuNUM0Ljg3NSA3LjM5NzQ2IDUuNjAyNTQgOC4xMjUgNi41IDguMTI1WiIgc3Ryb2tlPSIjNzE3MTgyIiBzdHJva2Utd2lkdGg9IjEuMDgzMzMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L2c+CjxkZWZzPgo8Y2xpcFBhdGggaWQ9ImNsaXAwXzQ3XzE2NjQiPgo8cmVjdCB3aWR0aD0iMTMiIGhlaWdodD0iMTMiIGZpbGw9IndoaXRlIi8+CjwvY2xpcFBhdGg+CjwvZGVmcz4KPC9zdmc+Cg=='

const props = defineProps<{
  suite: SuiteCardData
}>()

const emit = defineEmits<{
  (e: 'run'): void
  (e: 'delete'): void
  (e: 'arrange'): void
}>()

function getCardHeight() {
  return props.suite.metaRowHeight === 32 ? '231.33px' : '215.33px'
}

function getMetaRowHeight() {
  return props.suite.metaRowHeight === 32 ? '32px' : '16px'
}

function getActionsTop() {
  return props.suite.metaRowHeight === 32 ? '178.67px' : '162.67px'
}
</script>

<template>
  <div
    class="relative w-full rounded-[14px] border border-black/10 bg-white lg:w-[317.33px]"
    :style="{ height: getCardHeight() }"
  >
    <div class="absolute left-[20.67px] top-[20.67px] flex h-[38px] w-[276px] items-start justify-between">
      <div class="flex h-[38px] w-[130px] items-center gap-[10px]">
        <div class="flex h-[36px] w-[36px] items-center justify-center rounded-[10px] bg-[#E0E7FF]">
          <img :src="suiteCardIcon" alt="" class="h-[17px] w-[17px]" />
        </div>
        <div class="flex min-w-0 flex-1 flex-col gap-[2px]">
          <div class="truncate text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">{{ suite.title }}</div>
          <div class="truncate text-[12px] leading-[16px] text-[#717182]">维护人：{{ suite.owner }}</div>
        </div>
      </div>

      <div class="flex h-[16px] w-[40px] items-center">
        <img :src="suite.status === 'pass' ? suiteStatusPass : suiteStatusFail" alt="" class="h-[12px] w-[12px]" />
        <span
          class="ml-[4px] text-[12px] leading-[16px]"
          :class="suite.status === 'pass' ? 'text-[#00A63E]' : 'text-[#FB2C36]'"
        >
          {{ suite.status === 'pass' ? '通过' : '失败' }}
        </span>
      </div>
    </div>

    <div class="absolute left-[20.67px] top-[70.67px] flex h-[48px] w-[276px] gap-[8px]">
      <div class="flex h-[48px] w-[63px] flex-col items-center rounded-[10px] bg-[rgba(236,236,240,0.4)] pt-[6px]">
        <div class="text-center text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">{{ suite.caseCount }}</div>
        <div class="text-center text-[12px] leading-[16px] text-[#717182]">用例数</div>
      </div>
      <div class="flex h-[48px] w-[63px] flex-col items-center rounded-[10px] bg-[rgba(236,236,240,0.4)] pt-[6px]">
        <div class="text-center text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">{{ suite.concurrency }}</div>
        <div class="text-center text-[12px] leading-[16px] text-[#717182]">并发</div>
      </div>
      <div class="flex h-[48px] w-[63px] flex-col items-center rounded-[10px] bg-[rgba(236,236,240,0.4)] pt-[6px]">
        <div class="text-center text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">{{ suite.timeout }}</div>
        <div class="text-center text-[12px] leading-[16px] text-[#717182]">超时</div>
      </div>
      <div class="flex h-[48px] w-[63px] flex-col items-center rounded-[10px] bg-[rgba(236,236,240,0.4)] pt-[6px]">
        <div class="text-center text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">{{ suite.retry }}</div>
        <div class="text-center text-[12px] leading-[16px] text-[#717182]">重试</div>
      </div>
    </div>

    <div
      class="absolute left-[20.67px] top-[134.67px] flex w-[276px] gap-[8px] text-[12px] leading-[16px] text-[#717182]"
      :class="suite.metaRowHeight === 32 ? 'items-start' : 'items-center'"
      :style="{ height: getMetaRowHeight() }"
    >
      <span class="shrink-0">环境：{{ suite.environment }}</span>
      <span class="shrink-0">·</span>
      <span class="min-w-0 flex-1">最近运行：{{ suite.lastRunAt }}</span>
    </div>

    <div class="absolute left-[20.67px] flex h-[32px] w-[276px] items-center gap-[8px]" :style="{ top: getActionsTop() }">
      <button type="button" class="relative h-[32px] w-[68.33px] rounded-[10px] border border-black/10 bg-white" @click="emit('arrange')">
        <img :src="suiteActionArrange" alt="" class="absolute left-[12.67px] top-[9.5px] h-[13px] w-[13px]" />
        <span class="absolute left-[29.67px] top-[8px] text-[12px] font-medium leading-[16px] text-[#717182]">
          编排
        </span>
      </button>

      <button type="button" class="relative h-[32px] w-[67px] rounded-[10px] bg-[#155DFC]" @click="emit('run')">
        <img :src="suiteActionRun" alt="" class="absolute left-[12px] top-[9.5px] h-[13px] w-[13px]" />
        <span class="absolute left-[29px] top-[8px] text-[12px] font-medium leading-[16px] text-white">
          运行
        </span>
      </button>

      <button type="button" class="h-[32px] w-[32px]">
        <img :src="suiteAction1" alt="" class="h-full w-full" />
      </button>

      <button type="button" class="h-[32px] w-[32px]" @click="emit('delete')">
        <img :src="suiteAction2" alt="" class="h-full w-full" />
      </button>
    </div>
  </div>
</template>
