<script setup lang="ts">
import dataSetRowIcon from '@/assets/figma/ai-testing-platform/datasets-row-icon.svg'
import rowActions1 from '@/assets/figma/ai-testing-platform/datasets-row-actions-1.svg'
import rowActions2 from '@/assets/figma/ai-testing-platform/datasets-row-actions-2.svg'
import rowActions3 from '@/assets/figma/ai-testing-platform/datasets-row-actions-3.svg'

export type Row = {
  name: string
  format: 'CSV' | 'JSON'
  size: string
  rows: string
  owner: string
  updatedAt: string
  actionsIcon: 'row-actions-1' | 'row-actions-2' | 'row-actions-3'
  data?: Record<string, string>[]
}

defineProps<{
  rows: Row[]
}>()

defineEmits<{
  (e: 'view', row: Row): void
  (e: 'download', row: Row): void
  (e: 'delete', row: Row): void
}>()

const actionIconMap: Record<Row['actionsIcon'], string> = {
  'row-actions-1': rowActions1,
  'row-actions-2': rowActions2,
  'row-actions-3': rowActions3
}

function formatClass(format: Row['format']) {
  if (format === 'CSV') return { bg: '#DCFCE7', fg: '#008236' }
  return { bg: '#DBEAFE', fg: '#1447E6' }
}
</script>

<template>
  <div class="w-full overflow-x-auto">
    <div class="min-w-full">
      <div class="grid grid-cols-[minmax(200px,2fr)_minmax(72px,0.8fr)_minmax(80px,0.9fr)_minmax(72px,0.7fr)_minmax(90px,0.9fr)_minmax(110px,0.9fr)_124px] bg-[rgba(236,236,240,0.3)] border-b border-black/10">
        <div class="h-[40.33px] px-[16px] py-[12px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]">名称</div>
        </div>
        <div class="h-[40.33px] px-[16px] py-[12px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]">类型</div>
        </div>
        <div class="h-[40.33px] px-[16px] py-[12px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]">大小</div>
        </div>
        <div class="h-[40.33px] px-[16px] py-[12px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]">行数</div>
        </div>
        <div class="h-[40.33px] px-[16px] py-[12px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]">负责人</div>
        </div>
        <div class="h-[40.33px] px-[16px] py-[12px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]">更新时间</div>
        </div>
        <div class="h-[40.33px]" />
      </div>

      <div>
        <div
          v-for="row in rows"
          :key="row.name"
          class="grid grid-cols-[minmax(200px,2fr)_minmax(72px,0.8fr)_minmax(80px,0.9fr)_minmax(72px,0.7fr)_minmax(90px,0.9fr)_minmax(110px,0.9fr)_124px] h-[56.67px] border-b border-black/10 last:border-b-0"
        >
          <div class="flex items-center gap-[8px] px-[16px]">
            <img :src="dataSetRowIcon" alt="" class="h-[14px] w-[14px]" />
            <div class="min-w-0 text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
              <div class="truncate">{{ row.name }}</div>
            </div>
          </div>

          <div class="flex items-center px-[16px]">
            <div
              class="rounded-full px-[8px] py-[2px] text-[12px] font-medium leading-[16px]"
              :style="{ background: formatClass(row.format).bg, color: formatClass(row.format).fg }"
            >
              {{ row.format }}
            </div>
          </div>

          <div class="flex items-center px-[16px] text-[12px] leading-[16px] text-[#717182]">
            {{ row.size }}
          </div>

          <div class="flex items-center px-[16px] text-[12px] leading-[16px] text-[#717182]">
            {{ row.rows }}
          </div>

          <div class="flex items-center px-[16px] text-[12px] leading-[16px] text-[#717182]">
            {{ row.owner }}
          </div>

          <div class="flex items-center px-[16px] text-[12px] leading-[16px] text-[#717182]">
            {{ row.updatedAt }}
          </div>

          <div class="flex items-center">
            <div class="relative h-[56.67px] w-[124px]">
              <img :src="actionIconMap[row.actionsIcon]" alt="" class="absolute inset-0 h-[56.67px] w-[124px]" />
              <button
                type="button"
                class="absolute left-0 top-0 h-full w-[41.33px]"
                aria-label="查看数据"
                @click="$emit('view', row)"
              />
              <button
                type="button"
                class="absolute left-[41.33px] top-0 h-full w-[41.33px]"
                aria-label="下载数据集"
                @click="$emit('download', row)"
              />
              <button
                type="button"
                class="absolute right-0 top-0 h-full w-[41.33px]"
                aria-label="删除数据集"
                @click="$emit('delete', row)"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
