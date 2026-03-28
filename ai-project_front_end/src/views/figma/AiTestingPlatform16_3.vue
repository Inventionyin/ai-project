<script setup lang="ts">
import AiTestingPlatformShell from '@/components/figma/ai-testing-platform/AiTestingPlatformShell.vue'
import TestCaseDetailPanel from '@/components/figma/ai-testing-platform/TestCaseDetailPanel.vue'
</script>

<template>
  <AiTestingPlatformShell active-asset-child="用例管理">
    <TestCaseDetailPanel />
  </AiTestingPlatformShell>
</template>
