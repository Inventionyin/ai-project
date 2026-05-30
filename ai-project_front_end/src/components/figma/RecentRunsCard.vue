<script setup lang="ts">
import { LoaderCircle, List, ArrowRight } from 'lucide-vue-next'

type RunStatus = '通过' | '失败' | '执行中' | '排队中' | '已取消'

type RunItem = {
  id: string
  status: RunStatus
  title: string
  envTime: string
  right: { type: 'text'; value: string; color: string } | { type: 'spinner' }
}

const emit = defineEmits<{
  'open-all-runs': []
}>()

const statusStyle: Record<RunStatus, { bg: string; text: string; width: string }> = {
  通过: { bg: '#DCFCE7', text: '#008236', width: '40px' },
  失败: { bg: '#FFE2E2', text: '#E7000B', width: '40px' },
  执行中: { bg: '#DBEAFE', text: '#155DFC', width: '52px' },
  排队中: { bg: '#FEF3C7', text: '#B45309', width: '52px' },
  已取消: { bg: '#F3F4F6', text: '#4A5565', width: '52px' }
}

const props = withDefaults(defineProps<{
  items?: RunItem[]
  loading?: boolean
}>(), {
  items: () => [],
  loading: false
})
</script>

<template>
  <section
    class="w-full max-w-[628.67px] rounded-[14px] bg-white border-[0.6667px] border-black/10 pt-[20.67px] pr-[20.67px] pb-[0.67px] pl-[20.67px]"
  >
    <div class="flex items-center justify-between gap-4">
      <div class="flex items-center gap-2">
        <List class="w-[15px] h-[15px] text-[#717182]" :stroke-width="1.25" />
        <div class="text-sm font-semibold leading-5 text-[#0A0A0A]">最近运行</div>
      </div>

      <button
        type="button"
        class="h-4 w-16 flex items-center justify-center gap-1"
        aria-label="全部记录"
        @click="emit('open-all-runs')"
      >
        <span class="text-xs font-medium leading-4 text-brand-blue">全部记录</span>
        <ArrowRight class="w-3 h-3 text-brand-blue" :stroke-width="1" />
      </button>
    </div>

    <div v-if="props.loading" class="mt-4 h-32 flex items-center justify-center text-xs text-[#717182]">
      加载中...
    </div>

    <div v-else-if="props.items.length === 0" class="mt-4 h-32 flex items-center justify-center text-xs text-[#717182]">
      暂无运行记录
    </div>

    <div v-else class="mt-4 space-y-2">
      <div
        v-for="item in props.items"
        :key="item.id"
        class="h-8 w-full flex items-center gap-3 px-2 rounded-[10px]"
      >
        <span
          class="h-5 rounded-full px-2 flex items-center text-xs font-medium leading-4"
          :style="{ background: statusStyle[item.status].bg, color: statusStyle[item.status].text, width: statusStyle[item.status].width }"
        >
          {{ item.status }}
        </span>

        <div class="flex-1 min-w-0 flex flex-col">
          <div class="truncate text-xs font-normal leading-4 text-[#0A0A0A]">{{ item.title }}</div>
          <div class="truncate text-xs font-normal leading-4 text-[#717182]">{{ item.envTime }}</div>
        </div>

        <div class="w-[34.68px] h-4 flex items-center justify-end">
          <template v-if="item.right.type === 'spinner'">
            <LoaderCircle class="w-[13.72px] h-[13.72px] animate-spin" style="color:#2B7FFF" :stroke-width="1.0833334" />
          </template>
          <template v-else>
            <span class="text-xs font-medium leading-4" :style="{ color: item.right.color }">{{ item.right.value }}</span>
          </template>
        </div>
      </div>
    </div>
  </section>
</template>

