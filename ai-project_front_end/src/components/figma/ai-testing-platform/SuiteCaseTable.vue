<script setup lang="ts">
import { ref } from 'vue'
import suiteDetailDrag from '@/assets/figma/ai-testing-platform/suite-detail-drag.svg'
import suiteDetailConfig from '@/assets/figma/ai-testing-platform/suite-detail-config.svg'
import suiteDetailChevron from '@/assets/figma/ai-testing-platform/suite-detail-chevron.svg'

type SuiteCaseRow = {
  title: string
  typeLabel: string
  priority: string
}

const props = defineProps<{
  rows: SuiteCaseRow[]
}>()

const emit = defineEmits<{
  (e: 'remove', index: number): void
  (e: 'move', payload: { from: number; to: number }): void
}>()

const activeDeleteIndex = ref<number | null>(null)
const dragIndex = ref<number | null>(null)
const overIndex = ref<number | null>(null)

function onDelete(index: number) {
  activeDeleteIndex.value = index
  window.setTimeout(() => {
    emit('remove', index)
    activeDeleteIndex.value = null
  }, 180)
}

function moveUp(i: number) {
  if (i <= 0) return
  emit('move', { from: i, to: i - 1 })
}

function moveDown(i: number) {
  if (i >= props.rows.length - 1) return
  emit('move', { from: i, to: i + 1 })
}

function onDragStart(i: number, e: DragEvent) {
  dragIndex.value = i
  e.dataTransfer?.setData('text/plain', String(i))
  e.dataTransfer?.setDragImage(new Image(), 0, 0)
}

function onDragOver(i: number, e: DragEvent) {
  e.preventDefault()
  overIndex.value = i
}

function onDrop(i: number, e: DragEvent) {
  e.preventDefault()
  const from = dragIndex.value
  dragIndex.value = null
  overIndex.value = null
  if (from == null || from === i) return
  emit('move', { from, to: i })
}
</script>

<template>
  <section class="w-full md:w-[768px]">
    <div class="px-[16px] pt-[16px]">
      <div class="overflow-hidden rounded-[14px] border-[0.6667px] border-black/10 bg-white">
        <div class="flex h-[36.67px] items-center bg-[rgba(236,236,240,0.3)] px-[16px] border-b-[0.6667px] border-black/10">
          <div class="w-[40px] text-[12px] font-medium leading-[16px] text-[#717182]">#</div>
          <div class="flex-1 text-[12px] font-medium leading-[16px] text-[#717182]">标题</div>
          <div class="w-[64px] text-[12px] font-medium leading-[16px] text-[#717182]">类型</div>
          <div class="w-[64px] text-[12px] font-medium leading-[16px] text-[#717182]">优先级</div>
          <div class="w-[80px] text-right text-[12px] font-medium leading-[16px] text-[#717182]">操作</div>
        </div>

        <div
          v-for="(row, i) in props.rows"
          :key="`${row.title}-${i}`"
          class="flex h-[48.67px] items-center px-[16px] border-b-[0.6667px] border-black/10 last:border-b-0"
          draggable="true"
          @dragstart="onDragStart(i, $event)"
          @dragover="onDragOver(i, $event)"
          @drop="onDrop(i, $event)"
          :class="overIndex === i ? 'bg-[rgba(236,236,240,0.3)]' : ''"
        >
          <div class="flex w-[40px] items-center gap-[8px]">
            <img :src="suiteDetailDrag" alt="" class="h-[14px] w-[14px]" />
            <span class="text-[12px] leading-[16px] text-[#717182]">{{ i + 1 }}</span>
          </div>

          <div class="flex-1 text-[12px] leading-[16px] text-[#0A0A0A]">{{ row.title }}</div>

          <div class="w-[64px]">
            <span class="inline-flex h-[19.33px] items-center rounded-[4px] bg-[#DBEAFE] px-[6px] text-[12px] leading-[16px] text-[#1447E6]">
              {{ row.typeLabel }}
            </span>
          </div>

          <div class="w-[64px] text-[12px] leading-[16px] text-[#717182]">{{ row.priority }}</div>

          <div class="flex w-[80px] items-center justify-end gap-[6px]">
            <button
              type="button"
              class="h-[24px] w-[24px] rounded-[6px] bg-[rgba(236,236,240,0.4)] flex items-center justify-center text-[#717182]"
              :class="i === 0 ? 'opacity-40 pointer-events-none' : 'hover:text-[#0A0A0A]'"
              @click="moveUp(i)"
              aria-label="Move up"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" class="h-[14px] w-[14px]" fill="currentColor">
                <path d="M10 5l5 5H5l5-5Z" />
              </svg>
            </button>
            <button
              type="button"
              class="h-[24px] w-[24px] rounded-[6px] bg-[rgba(236,236,240,0.4)] flex items-center justify-center text-[#717182]"
              :class="i === props.rows.length - 1 ? 'opacity-40 pointer-events-none' : 'hover:text-[#0A0A0A]'"
              @click="moveDown(i)"
              aria-label="Move down"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" class="h-[14px] w-[14px]" fill="currentColor">
                <path d="M10 15l-5-5h10l-5 5Z" />
              </svg>
            </button>
            <button
              type="button"
              class="h-[24px] w-[24px] rounded-[6px] bg-[rgba(236,236,240,0.4)] flex items-center justify-center"
              :class="activeDeleteIndex === i ? 'text-[#FB2C36]' : 'text-[#717182]'"
              @mousedown="activeDeleteIndex = i"
              @mouseup="activeDeleteIndex = null"
              @mouseleave="activeDeleteIndex = null"
              @click="onDelete(i)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" class="h-[14px] w-[14px]" fill="currentColor">
                <path d="M5 7a1 1 0 0 1 2 0v7a1 1 0 1 1-2 0V7Zm4 0a1 1 0 1 1 2 0v7a1 1 0 1 1-2 0V7Zm-1-4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2h2a1 1 0 1 1 0 2h-1v10a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V5H3a1 1 0 1 1 0-2h2Zm8 2H6v10a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V5Zm-3-2h-2a1 1 0 0 0-1 1h4a1 1 0 0 0-1-1Z" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <button
      type="button"
      class="flex h-[44px] w-full items-center gap-[8px] border-l-[0.6667px] border-black/10 bg-white px-[16px]"
    >
      <img :src="suiteDetailConfig" alt="" class="h-[14px] w-[14px]" />
      <span class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">套件配置</span>
      <span class="flex-1" />
      <img :src="suiteDetailChevron" alt="" class="h-[14px] w-[14px]" />
    </button>
  </section>
</template>
