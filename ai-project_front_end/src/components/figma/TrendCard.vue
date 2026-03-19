<script setup lang="ts">
const xLabels = ['03-08', '03-09', '03-10', '03-11', '03-12', '03-13', '03-14']
const passRate = [40, 65, 50, 85, 70, 90, 33]
const failCount = [2, 1, 3, 1, 2, 0, 4]

const chartWidth = 609
const chartHeight = 180
const paddingX = 44
const paddingTop = 16
const paddingBottom = 28

const axisLabelGap = 8
const leftAxisX = paddingX
const rightAxisX = chartWidth - paddingX

const plotWidth = rightAxisX - leftAxisX
const plotHeight = chartHeight - paddingTop - paddingBottom

const xForIndex = (i: number) => leftAxisX + (plotWidth * i) / (xLabels.length - 1)
const yForPassRate = (v: number) => paddingTop + (plotHeight * (100 - v)) / 100
const maxCount = 10
const yForCount = (v: number) => paddingTop + (plotHeight * (maxCount - v)) / maxCount

const percentTicks = [100, 75, 50, 25, 0]
const countTicks = [10, 8, 6, 4, 2, 0]

const passPoints = passRate.map((v, i) => `${xForIndex(i)},${yForPassRate(v)}`).join(' ')
const failPoints = failCount.map((v, i) => `${xForIndex(i)},${yForCount(v)}`).join(' ')
</script>

<template>
  <section class="w-full max-w-[650.67px] rounded-[14px] bg-white border-[0.6667px] border-black/10 p-[20.67px]">
    <div class="w-full flex items-start justify-between gap-4">
      <div>
        <div class="text-sm font-semibold leading-5 text-[#0A0A0A]">近 7 天趋势</div>
        <div class="mt-0.5 text-xs font-normal leading-4 text-[#717182]">通过率与失败数变化</div>
      </div>

      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
          <span class="w-[12px] h-[2px] rounded" style="background:#2B7FFF"></span>
          <span class="text-xs font-normal leading-4 text-[#717182]">通过率</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="w-[12px] h-[2px] rounded" style="background:#FF6467"></span>
          <span class="text-xs font-normal leading-4 text-[#717182]">失败数</span>
        </div>
      </div>
    </div>

    <div class="mt-4 w-full h-[180px] overflow-hidden rounded-[10px] bg-white">
      <svg
        :width="chartWidth"
        :height="chartHeight"
        class="w-full h-full"
        viewBox="0 0 609 180"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        aria-label="近 7 天趋势"
      >
        <g opacity="0.12" stroke="#0A0A0A" stroke-width="1">
          <line :x1="leftAxisX" y1="16" :x2="rightAxisX" y2="16" />
          <line :x1="leftAxisX" y1="52" :x2="rightAxisX" y2="52" />
          <line :x1="leftAxisX" y1="88" :x2="rightAxisX" y2="88" />
          <line :x1="leftAxisX" y1="124" :x2="rightAxisX" y2="124" />

          <line :x1="leftAxisX" :y1="paddingTop" :x2="leftAxisX" :y2="paddingTop + plotHeight" />
          <line :x1="rightAxisX" :y1="paddingTop" :x2="rightAxisX" :y2="paddingTop + plotHeight" />
        </g>

        <g font-family="Inter" font-size="12" fill="#717182">
          <text :x="leftAxisX - axisLabelGap" y="14" text-anchor="end">通过率</text>
          <text :x="rightAxisX + axisLabelGap" y="14" text-anchor="start">失败数</text>

          <g v-for="v in percentTicks" :key="`p-${v}`">
            <text :x="leftAxisX - axisLabelGap" :y="yForPassRate(v) + 4" text-anchor="end">{{ v }}%</text>
          </g>
          <g v-for="v in countTicks" :key="`c-${v}`">
            <text :x="rightAxisX + axisLabelGap" :y="yForCount(v) + 4" text-anchor="start">{{ v }}</text>
          </g>
        </g>

        <polyline :points="passPoints" stroke="#2B7FFF" stroke-width="2" fill="none" />
        <polyline :points="failPoints" stroke="#FF6467" stroke-width="2" fill="none" />

        <g v-for="(label, i) in xLabels" :key="label">
          <circle :cx="xForIndex(i)" :cy="yForPassRate(passRate[i])" r="3" fill="#2B7FFF" />
          <circle :cx="xForIndex(i)" :cy="yForCount(failCount[i])" r="3" fill="#FF6467" />
          <text
            :x="xForIndex(i)"
            y="172"
            text-anchor="middle"
            font-family="Inter"
            font-size="12"
            fill="#717182"
          >
            {{ label }}
          </text>
        </g>
      </svg>
    </div>
  </section>
</template>
