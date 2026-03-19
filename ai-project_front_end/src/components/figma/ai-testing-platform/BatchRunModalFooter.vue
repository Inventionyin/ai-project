<script setup lang="ts">
import nextArrow from '@/assets/figma/ai-testing-platform/batch-run-next-arrow.svg'
import executeIcon from '@/assets/figma/ai-testing-platform/batch-run-execute-icon.svg'

const props = withDefaults(defineProps<{
  step?: 1 | 2 | 3
  executeCount?: number
}>(), {
  step: 1,
  executeCount: 0
})

const emit = defineEmits<{
  (e: 'cancel'): void
  (e: 'next'): void
  (e: 'prev'): void
  (e: 'execute'): void
}>()
</script>

<template>
  <div class="flex h-[68.67px] w-full items-center justify-between border-t border-black/10 pl-[20px] pr-[20px]">
    <button
      type="button"
      class="h-[36px] w-[61.33px] rounded-[10px] border border-black/10 text-[14px] font-medium leading-[20px] text-[#0A0A0A]"
      @click="emit('cancel')"
    >
      取消
    </button>

    <div v-if="props.step === 3" class="flex h-[36px] w-[220.98px] items-center gap-[8px]">
      <button
        type="button"
        class="h-[36px] w-[93.48px] rounded-[10px] border border-black/10 text-[14px] font-medium leading-[20px] text-[#717182]"
        @click="emit('prev')"
      >
        ← 上一步
      </button>
      <button type="button" class="relative h-[36px] w-[119.5px] rounded-[10px] bg-[#00A63E]" @click="emit('execute')">
        <img :src="executeIcon" alt="" class="absolute left-[20px] top-[11.5px] h-[13px] w-[13px]" />
        <span class="absolute left-[41px] top-[8.33px] text-[14px] font-medium leading-[20px] text-white">
          执行 {{ Math.max(0, props.executeCount) }} 条
        </span>
      </button>
    </div>

    <button v-else type="button" class="relative h-[36px] w-[102px] rounded-[10px] bg-[#155DFC]" @click="emit('next')">
      <span class="absolute left-[20px] top-[8.33px] text-[14px] font-medium leading-[20px] text-white">下一步 </span>
      <img :src="nextArrow" alt="" class="absolute left-[68px] top-[11px] h-[14px] w-[14px]" />
    </button>
  </div>
</template>
