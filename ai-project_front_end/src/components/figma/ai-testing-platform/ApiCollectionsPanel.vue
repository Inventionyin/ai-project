<script setup lang="ts">
import { ref } from 'vue'
import ApiCollectionsList from '@/components/figma/ai-testing-platform/ApiCollectionsList.vue'
import ApiRequestConfigPanel from '@/components/figma/ai-testing-platform/ApiRequestConfigPanel.vue'

const selectedCollectionId = ref('')
const selectedRequestId = ref('')

function onSelectEndpoint(collectionId: string, requestId: string) {
  selectedCollectionId.value = collectionId
  selectedRequestId.value = requestId
}
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)]">
    <div class="flex flex-col gap-[16px] p-[16px] md:min-h-[calc(100vh-48px)] md:flex-row md:gap-0 md:p-0">
      <ApiCollectionsList @select-endpoint="onSelectEndpoint" />
      <ApiRequestConfigPanel
        :collection-id="selectedCollectionId"
        :request-id="selectedRequestId"
      />
    </div>
  </div>
</template>
