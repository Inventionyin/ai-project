<script setup lang="ts">
import { Activity, CheckCircle, Clock, XCircle } from 'lucide-vue-next'

type StatItem = {
  label: string
  value: string
  subLabel: string
  icon: any
  iconBg: string
  iconColor: string
}

const items: StatItem[] = [
  {
    label: '今日执行',
    value: '3',
    subLabel: '次运行',
    icon: Activity,
    iconBg: '#EFF6FF',
    iconColor: '#155DFC'
  },
  {
    label: '通过',
    value: '1',
    subLabel: '通过率 33%',
    icon: CheckCircle,
    iconBg: '#F0FDF4',
    iconColor: '#00A63E'
  },
  {
    label: '失败',
    value: '1',
    subLabel: '需要关注',
    icon: XCircle,
    iconBg: '#FEF2F2',
    iconColor: '#FB2C36'
  },
  {
    label: '进行中',
    value: '1',
    subLabel: '实时更新',
    icon: Clock,
    iconBg: '#FFF7ED',
    iconColor: '#D08700'
  }
]
</script>

<template>
  <section class="w-full max-w-[650.67px] grid grid-cols-2 sm:grid-cols-4 gap-4">
    <div
      v-for="item in items"
      :key="item.label"
      class="w-full sm:w-[150.67px] h-[129.33px] rounded-[14px] bg-white border-[0.6667px] border-black/10"
    >
      <div class="h-full w-full px-[16.67px] pt-[16.67px] pb-[16px] flex flex-col">
        <div class="flex items-center justify-between">
          <div class="text-sm font-normal leading-5 text-[#717182]">{{ item.label }}</div>
          <div class="w-8 h-8 rounded-[10px] flex items-center justify-center" :style="{ background: item.iconBg }">
            <component :is="item.icon" class="w-4 h-4" :style="{ color: item.iconColor }" />
          </div>
        </div>

        <div class="mt-[12.67px] flex items-end gap-2">
          <div class="text-2xl font-semibold leading-8 text-[#0A0A0A]">{{ item.value }}</div>
          <div class="pb-[1px] text-xs font-normal leading-4 text-[#717182]">{{ item.subLabel }}</div>
        </div>
      </div>
    </div>
  </section>
</template>

