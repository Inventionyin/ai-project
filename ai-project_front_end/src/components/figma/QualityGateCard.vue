<script setup lang="ts">
import { computed } from 'vue'
import { AlertTriangle, CheckCircle2, Shield } from 'lucide-vue-next'

type GateItem = {
  label: string
  value: string
  threshold: string
  valueColor: string
  icon: any
  iconColor: string
}

type QualityGateInputItem = {
  name: string
  threshold: string
  current: string
  passed: boolean
}

type QualityGateOverall = 'PASSED' | 'PARTIAL_FAIL' | 'FAILED' | 'UNKNOWN'

const props = withDefaults(defineProps<{
  items?: QualityGateInputItem[]
  overall?: QualityGateOverall
  loading?: boolean
}>(), {
  items: () => [],
  overall: 'UNKNOWN',
  loading: false
})

const items = computed<GateItem[]>(() =>
  props.items.map((item) => ({
    label: item.name,
    value: item.current,
    threshold: item.threshold,
    valueColor: item.passed ? '#00A63E' : '#FB2C36',
    icon: item.passed ? CheckCircle2 : AlertTriangle,
    iconColor: item.passed ? '#00C950' : '#FB2C36'
  }))
)

const resultText = computed(() => {
  if (props.loading) return '加载中...'
  if (props.overall === 'PASSED') return '全部通过'
  if (props.overall === 'PARTIAL_FAIL') return '部分未通过'
  if (props.overall === 'FAILED') return '未通过'
  return '暂无数据'
})

const resultBadgeClass = computed(() => {
  if (props.overall === 'PASSED') return 'bg-[#DCFCE7] text-[#166534]'
  if (props.overall === 'PARTIAL_FAIL') return 'bg-[#FEF9C2] text-[#A65F00]'
  if (props.overall === 'FAILED') return 'bg-[#FEE2E2] text-[#B91C1C]'
  return 'bg-[#F1F5F9] text-[#475569]'
})
</script>

<template>
  <section
    class="w-full max-w-[628.67px] rounded-[14px] bg-white border-[0.6667px] border-black/10 pt-[20.67px] pr-[20.67px] pb-[0.67px] pl-[20.67px]"
  >
    <div class="flex items-center gap-2">
      <Shield class="w-[15px] h-[15px] text-[#717182]" :stroke-width="1.25" />
      <div class="text-sm font-semibold leading-5 text-[#0A0A0A]">质量门禁状态</div>
    </div>

    <div class="mt-4 space-y-3">
      <div v-for="item in items" :key="item.label" class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <component
            :is="item.icon"
            class="w-[14px] h-[14px]"
            :style="{ color: item.iconColor }"
            :stroke-width="1.1666666"
          />
          <span class="text-xs font-normal leading-4 text-[#0A0A0A]">{{ item.label }}</span>
        </div>

        <div class="flex flex-col items-end text-right">
          <div class="text-xs font-medium leading-4" :style="{ color: item.valueColor }">{{ item.value }}</div>
          <div class="text-xs font-normal leading-4 text-[#717182]">{{ item.threshold }}</div>
        </div>
      </div>
      <div v-if="!items.length" class="text-xs font-normal leading-4 text-[#717182]">暂无门禁数据</div>
    </div>

    <div class="mt-[12.67px] pt-[12.67px] border-t-[0.6667px] border-black/10 flex items-center justify-between">
      <span class="text-xs font-normal leading-4 text-[#717182]">门禁结果</span>
      <span class="h-5 rounded-full px-2 flex items-center" :class="resultBadgeClass">
        <span class="text-xs font-medium leading-4">{{ resultText }}</span>
      </span>
    </div>
  </section>
</template>

