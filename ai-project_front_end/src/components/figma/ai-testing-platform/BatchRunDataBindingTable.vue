<script setup lang="ts">
export type BatchRunDataBindingRow = {
  id: string
  title: string
  priority: 'P0' | 'P1'
  overrideParamsText?: string
}

const props = defineProps<{
  rows: BatchRunDataBindingRow[]
  errorsById?: Record<string, string>
}>()

const emit = defineEmits<{
  (e: 'update-row-override', payload: { id: string; overrideParamsText: string }): void
}>()

const priorityStyle = (priority: BatchRunDataBindingRow['priority']) => {
  if (priority === 'P0') {
    return { bg: '#FFE2E2', text: '#C10007' }
  }
  return { bg: '#FFEDD4', text: '#CA3500' }
}
</script>

<template>
  <div class="w-full max-w-[615.33px] overflow-x-auto">
    <div class="min-w-[597.33px] rounded-[14px] border border-black/10 bg-white p-[0.67px]">
      <div class="relative h-[32.67px] w-[597.33px] border-b border-black/10 bg-[rgba(236,236,240,0.3)]">
        <div class="absolute left-[12px] top-[8px] text-[12px] font-medium leading-[16px] text-[#717182]">用例</div>
        <div class="absolute left-[250px] top-[8px] text-[12px] font-medium leading-[16px] text-[#717182]">参数覆盖（JSON，可选）</div>
        <div class="absolute left-[550px] top-[8px] text-[12px] font-medium leading-[16px] text-[#717182]">优先级</div>
      </div>

      <div class="max-h-[320px] overflow-y-auto">
        <div
          v-for="row in rows"
          :key="row.id"
          class="relative h-[52.67px] w-[597.33px] border-b border-black/10 bg-white last:border-b-0"
        >
          <div class="absolute left-[12px] top-[17.75px] w-[197.33px] text-[12px] font-medium leading-[16.5px] text-[#0A0A0A]">
            {{ row.title }}
          </div>

          <div class="absolute left-[217.33px] top-[12px] w-[300px]">
            <input
              :value="row.overrideParamsText || ''"
              class="h-[28px] w-full rounded-[10px] border px-[10px] text-[11px] leading-[16.5px] outline-none"
              :class="props.errorsById?.[row.id] ? 'border-[#FB2C36] bg-white text-[#0A0A0A]' : 'border-black/10 bg-white text-[#0A0A0A]'"
              style="font-family: Consolas"
              type="text"
              placeholder='例如：{"key":"value"}'
              @input="emit('update-row-override', { id: row.id, overrideParamsText: ($event.target as HTMLInputElement).value })"
            />
          </div>

          <div
            class="absolute left-[533.33px] top-[20px] inline-flex h-[16.67px] items-center rounded-full px-[6px]"
            :style="{ background: priorityStyle(row.priority).bg }"
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
