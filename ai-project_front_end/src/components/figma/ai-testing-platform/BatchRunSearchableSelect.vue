<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import selectChevron from '@/assets/figma/ai-testing-platform/batch-run-select-chevron.svg'
import selectClear from '@/assets/figma/ai-testing-platform/batch-run-select-clear.svg'

type SelectOption = string | { value: string; label: string }

const props = withDefaults(defineProps<{
  value: string
  options?: SelectOption[]
  width: number
  height?: number
}>(), {
  options: () => ['订单中心 API', '支付中心 API', '用户中心 API', '库存中心 API'],
  height: 28
})

const emit = defineEmits<{
  (e: 'update:value', value: string): void
}>()

const rootRef = ref<HTMLElement | null>(null)
const isOpen = ref(false)

const resolvedOptions = computed(() => {
  const list = Array.isArray(props.options) ? props.options : []
  return list
    .map((item) => {
      if (typeof item === 'string') {
        const v = item.trim()
        return v ? { value: v, label: v } : null
      }
      const value = String(item?.value || '').trim()
      const label = String(item?.label || '').trim()
      if (!value || !label) return null
      return { value, label }
    })
    .filter(Boolean) as Array<{ value: string; label: string }>
})

const labelByValue = computed(() => resolvedOptions.value.reduce<Record<string, string>>((acc, item) => {
  acc[item.value] = item.label
  return acc
}, {}))

const displayValue = computed(() => {
  const value = String(props.value || '').trim()
  if (!value) return ''
  return labelByValue.value[value] || value
})

function toggleOpen() {
  isOpen.value = !isOpen.value
}

function close() {
  isOpen.value = false
}

function clearValue() {
  emit('update:value', '')
  close()
}

function selectValue(next: string) {
  emit('update:value', next)
  close()
}

function onWindowClick(e: MouseEvent) {
  if (!isOpen.value) return
  const target = e.target as Node | null
  if (!target) return
  if (rootRef.value?.contains(target)) return
  close()
}

onMounted(() => {
  window.addEventListener('click', onWindowClick)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', onWindowClick)
})
</script>

<template>
  <div
    ref="rootRef"
    class="relative rounded-[10px] border border-[#8EC5FF] bg-[#EFF6FF]"
    :style="{ width: `${width}px`, height: `${height}px` }"
  >
    <button
      type="button"
      class="absolute inset-y-0 left-0 right-[28px] rounded-[10px] text-left"
      @click="toggleOpen"
    >
      <div class="absolute left-[10.67px] top-[5.75px] text-[11px] font-medium leading-[16.5px] text-[#1447E6]">
        {{ displayValue }}
      </div>
      <img :src="selectChevron" alt="" class="absolute right-[10.67px] top-[9px] h-[10px] w-[10px]" />
    </button>

    <button
      type="button"
      class="absolute inset-y-0 right-0 w-[28px] rounded-[10px]"
      @click="clearValue"
    >
      <img :src="selectClear" alt="" class="absolute right-[10.67px] top-[9px] h-[10px] w-[10px]" />
    </button>

    <div
      v-if="isOpen"
      class="absolute left-0 top-full z-20 mt-[6px] overflow-hidden rounded-[10px] border border-black/10 bg-white shadow-[0px_10px_15px_-3px_rgba(0,0,0,0.1),0px_4px_6px_-4px_rgba(0,0,0,0.1)]"
      :style="{ width: `${width}px` }"
    >
      <button
        v-for="option in resolvedOptions"
        :key="option.value"
        type="button"
        class="flex h-[32px] w-full items-center px-[12px] text-left text-[12px] leading-[16px] text-[#0A0A0A] hover:bg-[rgba(236,236,240,0.6)]"
        @click="selectValue(option.value)"
      >
        {{ option.label }}
      </button>
    </div>
  </div>
</template>
