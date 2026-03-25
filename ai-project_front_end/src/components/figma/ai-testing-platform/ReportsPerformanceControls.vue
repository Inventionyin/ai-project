<script setup lang="ts">
import chevronDownSmall from '@/assets/figma/ai-testing-platform/chevron-down-small.svg'
import reportsSingleDetail from '@/assets/figma/ai-testing-platform/reports-single-detail.svg'
import type { PerformanceReportListItem } from '@/lib/aiTestingPlatformApi'

const modelValue = defineModel<string>({ required: true })

defineProps<{
  items: PerformanceReportListItem[]
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'refresh'): void
}>()
</script>

<template>
  <div class="flex flex-wrap items-center gap-[12px]">
    <div class="relative h-[32px] w-full max-w-[360px]">
      <select
        v-model="modelValue"
        class="h-full w-full appearance-none rounded-[10px] border border-black/10 bg-white px-[12px] pr-[36px] text-[14px] leading-[20px] text-[#717182] outline-none"
      >
        <option v-for="item in items" :key="item.id" :value="item.id">
          {{ item.name }} · {{ new Date(item.createdAt * 1000).toLocaleString() }}
        </option>
      </select>
      <img :src="chevronDownSmall" alt="" class="pointer-events-none absolute right-[12px] top-1/2 h-[13px] w-[13px] -translate-y-1/2" />
    </div>

    <button
      type="button"
      class="flex h-[32px] items-center gap-[6px] rounded-[10px] border border-black/10 bg-white px-[12px]"
      :disabled="loading"
      @click="emit('refresh')"
    >
      <img :src="reportsSingleDetail" alt="" class="h-[13px] w-[13px]" />
      <span class="text-[14px] font-medium leading-[20px] text-[#717182]">{{ loading ? '加载中...' : '刷新数据' }}</span>
    </button>
  </div>
</template>
