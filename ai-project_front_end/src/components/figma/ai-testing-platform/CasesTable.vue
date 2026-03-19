<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export type Row = {
  id: string
  title: string
  type: 'API' | 'UI' | 'PERF' | 'MIX'
  priority: 'P0' | 'P1' | 'P2' | 'P3'
  status: '已评审' | '草稿' | '已弃用'
  feature: string
  story: string
  callUrl: string
  bindingConfig: string
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
  (e: 'manage-bindings', payload: { id: string; title: string }): void
}>()

const openMenuIndex = ref<number | null>(null)

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

function closeMenu() {
  openMenuIndex.value = null
}

function toggleMenu(index: number) {
  openMenuIndex.value = openMenuIndex.value === index ? null : index
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

const rowHeight = '56.67px'
</script>

<template>
  <button
    v-if="openMenuIndex !== null"
    type="button"
    class="fixed inset-0 z-40"
    aria-label="Close actions menu"
    @click="closeMenu"
  />

  <div class="w-full overflow-x-auto">
    <div class="min-w-[1220px]">
      <div class="grid grid-cols-[45px_minmax(160px,240px)_70px_70px_70px_120px_120px_180px_100px_80px_80px_110px_47px] bg-[rgba(236,236,240,0.3)] border-b border-black/10">
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
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">标题</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">类型</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">优先级</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">状态</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">Feature</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">Story</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">调用 URL</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">绑定配置</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">维护人</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">最近运行</div>
        <div class="flex h-[56.33px] items-center px-[12px] text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">更新时间</div>
        <div class="flex h-[56.33px] items-center justify-center text-[12px] font-medium leading-[16px] text-[#717182] whitespace-nowrap">...</div>
      </div>

      <div class="border-b border-black/10">
        <div
          v-for="(row, index) in rows"
          :key="row.id"
          class="grid grid-cols-[45px_minmax(160px,240px)_70px_70px_70px_120px_120px_180px_100px_80px_80px_110px_47px] border-b border-black/10 last:border-b-0"
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
            <div class="absolute left-[12px] right-[12px] top-1/2 -translate-y-1/2 truncate text-[12px] leading-[16px] text-[#717182]">
              {{ row.feature || '-' }}
            </div>
          </div>

          <div class="relative h-full">
            <div class="absolute left-[12px] right-[12px] top-1/2 -translate-y-1/2 truncate text-[12px] leading-[16px] text-[#717182]">
              {{ row.story || '-' }}
            </div>
          </div>

          <div class="relative h-full">
            <div class="absolute left-[12px] right-[12px] top-1/2 -translate-y-1/2 truncate text-[12px] leading-[16px] text-[#717182]">
              {{ row.callUrl || '-' }}
            </div>
          </div>

          <div class="relative h-full">
            <button
              type="button"
              class="absolute left-[12px] right-[12px] top-1/2 -translate-y-1/2 truncate text-left text-[12px] leading-[16px] text-[#155DFC] hover:underline"
              :title="row.bindingConfig || ''"
              @click.stop="emit('manage-bindings', { id: row.id, title: row.title })"
            >
              {{ row.bindingConfig || '-' }}
            </button>
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

          <div class="relative h-full">
            <button
              type="button"
              class="absolute left-1/2 top-1/2 z-30 -translate-x-1/2 -translate-y-1/2 rounded-[6px] px-[6px] py-[4px] text-[16px] font-semibold leading-[16px] text-[#717182] hover:bg-black/5"
              aria-label="Open row actions"
              @click.stop="toggleMenu(index)"
            >
              ...
            </button>

            <div
              v-if="openMenuIndex === index"
              class="absolute right-[8px] top-1/2 z-50 -translate-y-1/2 overflow-hidden rounded-[10px] border border-black/10 bg-white shadow-[0px_10px_15px_-3px_rgba(0,0,0,0.1),0px_4px_6px_-4px_rgba(0,0,0,0.1)]"
            >
              <button
                type="button"
                class="block w-full px-[12px] py-[8px] text-left text-[14px] leading-[20px] text-[#0A0A0A] hover:bg-black/5"
                @click.stop="emit('edit', index); closeMenu()"
              >
                编辑
              </button>
              <button
                type="button"
                class="block w-full px-[12px] py-[8px] text-left text-[14px] leading-[20px] text-[#FB2C36] hover:bg-black/5"
                @click.stop="emit('delete', index); closeMenu()"
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
