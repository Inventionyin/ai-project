<script setup lang="ts">
const rows = [
  {
    label: '接口测试(API)',
    percent: '92%',
    percentColor: '#D08700',
    passWidth: 226.63,
    failWidth: 19.7
  },
  {
    label: '冒烟套件',
    percent: '100%',
    percentColor: '#00A63E',
    passWidth: 246.33,
    failWidth: 0
  },
  {
    label: '回归套件',
    percent: '87%',
    percentColor: '#D08700',
    passWidth: 214.3,
    failWidth: 32.02
  },
  {
    label: 'P0 用例',
    percent: '95%',
    percentColor: '#00A63E',
    passWidth: 234.01,
    failWidth: 12.31
  },
  {
    label: 'P1 用例',
    percent: '88%',
    percentColor: '#D08700',
    passWidth: 216.77,
    failWidth: 29.55
  }
] as const
</script>

<template>
  <section
    class="w-full rounded-[14px] border border-black/10 bg-white px-[20.67px] pt-[20.67px] pb-[0.67px] md:h-[237.33px]"
  >
    <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">按维度分析</div>

    <div class="mt-[16px] flex flex-col gap-[12px]">
      <div v-for="row in rows" :key="row.label" class="flex items-center gap-[12px]">
        <div class="w-[128px] text-[12px] leading-[16px] text-[#717182]">{{ row.label }}</div>

        <div class="relative h-[8px] w-[246.33px] overflow-hidden rounded-full bg-[#ECECF0]">
          <div class="absolute left-0 top-0 h-full bg-[#00C950]" :style="{ width: `${row.passWidth}px` }" />
          <div
            class="absolute top-0 h-full bg-[#FF6467]"
            :style="{ left: `${row.passWidth}px`, width: `${row.failWidth}px` }"
          />
        </div>

        <div class="w-[48px] text-right text-[12px] font-medium leading-[16px]" :style="{ color: row.percentColor }">
          {{ row.percent }}
        </div>
      </div>
    </div>
  </section>
</template>
