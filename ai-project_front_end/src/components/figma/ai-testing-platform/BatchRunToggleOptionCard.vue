<script setup lang="ts">
const props = defineProps<{
  icon: string
  title: string
  description: string
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

function toggle() {
  emit('update:modelValue', !props.modelValue)
}
</script>

<template>
  <div class="relative h-[59.33px] w-full rounded-[14px] border border-black/10 bg-white">
    <div class="absolute left-[12.67px] top-[12.67px] flex h-[34px] items-center gap-[8px]">
      <img :src="icon" alt="" class="h-[13px] w-[13px]" />
      <div class="flex flex-col gap-[2px]">
        <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">{{ title }}</div>
        <div class="text-[12px] leading-[16px] text-[#717182]">{{ description }}</div>
      </div>
    </div>

    <button type="button" class="absolute right-[12.67px] top-[19.67px] h-[20px] w-[36px] rounded-full" @click="toggle">
      <span
        class="absolute inset-0 rounded-full"
        :class="modelValue ? 'bg-[#155DFC]' : 'bg-black/10'"
      />
      <span
        class="absolute top-[2px] h-[16px] w-[16px] rounded-full bg-white shadow-[0px_1px_2px_-1px_rgba(0,0,0,0.1),0px_1px_3px_0px_rgba(0,0,0,0.1)] transition-all"
        :style="{ left: modelValue ? '18px' : '2px' }"
      />
    </button>
  </div>
</template>
