<script setup lang="ts">
import AiTestingPlatformShell from '@/components/figma/ai-testing-platform/AiTestingPlatformShell.vue'
import SuiteDetailPanel from '@/components/figma/ai-testing-platform/SuiteDetailPanel.vue'
</script>

<template>
  <AiTestingPlatformShell active-asset-child="测试套件">
    <SuiteDetailPanel />
  </AiTestingPlatformShell>
</template>
