<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export type Row = {
  id: string
  testCaseId: string
  title: string
  type: 'API' | 'UI' | 'PERF' | 'MIX'
  priority: 'P0' | 'P1' | 'P2' | 'P3'
  status: '已评审' | '草稿' | '已弃用'
  module: string
  interfaceUrl: string
  method: string
  apiParams: Record<string, unknown> | null
  expectedResult?: string | null
  owner: string
  lastRun: '通过' | '失败' | '-' | '跳过'
  updatedAt: string
}

const props = defineProps<{
  rows: Row[]
  selectedIds: string[]
}>()

const emit = defineEmits<{
  (e: 'delete', index: number): void
  (e: 'edit', index: number): void
  (e: 'update:selectedIds', value: string[]): void
}>()

const router = useRouter()
const route = useRoute()

const projectId = computed(() => {
  const value = route.params.projectId
  return typeof value === 'string' && value.length > 0 ? value : '1'
})

function openCaseDetail(id: string) {
  router.push({
    path: `/projects/${projectId.value}/assets/testcases/${id}`,
    query: { tab: 'basic' }
  })
}

const selectedSet = computed(() => new Set(props.selectedIds))
const visibleIds = computed(() => props.rows.map((row) => row.id))
const isAllVisibleSelected = computed(() => visibleIds.value.length > 0 && visibleIds.value.every((id) => selectedSet.value.has(id)))
const isSomeVisibleSelected = computed(() => visibleIds.value.some((id) => selectedSet.value.has(id)))

function setSelectedIds(next: string[]) {
  emit('update:selectedIds', Array.from(new Set(next)))
}

function toggleAllVisible() {
  if (!visibleIds.value.length) return
  if (isAllVisibleSelected.value) {
    setSelectedIds(props.selectedIds.filter((id) => !visibleIds.value.includes(id)))
    return
  }
  setSelectedIds([...props.selectedIds, ...visibleIds.value])
}

function toggleRowSelection(id: string) {
  if (selectedSet.value.has(id)) {
    setSelectedIds(props.selectedIds.filter((item) => item !== id))
    return
  }
  setSelectedIds([...props.selectedIds, id])
}

function priorityClass(priority: Row['priority']) {
  if (priority === 'P0') return { bg: '#FFE2E2', fg: '#C10007' }
  if (priority === 'P1') return { bg: '#FFEDD4', fg: '#CA3500' }
  if (priority === 'P2') return { bg: '#FFF8CC', fg: '#A05A00' }
  return { bg: '#FFEDD4', fg: '#CA3500' }
}

function statusClass(status: Row['status']) {
  if (status === '已评审') return '#00A63E'
  if (status === '草稿') return '#D08700'
  return '#99A1AF'
}

function lastRunClass(lastRun: Row['lastRun']) {
  if (lastRun === '通过') return '#00A63E'
  if (lastRun === '失败') return '#FB2C36'
  if (lastRun === '跳过') return '#6A7282'
  return '#99A1AF'
}

function formatApiParams(apiParams: Row['apiParams']) {
  if (!apiParams || typeof apiParams !== 'object' || Array.isArray(apiParams)) return '-'
  const entries = Object.keys(apiParams)
  if (!entries.length) return '-'
  try {
    return JSON.stringify(apiParams)
  } catch {
    return '-'
  }
}

const rowHeight = '56.67px'
</script>

