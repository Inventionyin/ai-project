<script setup lang="ts">
export type BatchRunEnvironmentOption = {
  id: string
  name: string
  host?: string | null
}

const props = defineProps<{
  value: string
  options: BatchRunEnvironmentOption[]
}>()

const emit = defineEmits<{
  (e: 'update:value', value: string): void
}>()

function resolveDot(name: string) {
  const text = name.toLowerCase()
  if (text.includes('prod') || text.includes('生产')) return '#FF6467'
  return '#00C950'
}

function buttonClass(id: string) {
  if (id === props.value) return 'bg-[#EFF6FF] border-[#2B7FFF]'
  return 'bg-white border-black/10'
}

function labelClass(id: string) {
  if (id === props.value) return 'text-[#1447E6]'
  return 'text-[#0A0A0A]'
}
</script>

<template>
  <div class="w-full">
    <div class="text-[12px] font-semibold leading-[16px] text-[#0A0A0A]">执行环境 *</div>
    <div class="mt-[8px] w-full overflow-x-auto">
      <div class="flex w-[615.33px] items-center gap-[8px]">
        <button
          v-for="item in props.options"
          :key="item.id"
          type="button"
          class="flex h-[59px] w-[199.77px] flex-col gap-[4px] rounded-[14px] border-[2px] px-0 pb-[10px] pl-[10px] pt-[10px] text-left"
          :class="buttonClass(item.id)"
          @click="emit('update:value', item.id)"
        >
          <div class="flex items-center gap-[6px]">
            <span class="h-[6px] w-[6px] rounded-full" :style="{ background: resolveDot(item.name) }" />
            <span class="text-[12px] font-medium leading-[16px]" :class="labelClass(item.id)">
              {{ item.name }}
            </span>
          </div>
          <div class="text-[10px] font-medium leading-[15px] text-[#717182]" style="font-family: Consolas">
            {{ item.host || item.id.slice(0, 8) }}
          </div>
        </button>
      </div>
    </div>
  </div>
</template>
