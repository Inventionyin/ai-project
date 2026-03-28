<script setup lang="ts">
import BatchRunStepIndicator from '@/components/figma/ai-testing-platform/BatchRunStepIndicator.vue'
import BatchRunEnvironmentSelect, { type BatchRunEnvironmentOption } from '@/components/figma/ai-testing-platform/BatchRunEnvironmentSelect.vue'
import BatchRunConcurrencyInput from '@/components/figma/ai-testing-platform/BatchRunConcurrencyInput.vue'
import BatchRunToggleOptionCard from '@/components/figma/ai-testing-platform/BatchRunToggleOptionCard.vue'
import BatchRunRequestPreview from '@/components/figma/ai-testing-platform/BatchRunRequestPreview.vue'
import stopIcon from '@/assets/figma/ai-testing-platform/batch-run-stop-on-failure-icon.svg'
import notifyIcon from '@/assets/figma/ai-testing-platform/batch-run-notify-on-fail-icon.svg'

defineProps<{
  envId: string
  environments: BatchRunEnvironmentOption[]
  concurrency: number
  stopOnFailure: boolean
  notifyOnFail: boolean
  idempotencyKey: string
}>()

const emit = defineEmits<{
  (e: 'update:envId', value: string): void
  (e: 'update:concurrency', value: number): void
  (e: 'update:stopOnFailure', value: boolean): void
  (e: 'update:notifyOnFail', value: boolean): void
}>()
</script>

<template>
  <div class="flex w-full flex-col gap-[20px]">
    <BatchRunStepIndicator :active-step="3" />

    <div class="flex w-full flex-col gap-[16px]">
      <BatchRunEnvironmentSelect :value="envId" :options="environments" @update:value="emit('update:envId', $event)" />

      <BatchRunConcurrencyInput :value="concurrency" :min="1" :max="100" @update:value="emit('update:concurrency', $event)" />

      <div class="flex w-full flex-col gap-[8px]">
        <BatchRunToggleOptionCard
          :icon="stopIcon"
          title="失败即停（stopOnFailure）"
          description="首条用例失败后立即终止剩余执行"
          :model-value="stopOnFailure"
          @update:model-value="emit('update:stopOnFailure', $event)"
        />
        <BatchRunToggleOptionCard
          :icon="notifyIcon"
          title="失败时通知"
          description="执行出现失败用例时发送通知"
          :model-value="notifyOnFail"
          @update:model-value="emit('update:notifyOnFail', $event)"
        />
      </div>

      <BatchRunRequestPreview
        :concurrency="concurrency"
        :stop-on-failure="stopOnFailure"
        :idempotency-key="idempotencyKey"
      />
    </div>
  </div>
</template>
