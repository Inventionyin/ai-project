<script setup lang="ts">
import { computed } from 'vue'
import type { PerformanceReportDetail } from '@/lib/aiTestingPlatformApi'

const props = defineProps<{
  report: PerformanceReportDetail | null
  loading?: boolean
  errorText?: string
}>()

const trendWidth = 760
const trendHeight = 240
const trendPadding = 20

const tpsValues = computed(() => (props.report?.trendPoints || []).map((item) => item.tps))
const rtValues = computed(() => (props.report?.trendPoints || []).map((item) => item.avgResponseMs))

function buildPolyline(values: number[], width: number, height: number, padding: number) {
  if (!values.length) return ''
  const max = Math.max(...values)
  const min = Math.min(...values)
  const innerWidth = width - padding * 2
  const innerHeight = height - padding * 2
  const len = values.length > 1 ? values.length - 1 : 1
  const delta = max - min || 1
  return values
    .map((value, index) => {
      const x = padding + (innerWidth * index) / len
      const y = padding + innerHeight - ((value - min) / delta) * innerHeight
      return `${x},${y}`
    })
    .join(' ')
}

const tpsLine = computed(() => buildPolyline(tpsValues.value, trendWidth, trendHeight, trendPadding))
const rtLine = computed(() => buildPolyline(rtValues.value, trendWidth, trendHeight, trendPadding))

const maxLatencyCount = computed(() => {
  const values = (props.report?.latencyDistribution || []).map((item) => item.count)
  return values.length ? Math.max(...values) : 1
})

const resourceRows = computed(() => {
  if (!props.report) return []
  return [
    { label: 'CPU 平均占用', value: props.report.resources.cpuAvg, max: 100, suffix: '%' },
    { label: 'CPU 峰值占用', value: props.report.resources.cpuMax, max: 100, suffix: '%' },
    { label: '内存平均占用', value: props.report.resources.memoryAvg, max: 100, suffix: '%' },
    { label: '内存峰值占用', value: props.report.resources.memoryMax, max: 100, suffix: '%' }
  ]
})
</script>

