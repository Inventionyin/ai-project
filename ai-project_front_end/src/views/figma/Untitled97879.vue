<script setup lang="ts">
import AiTestingPlatformShell from '@/components/figma/ai-testing-platform/AiTestingPlatformShell.vue'
import DataSetsPanel from '@/components/figma/ai-testing-platform/DataSetsPanel.vue'
</script>

<template>
  <AiTestingPlatformShell active-asset-child="测试数据">
    <DataSetsPanel />
  </AiTestingPlatformShell>
</template>
