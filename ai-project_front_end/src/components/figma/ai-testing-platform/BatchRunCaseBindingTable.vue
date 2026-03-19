<script setup lang="ts">
import BatchRunSearchableSelect from '@/components/figma/ai-testing-platform/BatchRunSearchableSelect.vue'

export type BatchRunCaseRow = {
  id: string
  title: string
  bindingId: string
  method: 'POST'
  priority: 'P0' | 'P1'
}

const props = withDefaults(defineProps<{
  rows?: BatchRunCaseRow[]
  optionsByCaseId?: Record<string, Array<{ value: string; label: string }>>
}>(), {
  optionsByCaseId: () => ({}),
  rows: () => ([
    { id: '1', title: '创建订单-正常流程', bindingId: '', method: 'POST', priority: 'P0' },
    { id: '2', title: '创建订单-余额不足', bindingId: '', method: 'POST', priority: 'P1' },
    { id: '3', title: '支付-微信支付回调验签', bindingId: '', method: 'POST', priority: 'P0' },
    { id: '4', title: '查询订单列表-分页正确性', bindingId: '', method: 'POST', priority: 'P0' }
  ])
})

const emit = defineEmits<{
  (e: 'update-row-binding', payload: { id: string; bindingId: string }): void
}>()

const priorityStyle = (priority: BatchRunCaseRow['priority']) => {
  if (priority === 'P0') {
    return { bg: '#FFE2E2', text: '#C10007' }
  }
  return { bg: '#FFEDD4', text: '#CA3500' }
}
</script>

<template>
  <div class="h-full w-full max-w-[615.33px] overflow-x-auto rounded-[14px] border border-black/10 bg-white p-[0.67px]">
    <div class="flex h-full min-w-[597.33px] flex-col">
      <div class="relative h-[32.67px] w-[597.33px] border-b border-black/10 bg-[rgba(236,236,240,0.3)]">
        <div class="absolute left-[12px] top-[8px] text-[12px] font-medium leading-[16px] text-[#717182]">用例</div>
        <div class="absolute left-[217.33px] top-[8px] text-[12px] font-medium leading-[16px] text-[#717182]">绑定配置 *</div>
        <div class="absolute left-[445.33px] top-[8px] text-[12px] font-medium leading-[16px] text-[#717182]">类型</div>
        <div class="absolute left-[533.33px] top-[8px] text-[12px] font-medium leading-[16px] text-[#717182]">优先级</div>
      </div>

      <div class="min-h-0 flex-1 overflow-y-auto">
        <div
          v-for="row in props.rows"
          :key="row.id"
          class="relative h-[52.67px] w-[597.33px] border-b border-black/10 bg-white last:border-b-0"
        >
          <div class="absolute left-[12px] top-[17.75px] w-[197.33px] text-[12px] font-medium leading-[16.5px] text-[#0A0A0A]">
            {{ row.title }}
          </div>

          <div class="absolute left-[217.33px] top-[12px]">
            <BatchRunSearchableSelect
              :value="row.bindingId"
              :options="props.optionsByCaseId[row.id] || []"
              :width="220"
              :height="28"
              @update:value="emit('update-row-binding', { id: row.id, bindingId: $event })"
            />
          </div>

          <div class="absolute left-[445.33px] top-[20px] flex h-[16.67px] w-[39.03px] items-center justify-center rounded-[4px] bg-[#DBEAFE] px-[6px] py-[2px]">
            <span class="text-[10px] font-bold leading-[15px] text-[#1447E6]">{{ row.method }}</span>
          </div>

          <div
            class="absolute left-[533.33px] top-[20px] flex h-[16.67px] w-[23.99px] items-center justify-center rounded-full px-[6px] py-[2px]"
            :style="{ backgroundColor: priorityStyle(row.priority).bg }"
          >
            <span class="text-[10px] font-medium leading-[15px]" :style="{ color: priorityStyle(row.priority).text }">
              {{ row.priority }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
