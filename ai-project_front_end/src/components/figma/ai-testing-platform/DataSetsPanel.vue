<script setup lang="ts">
import { computed, ref } from 'vue'
import uploadIcon from '@/assets/figma/ai-testing-platform/datasets-upload-icon.svg'
import searchIcon from '@/assets/figma/ai-testing-platform/datasets-search-icon.svg'
import modalClose28 from '@/assets/figma/ai-testing-platform/modal-close-28.svg'
import DataSetsTable, { type Row } from '@/components/figma/ai-testing-platform/DataSetsTable.vue'

const rows = ref<Row[]>([
  {
    name: '订单测试数据集',
    format: 'CSV',
    size: '12KB',
    rows: '100',
    owner: '张三',
    updatedAt: '2024-03-14',
    actionsIcon: 'row-actions-1',
    data: []
  },
  {
    name: '用户边界数据',
    format: 'JSON',
    size: '5KB',
    rows: '50',
    owner: '李四',
    updatedAt: '2024-03-12',
    actionsIcon: 'row-actions-2',
    data: []
  },
  {
    name: '支付场景参数',
    format: 'CSV',
    size: '8KB',
    rows: '80',
    owner: '王五',
    updatedAt: '2024-03-10',
    actionsIcon: 'row-actions-3',
    data: []
  }
])

const isPreviewOpen = ref(false)
const previewRow = ref<Row | null>(null)

const previewData = computed(() => previewRow.value?.data ?? [])
const previewColumns = computed(() => {
  const first = previewData.value[0]
  if (!first) return []
  return Object.keys(first)
})
const previewColMinPx = computed(() => {
  const count = previewColumns.value.length
  if (count <= 4) return 160
  if (count <= 6) return 140
  return 120
})

function openPreview(row: Row) {
  previewRow.value = row
  isPreviewOpen.value = true
}

function closePreview() {
  isPreviewOpen.value = false
  previewRow.value = null
}

const isDeleteOpen = ref(false)
const deletingRow = ref<Row | null>(null)

function openDelete(row: Row) {
  deletingRow.value = row
  isDeleteOpen.value = true
}

function closeDelete() {
  isDeleteOpen.value = false
  deletingRow.value = null
}

function confirmDelete() {
  const target = deletingRow.value
  if (!target) return
  const idx = rows.value.findIndex((r) => r.name === target.name)
  if (idx >= 0) rows.value.splice(idx, 1)
  if (previewRow.value?.name === target.name) closePreview()
  closeDelete()
}

const isDownloading = ref(false)
let downloadingTimer: number | null = null

function downloadDataSet() {
  isDownloading.value = true
  if (downloadingTimer) window.clearTimeout(downloadingTimer)
  downloadingTimer = window.setTimeout(() => {
    isDownloading.value = false
    downloadingTimer = null
  }, 1500)
}

const isUploadOpen = ref(false)
const uploadName = ref('')
const uploadFile = ref<File | null>(null)
const uploadInputRef = ref<HTMLInputElement | null>(null)

function openUpload() {
  isUploadOpen.value = true
}

function closeUpload() {
  isUploadOpen.value = false
  uploadName.value = ''
  uploadFile.value = null
  if (uploadInputRef.value) uploadInputRef.value.value = ''
}

function onPickFile() {
  uploadInputRef.value?.click()
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0] ?? null
  uploadFile.value = file
}

function onDropFile(e: DragEvent) {
  e.preventDefault()
  const file = e.dataTransfer?.files?.[0] ?? null
  if (!file) return
  uploadFile.value = file
}

