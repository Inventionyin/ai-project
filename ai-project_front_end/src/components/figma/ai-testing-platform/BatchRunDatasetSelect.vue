<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import selectChevron from '@/assets/figma/ai-testing-platform/batch-run-select-chevron.svg'
import searchIcon from '@/assets/figma/ai-testing-platform/batch-run-dataset-search.svg'

export type BatchRunDatasetOption = {
  id: string
  name: string
  format: 'CSV' | 'JSON'
  rows: number
}

const props = withDefaults(defineProps<{
  value: string
  options: BatchRunDatasetOption[]
  width: number
  height?: number
}>(), {
  height: 28
})

const emit = defineEmits<{
  (e: 'update:value', value: string): void
}>()

const rootRef = ref<HTMLElement | null>(null)
const isOpen = ref(false)
const query = ref('')

const resolvedOptions = computed(() => {
  const list = Array.isArray(props.options) ? props.options : []
  const normalized = list.filter((item) => item && typeof item.name === 'string' && item.name.trim().length > 0)
  const q = query.value.trim().toLowerCase()
  if (!q) return normalized
  return normalized.filter((item) => item.name.toLowerCase().includes(q))
})

function open() {
  isOpen.value = true
}

function close() {
  isOpen.value = false
}

function toggle() {
  if (isOpen.value) {
    close()
    return
  }
  open()
}

function selectOption(option: BatchRunDatasetOption) {
  emit('update:value', option.name)
  close()
}

function onWindowClick(e: MouseEvent) {
  if (!isOpen.value) return
  const target = e.target as Node | null
  if (!target) return
  if (rootRef.value?.contains(target)) return
  close()
}

function onKeydown(e: KeyboardEvent) {
  if (e.key !== 'Escape') return
  if (!isOpen.value) return
  close()
}

watch(isOpen, (next) => {
  if (next) query.value = ''
})

onMounted(() => {
  window.addEventListener('click', onWindowClick)
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', onWindowClick)
  window.removeEventListener('keydown', onKeydown)
})

function formatBadgeClass(format: BatchRunDatasetOption['format']) {
  if (format === 'CSV') return 'bg-[#DCFCE7] text-[#008236]'
  return 'bg-[#DBEAFE] text-[#1447E6]'
}
</script>

<template>
  <div ref="rootRef" class="relative" :style="{ width: `${width}px` }">
    <button
      v-if="!isOpen"
      type="button"
      class="flex items-center justify-between gap-[6px] rounded-[10px] border border-black/10 bg-transparent px-[10px]"
      :style="{ width: `${width}px`, height: `${height}px` }"
      @click="toggle"
    >
      <span
        class="flex-1 truncate text-[11px] leading-[16.5px]"
        :class="value ? 'font-medium text-[#0A0A0A]' : 'font-normal text-[#717182]'"
      >
        {{ value || '搜索数据集…' }}
      </span>
      <img :src="selectChevron" alt="" class="h-[10px] w-[10px] shrink-0" />
    </button>

    <div
      v-else
      class="flex items-center gap-[6px] rounded-[10px] border border-[#51A2FF] bg-transparent px-[10px] shadow-[0px_0px_0px_2px_rgba(81,162,255,0.2)]"
      :style="{ width: `${width}px`, height: `${height}px` }"
      @click="open"
    >
      <img :src="searchIcon" alt="" class="h-[10px] w-[10px] shrink-0" />
      <input
        v-model="query"
        class="h-[16.5px] w-full bg-transparent text-[11px] leading-[16.5px] text-[#0A0A0A] outline-none placeholder:text-[#0A0A0A]"
        placeholder="搜索数据集…"
        type="text"
      />
    </div>

    <div
      v-if="isOpen"
      class="absolute left-0 top-full z-30 mt-[4px] overflow-hidden rounded-[14px] border border-black/10 bg-white p-[0.67px] shadow-[0px_8px_10px_-6px_rgba(0,0,0,0.1),0px_20px_25px_-5px_rgba(0,0,0,0.1)]"
      :style="{ width: `${width}px` }"
    >
      <button
        v-for="option in resolvedOptions"
        :key="option.id"
        type="button"
        class="flex h-[33.33px] w-full items-center justify-between px-[12px] text-left hover:bg-[rgba(236,236,240,0.6)]"
        @click="selectOption(option)"
      >
        <span class="flex items-center gap-[6px]">
          <span
            class="inline-flex h-[17.5px] items-center rounded-[4px] px-[4px] text-[9px] font-bold leading-[14px]"
            :class="formatBadgeClass(option.format)"
          >
            {{ option.format }}
          </span>
          <span class="text-[11px] font-medium leading-[16.5px] text-[#0A0A0A]">{{ option.name }}</span>
        </span>
        <span class="text-[10px] leading-[15px] text-[#717182]" style="font-family: Consolas">
          {{ option.rows }} 行
        </span>
      </button>
    </div>
  </div>
</template>
