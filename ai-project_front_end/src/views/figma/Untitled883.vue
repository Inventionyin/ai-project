<script setup lang="ts">
import AiTestingPlatformShell from '@/components/figma/ai-testing-platform/AiTestingPlatformShell.vue'
import ApiCollectionsPanel from '@/components/figma/ai-testing-platform/ApiCollectionsPanel.vue'
</script>

<template>
  <AiTestingPlatformShell active-asset-child="接口集合">
    <ApiCollectionsPanel />
  </AiTestingPlatformShell>
</template>
