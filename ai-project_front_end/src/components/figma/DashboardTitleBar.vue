<script setup lang="ts">
import { RefreshCw } from 'lucide-vue-next'
</script>

<template>
  <section class="w-full max-w-[650.67px] flex flex-wrap items-center justify-between gap-4">
    <div class="min-w-0">
      <h1 class="text-[18px] font-semibold leading-[28px] text-[#0A0A0A]">仪表盘</h1>
      <p class="mt-0.5 text-sm font-normal leading-5 text-[#717182]">项目质量概览 · 2024-03-14</p>
    </div>

    <div class="flex w-full items-center justify-end gap-3 sm:w-auto">
      <button
        class="h-8 w-[72.33px] rounded-[10px] border-[0.6667px] border-black/10 bg-white flex items-center justify-center gap-1.5"
      >
        <RefreshCw class="w-[13px] h-[13px] text-[#717182]" />
        <span class="text-sm font-medium leading-5 text-[#717182]">刷新</span>
      </button>
    </div>
  </section>
</template>

