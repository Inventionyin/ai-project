<script setup lang="ts">
import ApiCollectionsList from '@/components/figma/ai-testing-platform/ApiCollectionsList.vue'
import ApiRequestConfigPanel from '@/components/figma/ai-testing-platform/ApiRequestConfigPanel.vue'
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)]">
    <div class="flex flex-col gap-[16px] p-[16px] md:min-h-[calc(100vh-48px)] md:flex-row md:gap-0 md:p-0">
      <ApiCollectionsList />
      <ApiRequestConfigPanel />
    </div>
  </div>
</template>