function formatSize(bytes: number) {
  if (!Number.isFinite(bytes)) return '-'
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 102.4) / 10}KB`
  return `${Math.round((bytes / 1024 / 1024) * 10) / 10}MB`
}

function detectFormat(file: File | null): 'CSV' | 'JSON' {
  const name = file?.name?.toLowerCase() ?? ''
  if (name.endsWith('.csv')) return 'CSV'
  if (name.endsWith('.json')) return 'JSON'
  return 'CSV'
}

function handleUpload() {
  const file = uploadFile.value
  if (!file) return
  const name = uploadName.value.trim() || file.name.replace(/\.(csv|json)$/i, '')

  rows.value.unshift({
    name,
    format: detectFormat(file),
    size: formatSize(file.size),
    rows: '—',
    owner: '张三',
    updatedAt: new Date().toISOString().slice(0, 10),
    actionsIcon: 'row-actions-1',
    data: []
  })

  closeUpload()
}
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)] md:pr-[16.67px]">
    <div class="flex flex-col gap-[16px] px-[16px] pt-[16px] md:px-[24px] md:pt-[24px]">
      <div class="flex flex-col gap-[12px] md:flex-row md:items-center md:justify-between md:gap-0">
        <div class="flex flex-col gap-[2px]">
          <div class="text-[18px] font-semibold leading-[28px] text-[#0A0A0A]">测试数据集</div>
          <div class="text-[14px] leading-[20px] text-[#717182]">CSV / JSON 数据文件管理</div>
        </div>

        <button type="button" class="relative h-[32px] w-[114px] rounded-[10px] bg-[#155DFC]" @click="openUpload">
          <img :src="uploadIcon" alt="" class="absolute left-[12px] top-[9px] h-[14px] w-[14px]" />
          <span class="absolute left-[30px] top-[6.33px] text-[14px] font-medium leading-[20px] text-white">
            上传数据集
          </span>
        </button>
      </div>

      <div class="relative h-[36px] w-full max-w-[384px] rounded-[10px] border border-black/10 bg-white pl-[36px] pr-[12px]">
        <img :src="searchIcon" alt="" class="absolute left-[12px] top-[11px] h-[14px] w-[14px]" />
        <div class="flex h-full items-center text-[14px] leading-[20px] text-[#0A0A0A]">搜索数据集...</div>
      </div>

      <div class="w-full rounded-[14px] border border-black/10 bg-white p-[0.67px]">
        <DataSetsTable :rows="rows" @view="openPreview" @download="downloadDataSet" @delete="openDelete" />
      </div>
    </div>
  </div>

  <div v-if="isDownloading" class="fixed left-1/2 top-[16px] z-[60] -translate-x-1/2">
    <div class="rounded-[10px] border border-black/10 bg-white px-[12px] py-[8px] text-[14px] leading-[20px] text-[#0A0A0A] shadow-[0px_10px_15px_-3px_rgba(0,0,0,0.1),0px_4px_6px_-4px_rgba(0,0,0,0.1)]">
      数据下载中
    </div>
  </div>

  <div v-if="isUploadOpen" class="fixed inset-0 z-50 flex items-center justify-center">
    <button class="absolute inset-0 bg-black/40" type="button" aria-label="Close" @click="closeUpload" />

    <div class="relative h-[388px] w-full max-w-[calc(100vw-32px)] overflow-hidden rounded-[16px] border border-black/10 bg-white shadow-[0px_25px_50px_-12px_rgba(0,0,0,0.25)] sm:w-[448px] sm:max-w-[448px]">
      <div class="px-[24px] pt-[24px]">
        <div class="text-[16px] font-semibold leading-[24px] text-[#0A0A0A]">上传数据集</div>
      </div>

      <div class="px-[24px] pt-[16px]">
        <div class="flex flex-col gap-[16px]">
          <div class="flex flex-col gap-[6px]">
            <div class="h-[20px] text-[14px] font-medium leading-[20px] text-[#0A0A0A]">数据集名称</div>
            <input
              v-model="uploadName"
              class="h-[36px] w-full rounded-[10px] border-[0.6667px] border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              placeholder="如：订单测试数据集"
              type="text"
            />
          </div>

          <div class="flex flex-col gap-[6px]">
            <div class="h-[20px] text-[14px] font-medium leading-[20px] text-[#0A0A0A]">选择文件（CSV / JSON）</div>

            <input ref="uploadInputRef" class="hidden" type="file" accept=".csv,.json" @change="onFileChange" />

            <button
              type="button"
              class="relative h-[140px] w-full rounded-[14px] border-2 border-dashed border-black/10 bg-white"
              style="border-dasharray: 4 2"
              @click="onPickFile"
              @dragover.prevent
              @drop="onDropFile"
            >
              <svg
                class="absolute left-1/2 top-[34px] h-6 w-6 -translate-x-1/2"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden="true"
              >
                <path d="M4 17v2a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-2" stroke="#717182" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M8 8l4-4 4 4" stroke="#717182" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M12 4v10" stroke="#717182" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>

              <div class="absolute left-1/2 top-[66px] w-[332px] -translate-x-1/2 text-center text-[14px] leading-[20px] text-[#717182]">
                点击或拖拽文件到此处
              </div>
              <div class="absolute left-1/2 top-[90px] w-[332px] -translate-x-1/2 text-center text-[12px] leading-[16px] text-[#717182]">
                支持 .csv .json，最大 10MB
              </div>
            </button>
          </div>
        </div>
      </div>

      <div class="absolute left-[24px] top-[328px] flex h-[36px] w-[400px] gap-[8px]">
        <button
          type="button"
          class="h-[36px] flex-1 rounded-[10px] border-[0.6667px] border-black/10 bg-white text-[14px] font-medium leading-[20px] text-[#0A0A0A]"
          @click="closeUpload"
        >
          取消
        </button>
        <button
          type="button"
          class="h-[36px] flex-1 rounded-[10px] bg-[#155DFC] text-[14px] font-medium leading-[20px] text-white"
          @click="handleUpload"
        >
          上传
        </button>
      </div>
    </div>
  </div>

  <div v-if="isPreviewOpen" class="fixed inset-0 z-50 flex items-center justify-center">
    <button class="absolute inset-0 bg-black/40" type="button" aria-label="Close" @click="closePreview" />

    <div
      class="relative max-h-[calc(100vh-32px)] w-full max-w-[calc(100vw-32px)] overflow-hidden rounded-[16px] border border-black/10 bg-white shadow-[0px_25px_50px_-12px_rgba(0,0,0,0.25)] sm:w-[720px] sm:max-w-[720px]"
    >
      <div class="flex h-[60.67px] items-center justify-between border-b border-black/10 px-[24px]">
        <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">数据列表</div>
        <button type="button" class="flex h-[28px] w-[28px] items-center justify-center rounded-[10px]" aria-label="Close" @click="closePreview">
          <img :src="modalClose28" alt="" class="h-[28px] w-[28px]" />
        </button>
      </div>

      <div class="flex max-h-[calc(100vh-32px-60.67px)] flex-col gap-[12px] overflow-auto px-[24px] py-[16px]">
        <div class="flex flex-wrap items-center gap-x-[16px] gap-y-[6px] text-[12px] leading-[16px] text-[#717182]">
          <div class="text-[#0A0A0A]">{{ previewRow?.name }}</div>
          <div>类型：{{ previewRow?.format }}</div>
          <div>行数：{{ previewRow?.rows }}</div>
          <div>更新时间：{{ previewRow?.updatedAt }}</div>
        </div>

        <div v-if="previewData.length === 0" class="flex h-[240px] w-full items-center justify-center rounded-[14px] border border-black/10 bg-white">
          <div class="text-[14px] leading-[20px] text-[#717182]">暂无数据</div>
        </div>

        <div v-else class="w-full overflow-x-auto rounded-[14px] border border-black/10 bg-white">
          <div class="min-w-full">
            <div class="grid border-b border-black/10 bg-[rgba(236,236,240,0.3)]" :style="{ gridTemplateColumns: `repeat(${previewColumns.length}, minmax(${previewColMinPx}px, 1fr))` }">
              <div
                v-for="(col, colIdx) in previewColumns"
                :key="col"
                class="h-[40.33px] px-[16px] py-[12px] text-[12px] font-medium leading-[16px] text-[#717182]"
                :class="colIdx === previewColumns.length - 1 ? '' : 'border-r border-black/5'"
              >
                <div class="truncate">{{ col }}</div>
              </div>
            </div>

            <div
              v-for="(row, idx) in previewData"
              :key="idx"
              class="grid border-b border-black/10 last:border-b-0"
              :style="{ gridTemplateColumns: `repeat(${previewColumns.length}, minmax(${previewColMinPx}px, 1fr))` }"
            >
              <div
                v-for="(col, colIdx) in previewColumns"
                :key="col"
                class="flex h-[44px] items-center px-[16px] text-[12px] leading-[16px] text-[#0A0A0A]"
                :class="colIdx === previewColumns.length - 1 ? '' : 'border-r border-black/5'"
              >
                <div class="w-full truncate">{{ row[col] ?? '' }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-if="isDeleteOpen" class="fixed inset-0 z-50 flex items-center justify-center">
    <button class="absolute inset-0 bg-black/40" type="button" aria-label="Close" @click="closeDelete" />

    <div
      class="relative w-full max-w-[calc(100vw-32px)] overflow-hidden rounded-[16px] border border-black/10 bg-white shadow-[0px_25px_50px_-12px_rgba(0,0,0,0.25)] sm:w-[448px] sm:max-w-[448px]"
    >
      <div class="flex h-[60.67px] items-center justify-between border-b border-black/10 px-[24px]">
        <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">提示</div>
        <button type="button" class="flex h-[28px] w-[28px] items-center justify-center rounded-[10px]" aria-label="Close" @click="closeDelete">
          <img :src="modalClose28" alt="" class="h-[28px] w-[28px]" />
        </button>
      </div>

      <div class="px-[24px] pt-[20px] pb-[24px]">
        <div class="text-[14px] leading-[20px] text-[#0A0A0A]">是否删除测试数据？</div>

        <div class="mt-[20px] flex gap-[8px]">
          <button
            type="button"
            class="h-[36px] flex-1 rounded-[10px] border border-black/10 bg-white text-[14px] font-medium leading-[20px] text-[#0A0A0A]"
            @click="closeDelete"
          >
            取消
          </button>
          <button
            type="button"
            class="h-[36px] flex-1 rounded-[10px] bg-[#FB2C36] text-[14px] font-medium leading-[20px] text-white"
            @click="confirmDelete"
          >
            确定
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
