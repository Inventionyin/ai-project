<script setup lang="ts">
const stats = [
  { value: '86', label: '总用例', color: '#0A0A0A' },
  { value: '75', label: '通过', color: '#00A63E' },
  { value: '11', label: '失败', color: '#FB2C36' },
  { value: '0', label: '跳过', color: '#717182' },
  { value: '87.2%', label: '通过率', color: '#D08700' }
] as const
</script>

<template>
  <div class="flex flex-wrap gap-[12px]">
    <div
      v-for="item in stats"
      :key="item.label"
      class="flex w-[148px] flex-col gap-[4px] rounded-[10px] bg-[rgba(236,236,240,0.3)] px-[16px] py-[12px]"
    >
      <div class="text-[20px] font-semibold leading-[28px]" :style="{ color: item.color }">
        {{ item.value }}
      </div>
      <div class="text-[12px] leading-[16px] text-[#717182]">{{ item.label }}</div>
    </div>
  </div>
</template>
