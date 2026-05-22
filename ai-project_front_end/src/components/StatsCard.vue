<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  iconBgColor?: string
}>()
</script>

<template>
  <div class="flex flex-col items-start gap-3 p-5 bg-white border border-gray-100 rounded-[14px] shadow-sm hover:shadow-md transition-shadow h-full">
    <!-- Icon Container -->
    <div 
      class="flex items-center justify-center w-10 h-10 rounded-[10px]"
      :class="iconBgColor || 'bg-blue-50'"
    >
      <slot name="icon">
        <!-- Default Icon if none provided -->
        <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      </slot>
    </div>

    <!-- Content -->
    <div class="flex flex-col gap-1">
      <span class="text-2xl font-bold text-gray-900 leading-none">{{ value }}</span>
      <span class="text-sm text-gray-500 font-medium">{{ label }}</span>
    </div>
  </div>
</template>
