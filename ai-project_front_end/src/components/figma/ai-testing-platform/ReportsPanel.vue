<script setup lang="ts">
import { ref } from 'vue'
import ReportsToolbar from '@/components/figma/ai-testing-platform/ReportsToolbar.vue'
import ReportsViewTabs, { type ReportsViewTab } from '@/components/figma/ai-testing-platform/ReportsViewTabs.vue'
import ReportsKpiStrip from '@/components/figma/ai-testing-platform/ReportsKpiStrip.vue'
import ReportsTrendCard from '@/components/figma/ai-testing-platform/ReportsTrendCard.vue'
import ReportsFailureTop5Card from '@/components/figma/ai-testing-platform/ReportsFailureTop5Card.vue'
import ReportsDimensionAnalysisCard from '@/components/figma/ai-testing-platform/ReportsDimensionAnalysisCard.vue'
import ReportsSingleControls from '@/components/figma/ai-testing-platform/ReportsSingleControls.vue'
import ReportsSingleReportCard from '@/components/figma/ai-testing-platform/ReportsSingleReportCard.vue'

const activeView = ref<ReportsViewTab>('single')
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)] md:pr-[16.67px]">
    <div class="flex flex-col gap-[16px] px-[16px] pt-[16px] md:px-[24px] md:pt-[24px]">
      <ReportsToolbar />
      <ReportsViewTabs v-model="activeView" />

      <div v-if="activeView === 'trend'" class="flex flex-col gap-[16px]">
        <ReportsKpiStrip />
        <ReportsTrendCard />

        <div class="flex flex-col gap-[16px] md:flex-row">
          <ReportsFailureTop5Card class="md:w-[487.67px]" />
          <ReportsDimensionAnalysisCard class="md:w-[487.67px]" />
        </div>
      </div>

      <div v-else-if="activeView === 'single'" class="flex flex-col gap-[16px]">
        <ReportsSingleControls />
        <ReportsSingleReportCard />
      </div>
    </div>
  </div>
</template>
