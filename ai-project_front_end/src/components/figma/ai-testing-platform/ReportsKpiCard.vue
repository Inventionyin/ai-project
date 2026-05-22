<script setup lang="ts">
defineProps<{
  label: string
  value: string
  delta: string
  deltaColor: string
  iconBgColor: string
  iconSrc: string
}>()
</script>

<template>
  <div class="h-[121.33px] w-full rounded-[14px] border border-black/10 bg-white px-[16.67px] pt-[16.67px] sm:w-[235.83px]">
    <div class="flex items-center justify-between">
      <div class="text-[12px] leading-[16px] text-[#717182]">{{ label }}</div>
      <div class="flex h-[28px] w-[28px] items-center justify-center rounded-[10px]" :style="{ backgroundColor: iconBgColor }">
        <img :src="iconSrc" alt="" class="h-[14px] w-[14px]" />
      </div>
    </div>

    <div class="mt-[12px] text-[20px] font-semibold leading-[28px] text-[#0A0A0A]">{{ value }}</div>
    <div class="mt-[4px] text-[12px] leading-[16px]" :style="{ color: deltaColor }">{{ delta }}</div>
  </div>
</template>
