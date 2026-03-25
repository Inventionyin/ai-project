<script setup lang="ts">
import { computed } from 'vue'
import type { UiTestReportDetail } from '@/lib/aiTestingPlatformApi'

const props = defineProps<{
  report: UiTestReportDetail | null
  loading?: boolean
  errorText?: string
}>()

const passRateText = computed(() => {
  const total = props.report?.summary.total || 0
  const passed = props.report?.summary.passed || 0
  const rate = total > 0 ? (passed / total) * 100 : 0
  return `${rate.toFixed(1)}%`
})

function statusClass(status: string) {
  if (status === 'COMPLETED') return 'bg-[#E8F7EC] text-[#18A058]'
  if (status === 'RUNNING') return 'bg-[#E6F4FF] text-[#155DFC]'
  return 'bg-[#FFE2E2] text-[#E7000B]'
}
</script>

<template>
  <section class="w-full rounded-[14px] border border-black/10 bg-white p-[20px]">
    <div v-if="loading" class="py-[40px] text-center text-[14px] text-[#717182]">UI 测试报告加载中...</div>
    <div v-else-if="errorText" class="py-[40px] text-center text-[14px] text-[#E7000B]">{{ errorText }}</div>
    <div v-else-if="!report" class="py-[40px] text-center text-[14px] text-[#717182]">暂无可展示的 UI 测试报告</div>

    <div v-else class="flex flex-col gap-[20px]">
      <div class="flex flex-wrap items-start justify-between gap-[12px]">
        <div class="min-w-0">
          <div class="flex items-center gap-[8px]">
            <div class="text-[16px] font-semibold leading-[24px] text-[#0A0A0A]">
              {{ report.pageId }} · {{ report.assertLevel }}
            </div>
            <div class="h-[20px] rounded-full px-[8px] text-[12px] leading-[20px]" :class="statusClass(report.status)">
              {{ report.status }}
            </div>
          </div>
          <div class="mt-[4px] truncate text-[12px] leading-[16px] text-[#717182]">
            Run {{ report.runId }} · {{ new Date(report.startedAt * 1000).toLocaleString() }}
          </div>
        </div>
        <a :href="report.reportIndexUrl" target="_blank" rel="noreferrer" class="text-[13px] font-medium leading-[20px] text-[#155DFC] hover:underline">
          打开报告
        </a>
      </div>

      <div class="grid grid-cols-1 gap-[12px] md:grid-cols-5">
        <div class="rounded-[10px] border border-black/10 bg-[#FAFAFA] p-[12px]">
          <div class="text-[12px] text-[#717182]">总用例</div>
          <div class="mt-[4px] text-[22px] font-semibold text-[#0A0A0A]">{{ report.summary.total }}</div>
        </div>
        <div class="rounded-[10px] border border-black/10 bg-[#FAFAFA] p-[12px]">
          <div class="text-[12px] text-[#717182]">通过</div>
          <div class="mt-[4px] text-[22px] font-semibold text-[#18A058]">{{ report.summary.passed }}</div>
        </div>
        <div class="rounded-[10px] border border-black/10 bg-[#FAFAFA] p-[12px]">
          <div class="text-[12px] text-[#717182]">失败</div>
          <div class="mt-[4px] text-[22px] font-semibold text-[#E7000B]">{{ report.summary.failed }}</div>
        </div>
        <div class="rounded-[10px] border border-black/10 bg-[#FAFAFA] p-[12px]">
          <div class="text-[12px] text-[#717182]">跳过</div>
          <div class="mt-[4px] text-[22px] font-semibold text-[#0A0A0A]">{{ report.summary.skipped }}</div>
        </div>
        <div class="rounded-[10px] border border-black/10 bg-[#FAFAFA] p-[12px]">
          <div class="text-[12px] text-[#717182]">通过率</div>
          <div class="mt-[4px] text-[22px] font-semibold text-[#155DFC]">{{ passRateText }}</div>
        </div>
      </div>

      <div class="rounded-[12px] border border-black/10 p-[12px]">
        <div class="text-[14px] font-medium text-[#0A0A0A]">执行信息</div>
        <div class="mt-[10px] grid grid-cols-1 gap-[8px] text-[13px] leading-[20px] text-[#717182]">
          <div>结果状态：{{ report.result }}</div>
          <div>执行耗时：{{ report.summary.durationMs }} ms</div>
          <div class="truncate">Spec 路径：{{ report.specPath }}</div>
          <div class="truncate">报告目录：{{ report.reportDir }}</div>
        </div>
      </div>

      <div class="rounded-[12px] border border-black/10 p-[12px]">
        <div class="text-[14px] font-medium text-[#0A0A0A]">失败用例</div>
        <div v-if="!report.failedCases.length" class="mt-[10px] text-[13px] text-[#717182]">无失败用例</div>
        <div v-else class="mt-[10px] overflow-x-auto">
          <table class="w-full min-w-[680px] border-collapse text-left">
            <thead>
              <tr class="border-b border-black/10 text-[12px] text-[#717182]">
                <th class="px-[8px] py-[8px] font-medium">标题</th>
                <th class="px-[8px] py-[8px] font-medium">错误</th>
                <th class="px-[8px] py-[8px] font-medium">截图</th>
                <th class="px-[8px] py-[8px] font-medium">Trace</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in report.failedCases" :key="`${item.title}-${item.error}`" class="border-b border-black/5 text-[13px] text-[#0A0A0A]">
                <td class="px-[8px] py-[10px]">{{ item.title }}</td>
                <td class="px-[8px] py-[10px] text-[#E7000B]">{{ item.error }}</td>
                <td class="px-[8px] py-[10px]">
                  <a v-if="item.screenshot" :href="item.screenshot" target="_blank" rel="noreferrer" class="text-[#155DFC] hover:underline">查看</a>
                  <span v-else class="text-[#717182]">-</span>
                </td>
                <td class="px-[8px] py-[10px]">
                  <a v-if="item.trace" :href="item.trace" target="_blank" rel="noreferrer" class="text-[#155DFC] hover:underline">查看</a>
                  <span v-else class="text-[#717182]">-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>
