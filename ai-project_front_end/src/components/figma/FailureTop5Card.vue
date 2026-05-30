<script setup lang="ts">
import { computed } from 'vue'
import { ArrowRight, TrendingDown } from 'lucide-vue-next'

type FailItem = {
  id: string
  name: string
  failCount: number
  suiteNames: string[]
}

const emit = defineEmits<{
  'open-report': []
}>()

const props = withDefaults(defineProps<{
  items?: FailItem[]
  loading?: boolean
}>(), {
  items: () => [],
  loading: false
})

const normalizedItems = computed(() => props.items.slice(0, 5))
const maxCount = computed(() => {
  const counts = normalizedItems.value.map((item) => item.failCount)
  return counts.length ? Math.max(...counts) : 1
})
const barWidth = (count: number) => `${Math.max(8, Math.round((count / maxCount.value) * 60))}px`
</script>

<template>
  <section
    class="w-full max-w-[628.67px] rounded-[14px] bg-white border-[0.6667px] border-black/10 pt-[20.67px] pr-[20.67px] pb-[0.67px] pl-[20.67px]"
  >
    <div class="flex items-center justify-between gap-4">
      <div class="flex items-center gap-2">
        <TrendingDown class="w-[15px] h-[15px] text-[#FB2C36]" :stroke-width="1.25" />
        <div class="text-sm font-semibold leading-5 text-[#0A0A0A]">失败 Top 5</div>
      </div>

      <button
        type="button"
        class="h-4 w-16 flex items-center justify-center gap-1"
        aria-label="查看报告"
        @click="emit('open-report')"
      >
        <span class="text-xs font-medium leading-4 text-brand-blue">查看报告</span>
        <ArrowRight class="w-3 h-3 text-brand-blue" />
      </button>
    </div>

    <div v-if="props.loading" class="mt-4 h-32 flex items-center justify-center text-xs text-[#717182]">
      加载中...
    </div>

    <div v-else-if="normalizedItems.length === 0" class="mt-4 h-32 flex items-center justify-center text-xs text-[#717182]">
      暂无失败数据
    </div>

    <div v-else class="mt-4 space-y-2">
      <div
        v-for="(item, idx) in normalizedItems"
        :key="item.id"
        class="h-8 w-full flex items-center"
      >
        <div class="w-4 text-right text-xs font-normal leading-4 text-[#717182]">{{ idx + 1 }}</div>

        <div class="ml-3 flex-1 min-w-0 h-8 flex flex-col justify-center">
          <div class="truncate text-xs font-normal leading-4 text-[#0A0A0A]">{{ item.name }}</div>
          <div class="truncate text-xs font-normal leading-4 text-[#717182]">{{ item.suiteNames.join(' / ') || '-' }}</div>
        </div>

        <div class="ml-3 w-[60px] h-6 relative rounded bg-[#ECECF0] overflow-hidden">
          <div
            class="absolute left-0 top-1/2 -translate-y-1/2 h-[14px] bg-[#F87171]"
            :style="{ width: barWidth(item.failCount) }"
          ></div>
        </div>

        <div class="ml-3 w-12 text-right text-xs font-medium leading-4 text-[#FB2C36]">{{ item.failCount }} 次</div>
      </div>
    </div>
  </section>
</template>

