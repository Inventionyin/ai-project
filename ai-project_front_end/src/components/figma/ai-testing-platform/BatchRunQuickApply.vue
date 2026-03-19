<script setup lang="ts">
import applyIcon from '@/assets/figma/ai-testing-platform/batch-run-apply-icon.svg'
import BatchRunSearchableSelect from '@/components/figma/ai-testing-platform/BatchRunSearchableSelect.vue'

defineProps<{
  apiName: string
  options: string[]
}>()

const emit = defineEmits<{
  (e: 'update:apiName', value: string): void
  (e: 'apply-all'): void
}>()
</script>

<template>
  <div class="w-full overflow-x-auto">
    <div
      class="flex h-[56px] w-[615.33px] items-center gap-[8px] rounded-[14px] border-[2px] border-dashed border-[#BEDBFF] bg-[rgba(239,246,255,0.6)] pl-[12px]"
    >
      <img :src="applyIcon" alt="" class="h-[13px] w-[13px]" />
      <div class="h-[16px] w-[72px] text-[12px] font-medium leading-[16px] text-[#1447E6]">一键应用接口</div>

      <BatchRunSearchableSelect
        :value="apiName"
        :options="options"
        :width="394.33"
        :height="28"
        @update:value="emit('update:apiName', $event)"
      />

      <button
        type="button"
        class="h-[28px] w-[84px] rounded-[10px] bg-[#155DFC] text-[12px] font-medium leading-[16px] text-white"
        @click="emit('apply-all')"
      >
        应用到全部
      </button>
    </div>
  </div>
</template>
