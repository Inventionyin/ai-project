<template>
  <div class="rounded-[12px] border border-black/10 bg-white p-4">
    <div class="flex items-center justify-between mb-3">
      <div class="text-[14px] font-semibold text-[#0A0A0A]">版本差异概览</div>
      <div class="flex items-center gap-2">
        <span class="px-2 py-0.5 rounded text-[11px] bg-green-50 text-green-700">+{{ addedCount }} 新增</span>
        <span class="px-2 py-0.5 rounded text-[11px] bg-red-50 text-red-700">-{{ removedCount }} 移除</span>
        <span class="px-2 py-0.5 rounded text-[11px] bg-amber-50 text-amber-700">~{{ updatedCount }} 修改</span>
      </div>
    </div>

    <div v-if="items.length === 0" class="text-[12px] text-[#717182] py-4 text-center">暂无变更项</div>

    <div v-else class="space-y-2">
      <div v-for="item in items" :key="item.id" class="flex items-start gap-3 p-2 rounded border" :class="itemBorderClass(item.changeType)">
        <div class="flex-shrink-0 w-6 h-6 rounded flex items-center justify-center text-[12px] font-bold" :class="itemIconClass(item.changeType)">
          {{ itemIcon(item.changeType) }}
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2">
            <span class="text-[13px] font-medium text-[#0A0A0A] truncate">{{ item.title || '-' }}</span>
            <span class="flex-shrink-0 px-1.5 py-0.5 rounded text-[10px]" :class="itemTagClass(item.changeType)">{{ item.changeType }}</span>
            <span v-if="item.impactLevel" class="flex-shrink-0 px-1.5 py-0.5 rounded text-[10px]" :class="impactTagClass(item.impactLevel)">{{ item.impactLevel }}</span>
          </div>
          <p class="mt-1 text-[12px] text-[#4A5565] line-clamp-2">{{ item.description || '暂无描述' }}</p>
          <div v-if="item.sourcePath" class="mt-1 text-[11px] text-[#717182] font-mono">{{ item.sourcePath }}</div>
        </div>
      </div>
    </div>

    <!-- Impact distribution bar -->
    <div v-if="items.length > 0" class="mt-4 pt-3 border-t border-black/5">
      <div class="text-[12px] text-[#717182] mb-2">影响级别分布</div>
      <div class="flex gap-1 h-2 rounded-full overflow-hidden bg-gray-100">
        <div v-if="criticalCount > 0" class="bg-red-500" :style="{ width: `${(criticalCount / items.length) * 100}%` }" :title="`CRITICAL: ${criticalCount}`"></div>
        <div v-if="highCount > 0" class="bg-orange-500" :style="{ width: `${(highCount / items.length) * 100}%` }" :title="`HIGH: ${highCount}`"></div>
        <div v-if="mediumCount > 0" class="bg-yellow-500" :style="{ width: `${(mediumCount / items.length) * 100}%` }" :title="`MEDIUM: ${mediumCount}`"></div>
        <div v-if="lowCount > 0" class="bg-green-500" :style="{ width: `${(lowCount / items.length) * 100}%` }" :title="`LOW: ${lowCount}`"></div>
      </div>
      <div class="flex gap-3 mt-2">
        <span v-if="criticalCount > 0" class="text-[11px] text-red-600">CRITICAL {{ criticalCount }}</span>
        <span v-if="highCount > 0" class="text-[11px] text-orange-600">HIGH {{ highCount }}</span>
        <span v-if="mediumCount > 0" class="text-[11px] text-yellow-600">MEDIUM {{ mediumCount }}</span>
        <span v-if="lowCount > 0" class="text-[11px] text-green-600">LOW {{ lowCount }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface ChangeItem {
  id: string
  changeType: string
  impactLevel?: string | null
  title?: string | null
  description?: string | null
  sourcePath?: string | null
}

const props = defineProps<{ items: ChangeItem[] }>()

const addedCount = computed(() => props.items.filter(i => i.changeType === 'ADDED').length)
const removedCount = computed(() => props.items.filter(i => i.changeType === 'REMOVED').length)
const updatedCount = computed(() => props.items.filter(i => i.changeType === 'UPDATED').length)
const criticalCount = computed(() => props.items.filter(i => String(i.impactLevel || '').toUpperCase() === 'CRITICAL').length)
const highCount = computed(() => props.items.filter(i => String(i.impactLevel || '').toUpperCase() === 'HIGH').length)
const mediumCount = computed(() => props.items.filter(i => String(i.impactLevel || '').toUpperCase() === 'MEDIUM').length)
const lowCount = computed(() => props.items.filter(i => String(i.impactLevel || '').toUpperCase() === 'LOW').length)

function itemBorderClass(type: string) {
  if (type === 'ADDED') return 'border-green-200 bg-green-50/30'
  if (type === 'REMOVED') return 'border-red-200 bg-red-50/30'
  return 'border-amber-200 bg-amber-50/30'
}

function itemIconClass(type: string) {
  if (type === 'ADDED') return 'bg-green-100 text-green-700'
  if (type === 'REMOVED') return 'bg-red-100 text-red-700'
  return 'bg-amber-100 text-amber-700'
}

function itemIcon(type: string) {
  if (type === 'ADDED') return '+'
  if (type === 'REMOVED') return '-'
  return '~'
}

function itemTagClass(type: string) {
  if (type === 'ADDED') return 'bg-green-100 text-green-700'
  if (type === 'REMOVED') return 'bg-red-100 text-red-700'
  return 'bg-amber-100 text-amber-700'
}

function impactTagClass(level: string) {
  const v = String(level || '').toUpperCase()
  if (v === 'CRITICAL') return 'bg-red-100 text-red-700'
  if (v === 'HIGH') return 'bg-orange-100 text-orange-700'
  if (v === 'MEDIUM') return 'bg-yellow-100 text-yellow-700'
  return 'bg-green-100 text-green-700'
}
</script>
