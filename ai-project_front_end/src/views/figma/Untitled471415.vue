<script setup lang="ts">
import AiTestingPlatformShell from '@/components/figma/ai-testing-platform/AiTestingPlatformShell.vue'
import SuitesPanel from '@/components/figma/ai-testing-platform/SuitesPanel.vue'
</script>

<template>
  <AiTestingPlatformShell active-asset-child="测试套件">
    <SuitesPanel />
  </AiTestingPlatformShell>
</template>
