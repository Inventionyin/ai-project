<script setup lang="ts">
import minusIcon from '@/assets/figma/ai-testing-platform/batch-run-concurrency-minus.svg'
import plusIcon from '@/assets/figma/ai-testing-platform/batch-run-concurrency-plus.svg'

const props = withDefaults(defineProps<{
  value: number
  min?: number
  max?: number
}>(), {
  min: 1,
  max: 100
})

const emit = defineEmits<{
  (e: 'update:value', value: number): void
}>()

function clamp(value: number) {
  const min = Number(props.min)
  const max = Number(props.max)
  const safeMin = Number.isFinite(min) ? min : 1
  const safeMax = Number.isFinite(max) ? max : 100
  return Math.max(safeMin, Math.min(safeMax, value))
}

function step(delta: number) {
  const next = clamp(Number(props.value) + delta)
  emit('update:value', next)
}

function onInput(e: Event) {
  const input = e.target as HTMLInputElement
  const parsed = Number(input.value)
  if (!Number.isFinite(parsed)) {
    emit('update:value', clamp(1))
    return
  }
  emit('update:value', clamp(parsed))
}
</script>

<template>
  <div class="w-full">
    <div class="text-[12px] font-semibold leading-[16px] text-[#0A0A0A]">并发数</div>
    <div class="mt-[8px] flex w-full items-center gap-[12px]">
      <button type="button" class="h-[32px] w-[32px] shrink-0" aria-label="Decrease concurrency" @click="step(-1)">
        <img :src="minusIcon" alt="" class="h-full w-full" />
      </button>

      <input
        class="h-[32px] w-[64px] shrink-0 rounded-[10px] border border-black/10 bg-white text-center text-[14px] font-semibold leading-[20px] text-[#0A0A0A] outline-none"
        inputmode="numeric"
        :min="props.min"
        :max="props.max"
        :value="props.value"
        type="number"
        @input="onInput"
      />

      <button type="button" class="h-[32px] w-[32px] shrink-0" aria-label="Increase concurrency" @click="step(1)">
        <img :src="plusIcon" alt="" class="h-full w-full" />
      </button>

      <div class="h-[16px] w-[108.67px] text-[12px] leading-[16px] text-[#717182]">个并发（上限 100）</div>
    </div>
  </div>
</template>