<template>
  <section class="w-full rounded-[14px] border border-black/10 bg-white p-[20px]">
    <div v-if="loading" class="py-[40px] text-center text-[14px] text-[#717182]">性能报告加载中...</div>
    <div v-else-if="errorText" class="py-[40px] text-center text-[14px] text-[#E7000B]">{{ errorText }}</div>
    <div v-else-if="!report" class="py-[40px] text-center text-[14px] text-[#717182]">暂无可展示的性能报告</div>

    <div v-else class="flex flex-col gap-[20px]">
      <div class="flex flex-wrap items-start justify-between gap-[12px]">
        <div class="min-w-0">
          <div class="flex items-center gap-[8px]">
            <div class="text-[16px] font-semibold leading-[24px] text-[#0A0A0A]">{{ report.name }}</div>
            <div
              class="h-[20px] rounded-full px-[8px] text-[12px] leading-[20px]"
              :class="report.status === 'PASSED' ? 'bg-[#E8F7EC] text-[#18A058]' : report.status === 'RUNNING' ? 'bg-[#E6F4FF] text-[#155DFC]' : 'bg-[#FFE2E2] text-[#E7000B]'"
            >
              {{ report.status }}
            </div>
          </div>
          <div class="mt-[4px] truncate text-[12px] leading-[16px] text-[#717182]">
            {{ new Date(report.createdAt * 1000).toLocaleString() }} · {{ report.duration }} · {{ report.vus }} VUs
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-[12px] md:grid-cols-5">
        <div class="rounded-[10px] border border-black/10 bg-[#FAFAFA] p-[12px]">
          <div class="text-[12px] text-[#717182]">TPS</div>
          <div class="mt-[4px] text-[22px] font-semibold text-[#0A0A0A]">{{ report.tps.toFixed(1) }}</div>
        </div>
        <div class="rounded-[10px] border border-black/10 bg-[#FAFAFA] p-[12px]">
          <div class="text-[12px] text-[#717182]">平均响应时间</div>
          <div class="mt-[4px] text-[22px] font-semibold text-[#0A0A0A]">{{ report.avgResponseMs.toFixed(1) }}ms</div>
        </div>
        <div class="rounded-[10px] border border-black/10 bg-[#FAFAFA] p-[12px]">
          <div class="text-[12px] text-[#717182]">P95 响应时间</div>
          <div class="mt-[4px] text-[22px] font-semibold text-[#0A0A0A]">{{ report.p95ResponseMs.toFixed(1) }}ms</div>
        </div>
        <div class="rounded-[10px] border border-black/10 bg-[#FAFAFA] p-[12px]">
          <div class="text-[12px] text-[#717182]">成功率</div>
          <div class="mt-[4px] text-[22px] font-semibold text-[#18A058]">{{ report.successRate.toFixed(1) }}%</div>
        </div>
        <div class="rounded-[10px] border border-black/10 bg-[#FAFAFA] p-[12px]">
          <div class="text-[12px] text-[#717182]">磁盘 IO</div>
          <div class="mt-[4px] text-[16px] font-semibold text-[#0A0A0A]">
            R {{ report.resources.ioReadMb.toFixed(1) }}MB / W {{ report.resources.ioWriteMb.toFixed(1) }}MB
          </div>
        </div>
      </div>

      <div class="rounded-[12px] border border-black/10 p-[12px]">
        <div class="text-[14px] font-medium text-[#0A0A0A]">TPS 趋势图 / 平均响应时间趋势图</div>
        <svg :viewBox="`0 0 ${trendWidth} ${trendHeight}`" class="mt-[10px] h-[240px] w-full rounded-[8px] bg-[#F8FAFC]">
          <polyline v-if="tpsLine" :points="tpsLine" fill="none" stroke="#155DFC" stroke-width="2.5" />
          <polyline v-if="rtLine" :points="rtLine" fill="none" stroke="#F59E0B" stroke-width="2.5" />
        </svg>
        <div class="mt-[8px] flex items-center gap-[16px] text-[12px] text-[#717182]">
          <div class="flex items-center gap-[6px]">
            <span class="inline-block h-[8px] w-[8px] rounded-full bg-[#155DFC]" />
            TPS
          </div>
          <div class="flex items-center gap-[6px]">
            <span class="inline-block h-[8px] w-[8px] rounded-full bg-[#F59E0B]" />
            平均响应时间
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-[16px] md:grid-cols-2">
        <div class="rounded-[12px] border border-black/10 p-[12px]">
          <div class="text-[14px] font-medium text-[#0A0A0A]">响应时间分布</div>
          <div class="mt-[12px] flex flex-col gap-[10px]">
            <div v-for="bucket in report.latencyDistribution" :key="bucket.label" class="grid grid-cols-[64px_1fr_60px] items-center gap-[10px]">
              <div class="text-[12px] text-[#717182]">{{ bucket.label }}</div>
              <div class="h-[8px] rounded-full bg-[#EEF2FF]">
                <div
                  class="h-full rounded-full bg-[#4F7DFF]"
                  :style="{ width: `${Math.max(8, (bucket.count / maxLatencyCount) * 100)}%` }"
                />
              </div>
              <div class="text-right text-[12px] text-[#0A0A0A]">{{ bucket.count }}</div>
            </div>
          </div>
        </div>

        <div class="rounded-[12px] border border-black/10 p-[12px]">
          <div class="text-[14px] font-medium text-[#0A0A0A]">服务器资源占用</div>
          <div class="mt-[12px] flex flex-col gap-[10px]">
            <div v-for="item in resourceRows" :key="item.label">
              <div class="mb-[4px] flex items-center justify-between text-[12px]">
                <span class="text-[#717182]">{{ item.label }}</span>
                <span class="text-[#0A0A0A]">{{ item.value.toFixed(1) }}{{ item.suffix }}</span>
              </div>
              <div class="h-[8px] rounded-full bg-[#F3F4F6]">
                <div class="h-full rounded-full bg-[#155DFC]" :style="{ width: `${Math.min(100, (item.value / item.max) * 100)}%` }" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="rounded-[12px] border border-black/10 p-[12px]">
        <div class="text-[14px] font-medium text-[#0A0A0A]">单接口断言统计</div>
        <div class="mt-[10px] overflow-x-auto">
          <table class="w-full min-w-[520px] border-collapse text-left">
            <thead>
              <tr class="border-b border-black/10 text-[12px] text-[#717182]">
                <th class="px-[8px] py-[8px] font-medium">接口</th>
                <th class="px-[8px] py-[8px] font-medium">通过</th>
                <th class="px-[8px] py-[8px] font-medium">失败</th>
                <th class="px-[8px] py-[8px] font-medium">通过率</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in report.asserts" :key="item.apiName" class="border-b border-black/5 text-[13px] text-[#0A0A0A]">
                <td class="px-[8px] py-[10px]">{{ item.apiName }}</td>
                <td class="px-[8px] py-[10px] text-[#18A058]">{{ item.passed }}</td>
                <td class="px-[8px] py-[10px]" :class="item.failed > 0 ? 'text-[#E7000B]' : 'text-[#717182]'">{{ item.failed }}</td>
                <td class="px-[8px] py-[10px]">
                  {{
                    ((item.passed / Math.max(1, item.passed + item.failed)) * 100).toFixed(1)
                  }}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>
