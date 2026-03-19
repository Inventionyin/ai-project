<script setup lang="ts">
import headerIcon from '@/assets/figma/ai-testing-platform/batch-run-header-icon.svg'
import modalClose from '@/assets/figma/ai-testing-platform/batch-run-modal-close.svg'

const props = withDefaults(defineProps<{
  selectedCount: number
  boundCount?: number
}>(), {
  boundCount: undefined
})

const emit = defineEmits<{
  (e: 'close'): void
}>()

const resolvedBoundCount = () => {
  if (typeof props.boundCount === 'number') return Math.max(0, props.boundCount)
  return props.selectedCount
}
</script>

<template>
  <div class="flex h-[74.67px] w-full items-center justify-between border-b border-black/10 pl-[20px] pr-[20px]">
    <div class="flex items-center gap-[10px]">
      <img :src="headerIcon" alt="" class="h-[28px] w-[28px]" />
      <div class="flex flex-col gap-[2px]">
        <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">批量运行</div>
        <div class="text-[12px] leading-[16px] text-[#717182]">
          已选 {{ selectedCount }} 条 · {{ resolvedBoundCount() }}/{{ selectedCount }} 已选择绑定
        </div>
      </div>
    </div>

    <button
      type="button"
      class="h-[27px] w-[27px] rounded-[10px] px-[6px] pt-[6px] pb-0"
      @click="emit('close')"
    >
      <img :src="modalClose" alt="" class="h-[15px] w-[15px]" />
    </button>
  </div>
</template>