<template>
  <div class="w-full overflow-x-auto">
    <div class="min-w-[1620px]">
      <div class="grid grid-cols-[45px_140px_160px_minmax(160px,260px)_70px_70px_70px_220px_90px_260px_90px_80px_110px_150px] bg-[rgba(236,236,240,0.3)] border-x border-b border-black/10 divide-x divide-black/10">
        <div class="flex h-[56.33px] items-center justify-center">
          <input
            type="checkbox"
            class="h-[13px] w-[13px] rounded-[3px] border border-[#717182] bg-white accent-[#155DFC]"
            :checked="isAllVisibleSelected"
            :indeterminate="!isAllVisibleSelected && isSomeVisibleSelected"
            aria-label="Select all"
            @change="toggleAllVisible"
          />
        </div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">测试用例ID</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">功能模块</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">标题</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">类型</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">优先级</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">状态</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">interfaceUrl</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">调用方式</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">接口参数</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">维护人</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">最近运行</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">更新时间</div>
        <div class="flex h-[56.33px] items-center justify-center text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">操作</div>
      </div>

      <div class="border-b border-black/10">
        <div
          v-for="(row, index) in rows"
          :key="row.id"
          class="grid grid-cols-[45px_140px_160px_minmax(160px,260px)_70px_70px_70px_220px_90px_260px_90px_80px_110px_150px] border-x border-b border-black/10 divide-x divide-black/10 last:border-b-0"
          :style="{ height: rowHeight }"
        >
          <div class="relative h-full">
            <input
              type="checkbox"
              class="absolute left-[16px] top-1/2 h-[13px] w-[13px] -translate-y-1/2 rounded-[3px] border border-[#717182] bg-white accent-[#155DFC]"
              :checked="selectedSet.has(row.id)"
              aria-label="Select row"
              @change="toggleRowSelection(row.id)"
            />
          </div>

          <div class="relative h-full">
            <div class="absolute left-[12px] right-[12px] top-1/2 -translate-y-1/2 truncate text-[12px] leading-[16px] text-[#717182]">
              {{ row.testCaseId || '-' }}
            </div>
          </div>

          <div class="relative h-full">
            <div class="absolute left-[12px] right-[12px] top-1/2 -translate-y-1/2 truncate text-[12px] leading-[16px] text-[#717182]">
              {{ row.module || '-' }}
            </div>
          </div>

          <div class="relative h-full">
            <button
              type="button"
              class="absolute left-[12px] right-[12px] top-1/2 -translate-y-1/2 truncate text-left text-[14px] font-normal leading-[20px] text-[#0A0A0A]"
              :title="row.title"
              @click="openCaseDetail(row.id)"
            >
              {{ row.title }}
            </button>
          </div>

          <div class="relative h-full">
            <div class="absolute left-[12px] top-1/2 -translate-y-1/2 rounded-full px-[8px] py-[2px] text-[12px] font-medium leading-[16px]" style="background:#DBEAFE;color:#1447E6;">
              {{ row.type }}
            </div>
          </div>

          <div class="relative h-full">
            <div
              class="absolute left-[12px] top-1/2 -translate-y-1/2 rounded-full px-[8px] py-[2px] text-[12px] font-medium leading-[16px]"
              :style="{ background: priorityClass(row.priority).bg, color: priorityClass(row.priority).fg }"
            >
              {{ row.priority }}
            </div>
          </div>

          <div class="relative h-full">
            <div class="absolute left-[12px] top-1/2 -translate-y-1/2 text-[12px] font-medium leading-[16px]" :style="{ color: statusClass(row.status) }">
              {{ row.status }}
            </div>
          </div>

          <div class="relative h-full">
            <div
              class="absolute left-[12px] right-[12px] top-1/2 -translate-y-1/2 truncate text-[12px] leading-[16px] text-[#155DFC]"
              :title="row.interfaceUrl || ''"
            >
              {{ row.interfaceUrl || '-' }}
            </div>
          </div>

          <div class="relative h-full">
            <div class="absolute left-[12px] top-1/2 -translate-y-1/2 text-[12px] font-medium leading-[16px] text-[#717182]">
              {{ row.method || '-' }}
            </div>
          </div>

          <div class="relative h-full">
            <div
              class="absolute left-[12px] right-[12px] top-1/2 -translate-y-1/2 truncate text-[12px] leading-[16px] text-[#717182]"
              :title="formatApiParams(row.apiParams)"
            >
              {{ formatApiParams(row.apiParams) }}
            </div>
          </div>

          <div class="relative h-full">
            <div class="absolute left-[12px] right-[12px] top-1/2 -translate-y-1/2 truncate text-[12px] leading-[16px] text-[#717182]">
              {{ row.owner }}
            </div>
          </div>

          <div class="relative h-full">
            <div class="absolute left-[12px] top-1/2 -translate-y-1/2 text-[12px] font-medium leading-[16px]" :style="{ color: lastRunClass(row.lastRun) }">
              {{ row.lastRun }}
            </div>
          </div>

          <div class="relative h-full">
            <div class="absolute left-[12px] top-1/2 -translate-y-1/2 text-[12px] leading-[16px] text-[#717182]">
              {{ row.updatedAt }}
            </div>
          </div>

          <div class="flex h-full items-center justify-center">
            <div class="flex items-center gap-[12px]">
              <button
                type="button"
                class="text-[12px] font-medium leading-[16px] text-[#155DFC] hover:underline"
                @click.stop="emit('edit', index)"
              >
                编辑
              </button>
              <button
                type="button"
                class="text-[12px] font-medium leading-[16px] text-[#FB2C36] hover:underline"
                @click.stop="emit('delete', index)"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
