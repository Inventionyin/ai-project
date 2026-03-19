<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import btnAiGenerate from '@/assets/figma/ai-testing-platform/btn-ai-generate.svg'
import btnPlus from '@/assets/figma/ai-testing-platform/btn-plus.svg'
import suiteDetailRun from '@/assets/figma/ai-testing-platform/suite-detail-run.svg'
import filterIcon from '@/assets/figma/ai-testing-platform/filter-icon.svg'
import filterChevron from '@/assets/figma/ai-testing-platform/filter-chevron.svg'
import filterSearch from '@/assets/figma/ai-testing-platform/filter-search.svg'
import modalTagsIcon from '@/assets/figma/ai-testing-platform/modal-tags-icon.svg'
import navSuite from '@/assets/figma/ai-testing-platform/nav-suite.svg'
import apiRowRemove from '@/assets/figma/ai-testing-platform/api-row-remove-1.svg'
import CasesTable, { type Row } from '@/components/figma/ai-testing-platform/CasesTable.vue'
import CreateCaseModal from '@/components/figma/ai-testing-platform/CreateCaseModal.vue'
import EditCaseModal from '@/components/figma/ai-testing-platform/EditCaseModal.vue'
import AiGenerateCaseModal from '@/components/figma/ai-testing-platform/AiGenerateCaseModal.vue'
import BatchRunModal from '@/components/figma/ai-testing-platform/BatchRunModal.vue'
import TestcaseBindingsModal from '@/components/figma/ai-testing-platform/TestcaseBindingsModal.vue'
import type { BatchRunCaseRow } from '@/components/figma/ai-testing-platform/BatchRunCaseBindingTable.vue'
import { fetchBindingsByTestcaseIds, fetchRunCaseRuns, runFromTestcases } from '@/lib/aiTestingPlatformApi'

const route = useRoute()
const isCreateCaseOpen = ref(false)
const isAiGenerateOpen = ref(false)
const isEditCaseOpen = ref(false)
const editingCaseId = ref<string | null>(null)
const isBatchRunOpen = ref(false)
const isLoadingCases = ref(false)
const searchQuery = ref('')
const rows = ref<Row[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const selectedCaseIds = ref<string[]>([])
const currentUserId = ref('')
const currentUserName = ref('我')
const ownerOptions = ref<Array<{ id: string; username: string }>>([])
const ownerOptionsProjectId = ref('')
const bindingCountByCaseId = ref<Record<string, number>>({})
const bindingCountRequestSeq = ref(0)
const isBindingsModalOpen = ref(false)
const bindingsModalCaseId = ref('')
const bindingsModalCaseTitle = ref('')

type ApiResponse<T> = {
  code?: number
  message?: string
  data?: T
}

type PageData<T> = {
  page: number
  pageSize: number
  total: number
  items: T[]
}

type CurrentUserData = {
  userId: string
  username?: string | null
  name?: string | null
}

type TestCaseListItem = {
  id: string
  title: string
  version: string
  type: Row['type']
  priority: Row['priority']
  status: 'DRAFT' | 'REVIEWED' | 'DEPRECATED'
  lastRun?: 'QUEUED' | 'RUNNING' | 'PASSED' | 'FAILED' | 'SKIPPED' | null
  updatedAt: number
  tags: string[]
  ownerId?: string | null
}

type TestCaseDetail = {
  id: string
  projectId: string
  title: string
  version: string
  type: TestCaseListItem['type']
  priority: TestCaseListItem['priority']
  status: TestCaseListItem['status']
  tags: string[]
  ownerId?: string | null
  contentMd: string
}

type CreateCasePayload = {
  title: string
  type: TestCaseListItem['type']
  priority: TestCaseListItem['priority']
  status: TestCaseListItem['status']
  tags: string[]
  contentMd: string
  ownerId: string
}

type EditCasePayload = {
  title: string
  type: TestCaseListItem['type']
  priority: TestCaseListItem['priority']
  status: TestCaseListItem['status']
  tags: string[]
  ownerId: string
}

const statusLabelMap: Record<TestCaseListItem['status'], Row['status']> = {
  DRAFT: '草稿',
  REVIEWED: '已评审',
  DEPRECATED: '已弃用'
}

const caseLastRunLabelMap: Record<NonNullable<TestCaseListItem['lastRun']>, Row['lastRun']> = {
  QUEUED: '-',
  RUNNING: '-',
  PASSED: '通过',
  FAILED: '失败',
  SKIPPED: '跳过'
}

const resolveApiBaseUrl = () => {
  const envBase = String(import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!envBase) return ''
  return envBase.endsWith('/') ? envBase.slice(0, -1) : envBase
}

const resolveAuthHeader = () => {
  const accessToken = localStorage.getItem('accessToken')
  if (!accessToken) {
    throw new Error('登录状态已失效，请重新登录')
  }
  return `Bearer ${accessToken}`
}

const resolveOwnerDisplayName = (ownerId?: string | null) => {
  if (!ownerId) return '-'
  const fromOptions = ownerOptions.value.find((item) => item.id === ownerId)
  if (fromOptions) {
    return fromOptions.username
  }
  if (ownerId === currentUserId.value) {
    return currentUserName.value
  }
  return ownerId.slice(0, 8)
}

const resolveLastRunLabel = (lastRun?: TestCaseListItem['lastRun']) => {
  if (!lastRun) return '-'
  return caseLastRunLabelMap[lastRun] || '-'
}

function showToast(message: string, type: 'success' | 'error' = 'success') {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, type } }))
}

const formatDateTime = (timestamp: number) => {
  if (!Number.isFinite(timestamp) || timestamp <= 0) return '-'
  const date = new Date(timestamp * 1000)
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date)
}

const displayRows = computed(() => {
  if (!selectedPriorities.value.length) return rows.value
  return rows.value.filter((row) => selectedPriorities.value.includes(row.priority))
})

const selectedCount = computed(() => selectedCaseIds.value.length)
const casesCount = computed(() => displayRows.value.length)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const totalCasesLabel = computed(() => (total.value > 0 ? total.value : casesCount.value))

const batchRunRows = computed<BatchRunCaseRow[]>(() => {
  const selected = new Set(selectedCaseIds.value)
  const rowsSelected = displayRows.value.filter((row) => selected.has(row.id))
  return rowsSelected.map((row) => ({
    id: row.id,
    title: row.title,
    bindingId: '',
    method: 'POST',
    priority: row.priority === 'P0' ? 'P0' : 'P1'
  }))
})

const loadCurrentUser = async (authorization: string) => {
  const meResponse = await fetch(`${resolveApiBaseUrl()}/api/auth/me`, {
    method: 'GET',
    headers: {
      Authorization: authorization
    }
  })
  const mePayload = await meResponse.json() as ApiResponse<CurrentUserData>
  if (!meResponse.ok || mePayload.code !== 0 || !mePayload.data?.userId) {
    throw new Error(mePayload.message || '获取当前用户信息失败')
  }
  currentUserId.value = mePayload.data.userId
  currentUserName.value = mePayload.data.username || mePayload.data.name || currentUserName.value
}

const loadOwnerOptions = async (authorization: string, projectId: string) => {
  if (ownerOptionsProjectId.value === projectId && ownerOptions.value.length) {
    return
  }
  const response = await fetch(`${resolveApiBaseUrl()}/api/testcases/owners?projectId=${encodeURIComponent(projectId)}`, {
    method: 'GET',
    headers: {
      Authorization: authorization
    }
  })
  const payload = await response.json() as ApiResponse<Array<{ id: string; username: string }>>
  if (!response.ok || payload.code !== 0 || !payload.data) {
    throw new Error(payload.message || '获取维护人列表失败')
  }
  ownerOptions.value = payload.data
  ownerOptionsProjectId.value = projectId
}

const loadCases = async () => {
  const projectId = String(route.params.projectId || '').trim()
  if (!projectId) {
    rows.value = []
    total.value = 0
    return
  }

  isLoadingCases.value = true
  try {
    const authorization = resolveAuthHeader()
    if (!currentUserId.value) {
      await loadCurrentUser(authorization)
    }
    await loadOwnerOptions(authorization, projectId)
    const query = new URLSearchParams({
      projectId,
      page: String(page.value),
      pageSize: String(pageSize)
    })
    if (searchQuery.value.trim()) {
      query.set('title', searchQuery.value.trim())
    }
    if (selectedTypes.value.length) {
      query.set('type', selectedTypes.value[0])
    }
    if (selectedStatuses.value.length) {
      const statusParam = selectedStatuses.value[0] === '草稿'
        ? 'DRAFT'
        : selectedStatuses.value[0] === '已评审'
          ? 'REVIEWED'
          : 'DEPRECATED'
      query.set('status', statusParam)
    }

    const response = await fetch(`${resolveApiBaseUrl()}/api/testcases?${query.toString()}`, {
      method: 'GET',
      headers: {
        Authorization: authorization
      }
    })
    const payload = await response.json() as ApiResponse<PageData<TestCaseListItem>>
    if (!response.ok || payload.code !== 0 || !payload.data) {
      throw new Error(payload.message || '获取用例列表失败，请稍后重试')
    }

    const items = payload.data.items
    total.value = payload.data.total
    rows.value = items.map((item) => ({
      id: item.id,
      title: item.title,
      type: item.type,
      priority: item.priority,
      status: statusLabelMap[item.status],
      feature: item.tags?.[0] || '-',
      story: '-',
      callUrl: '-',
      bindingConfig: `${bindingCountByCaseId.value[item.id] ?? 0}个绑定`,
      owner: resolveOwnerDisplayName(item.ownerId),
      lastRun: resolveLastRunLabel(item.lastRun),
      updatedAt: formatDateTime(item.updatedAt)
    }))
    await loadBindingCounts(items.map((i) => i.id))
    selectedCaseIds.value = []
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '获取用例列表失败，请稍后重试'
    window.alert(errorMessage)
  } finally {
    isLoadingCases.value = false
  }
}

async function loadBindingCounts(caseIds: string[]) {
  const ids = Array.isArray(caseIds) ? caseIds.map((v) => String(v || '').trim()).filter(Boolean) : []
  if (!ids.length) return
  const seq = ++bindingCountRequestSeq.value
  try {
    const map = await fetchBindingsByTestcaseIds(ids)
    if (seq !== bindingCountRequestSeq.value) return
    bindingCountByCaseId.value = Object.keys(map).reduce<Record<string, number>>((acc, id) => {
      const list = map[id]
      acc[id] = Array.isArray(list) ? list.length : 0
      return acc
    }, {})
    rows.value = rows.value.map((row) => ({
      ...row,
      bindingConfig: `${bindingCountByCaseId.value[row.id] ?? 0}个绑定`
    }))
  } catch {
  }
}

function openBindingsModal(payload: { id: string; title: string }) {
  bindingsModalCaseId.value = payload.id
  bindingsModalCaseTitle.value = payload.title
  isBindingsModalOpen.value = true
}

function closeBindingsModal() {
  isBindingsModalOpen.value = false
  bindingsModalCaseId.value = ''
  bindingsModalCaseTitle.value = ''
}

function refreshBindingCounts() {
  const ids = displayRows.value.map((r) => r.id)
  void loadBindingCounts(ids)
}

const loadCaseDetail = async (id: string) => {
  const authorization = resolveAuthHeader()
  const detailResponse = await fetch(`${resolveApiBaseUrl()}/api/testcases/${id}`, {
    method: 'GET',
    headers: {
      Authorization: authorization
    }
  })
  const detailPayload = await detailResponse.json() as ApiResponse<TestCaseDetail>
  if (!detailResponse.ok || detailPayload.code !== 0 || !detailPayload.data) {
    throw new Error(detailPayload.message || '获取用例详情失败，请稍后重试')
  }
  return detailPayload.data
}

function openCreateCase() {
  isCreateCaseOpen.value = true
}

function openAiGenerateCase() {
  isAiGenerateOpen.value = true
}

function clearSelection() {
  selectedCaseIds.value = []
}

function batchExecuteSelected() {
  if (!selectedCount.value) return
  isBatchRunOpen.value = true
}

function bulkTagSelected() {
  if (!selectedCount.value) return
  showToast('批量打标签已触发')
}

function bulkAddToSuiteSelected() {
  if (!selectedCount.value) return
  showToast('批量加入套件已触发')
}

function bulkDeprecateSelected() {
  if (!selectedCount.value) return
  showToast('批量弃用已触发')
}

function closeAiGenerateCase() {
  isAiGenerateOpen.value = false
}

function closeCreateCase() {
  isCreateCaseOpen.value = false
}

function closeBatchRun() {
  isBatchRunOpen.value = false
}

function nextBatchRunStep() {
  showToast('下一步')
}

async function executeBatchRun(payload: { formState: Parameters<typeof runFromTestcases>[0]; idempotencyKey: string }) {
  closeBatchRun()
  try {
    const items = Array.isArray(payload.formState?.items) ? payload.formState.items : []
    if (!items.length) {
      showToast('未选择用例', 'error')
      return
    }
    showToast(`开始执行 ${items.length} 条`)
    const result = await runFromTestcases(payload.formState, payload.idempotencyKey)
    const runId = typeof (result as { runId?: unknown })?.runId === 'string' ? (result as { runId: string }).runId : ''
    showToast(runId ? `已开始执行：${runId}` : '已开始执行')
    if (runId) {
      void warmupRunCaseRuns(runId)
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '开始执行失败，请稍后重试'
    window.alert(errorMessage)
  }
}

async function warmupRunCaseRuns(runId: string) {
  for (let i = 0; i < 3; i += 1) {
    try {
      const caseRuns = await fetchRunCaseRuns(runId, true)
      if (Array.isArray(caseRuns) && caseRuns.length > 0) {
        showToast(`已生成 ${caseRuns.length} 条执行记录`)
        return
      }
    } catch {
      return
    }
    await new Promise((resolve) => window.setTimeout(resolve, 800))
  }
}

function startAiGenerateCase() {
}

async function saveCreateCase(payload: CreateCasePayload) {
  const projectId = String(route.params.projectId || '').trim()
  if (!projectId) return
  try {
    const authorization = resolveAuthHeader()
    const response = await fetch(`${resolveApiBaseUrl()}/api/testcases`, {
      method: 'POST',
      headers: {
        Authorization: authorization,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        projectId,
        title: payload.title,
        type: payload.type,
        priority: payload.priority,
        status: payload.status,
        tags: payload.tags,
        contentMd: payload.contentMd,
        ownerId: payload.ownerId || null
      })
    })
    const result = await response.json() as ApiResponse<TestCaseListItem>
    if (!response.ok || result.code !== 0) {
      throw new Error(result.message || '新增用例失败，请稍后重试')
    }
    closeCreateCase()
    page.value = 1
    await loadCases()
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '新增用例失败，请稍后重试'
    window.alert(errorMessage)
  }
}

const editingCaseDetail = ref<TestCaseDetail | null>(null)

async function openEditCase(index: number) {
  const target = displayRows.value[index]
  if (!target) return
  try {
    editingCaseId.value = target.id
    editingCaseDetail.value = await loadCaseDetail(target.id)
    isEditCaseOpen.value = true
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '获取用例详情失败，请稍后重试'
    window.alert(errorMessage)
    editingCaseId.value = null
    editingCaseDetail.value = null
  }
}

function closeEditCase() {
  isEditCaseOpen.value = false
  editingCaseId.value = null
  editingCaseDetail.value = null
}

async function deleteCase(index: number) {
  const target = displayRows.value[index]
  if (!target) return
  if (!window.confirm(`确认删除用例「${target.title}」吗？`)) return
  try {
    const authorization = resolveAuthHeader()
    const response = await fetch(`${resolveApiBaseUrl()}/api/testcases/${target.id}`, {
      method: 'DELETE',
      headers: {
        Authorization: authorization
      }
    })
    const payload = await response.json() as ApiResponse<Record<string, never>>
    if (!response.ok || payload.code !== 0) {
      throw new Error(payload.message || '删除用例失败，请稍后重试')
    }
    if (displayRows.value.length === 1 && page.value > 1) {
      page.value -= 1
    }
    await loadCases()
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '删除用例失败，请稍后重试'
    window.alert(errorMessage)
  }
}

async function saveEditCase(payload: EditCasePayload) {
  if (!editingCaseId.value || !editingCaseDetail.value) return
  const title = payload.title.trim()
  if (!title) {
    window.alert('请输入用例标题')
    return
  }
  try {
    const authorization = resolveAuthHeader()
    const query = new URLSearchParams({ id: editingCaseId.value })
    const ownerId = payload.ownerId.trim()
    const response = await fetch(`${resolveApiBaseUrl()}/api/testcases?${query.toString()}`, {
      method: 'PUT',
      headers: {
        Authorization: authorization,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        projectId: editingCaseDetail.value.projectId,
        title,
        type: payload.type,
        priority: payload.priority,
        status: payload.status,
        tags: payload.tags,
        contentMd: editingCaseDetail.value.contentMd,
        ownerId: ownerId || null
      })
    })
    const result = await response.json() as ApiResponse<TestCaseDetail>
    if (!response.ok || result.code !== 0) {
      throw new Error(result.message || '编辑用例失败，请稍后重试')
    }
    closeEditCase()
    await loadCases()
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '编辑用例失败，请稍后重试'
    window.alert(errorMessage)
  }
}
const editingInitialData = computed(() => {
  if (!editingCaseDetail.value) {
    return {
      title: '',
      type: 'API' as const,
      priority: 'P0' as const,
      status: 'DRAFT' as const,
      tags: [] as string[],
      ownerId: ''
    }
  }
  return {
    title: editingCaseDetail.value.title,
    type: editingCaseDetail.value.type,
    priority: editingCaseDetail.value.priority,
    status: editingCaseDetail.value.status,
    tags: editingCaseDetail.value.tags || [],
    ownerId: editingCaseDetail.value.ownerId || ''
  }
})

const isFilterOpen = ref(false)
const filterAreaRef = ref<HTMLElement | null>(null)

const typeOptions = ['API', 'UI', 'PERF', 'MIX'] as const
const statusOptions = ['草稿', '已评审', '已弃用'] as const
const priorityOptions = ['P0', 'P1', 'P2', 'P3'] as const

const selectedTypes = ref<string[]>([])
const selectedStatuses = ref<string[]>([])
const selectedPriorities = ref<string[]>([])

const selectedFiltersCount = computed(() => selectedTypes.value.length + selectedStatuses.value.length + selectedPriorities.value.length)

function toggleValue(list: string[], value: string) {
  const idx = list.indexOf(value)
  if (idx >= 0) list.splice(idx, 1)
  else list.push(value)
}

function pillClass(isActive: boolean) {
  if (isActive) return 'bg-[#EFF6FF] border-[#2B7FFF] text-[#155DFC]'
  return 'bg-white border-black/10 text-[#717182]'
}

function toggleFilter() {
  isFilterOpen.value = !isFilterOpen.value
}

function closeFilter() {
  isFilterOpen.value = false
}

function onWindowClick(e: MouseEvent) {
  const el = filterAreaRef.value
  if (!el) return
  if (!el.contains(e.target as Node)) closeFilter()
}

onMounted(() => {
  window.addEventListener('click', onWindowClick)
  void loadCases()
})

onBeforeUnmount(() => {
  window.removeEventListener('click', onWindowClick)
})

let searchTimer = 0
watch(searchQuery, () => {
  page.value = 1
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    void loadCases()
  }, 300)
})

watch([selectedTypes, selectedStatuses], () => {
  page.value = 1
  void loadCases()
}, { deep: true })

watch(() => route.params.projectId, () => {
  page.value = 1
  ownerOptions.value = []
  ownerOptionsProjectId.value = ''
  void loadCases()
})
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)] md:pr-[16.67px]">
    <div class="flex flex-col gap-[16px] px-[16px] pt-[16px] md:px-[24px] md:pt-[24px]">
      <div class="flex flex-col gap-[12px] md:flex-row md:items-center md:justify-between md:gap-0">
        <div class="flex flex-col gap-[2px]">
          <div class="text-[13px] font-normal leading-[18px] text-[#0A0A0A]">用例管理</div>
          <div class="text-[14px] leading-[20px] text-[#717182]">
            共 {{ totalCasesLabel }} 条用例
            <span v-if="selectedCount > 0"> · 已选 {{ selectedCount }} 条</span>
          </div>
        </div>

        <div class="flex h-[32px] items-center gap-[8px]">
          <button
            type="button"
            class="relative h-[32px] w-[126.51px] rounded-[10px] border border-[#7BF1A8] bg-[#F0FDF4]"
            :class="selectedCount > 0 ? '' : 'opacity-30 pointer-events-none'"
            @click="batchExecuteSelected"
          >
            <img :src="suiteDetailRun" alt="" class="absolute left-[12.67px] top-[9px] h-[14px] w-[14px]" />
            <span class="absolute left-[32.67px] top-[6.33px] text-[14px] font-medium leading-[20px] text-[#00A63E]">
              批量执行
            </span>
            <span
              v-if="selectedCount > 0"
              class="absolute right-[10px] top-[6px] flex h-[20px] min-w-[20px] items-center justify-center rounded-full bg-[#DCFCE7] px-[6px] text-[12px] font-medium leading-[16px] text-[#00A63E]"
            >
              {{ selectedCount }}
            </span>
          </button>
          <button
            type="button"
            class="relative h-[32px] w-[91.45px] rounded-[10px] border border-[#BEDBFF] bg-white"
            @click="openAiGenerateCase"
          >
            <img :src="btnAiGenerate" alt="" class="absolute left-[12.67px] top-[9px] h-[14px] w-[14px]" />
            <span class="absolute left-[32.67px] top-[6.33px] text-[14px] font-medium leading-[20px] text-[#155DFC]">
              AI 生成
            </span>
          </button>
          <button type="button" class="relative h-[32px] w-[100px] rounded-[10px] bg-[#155DFC]" @click="openCreateCase">
            <img :src="btnPlus" alt="" class="absolute left-[12px] top-[9px] h-[14px] w-[14px]" />
            <span class="absolute left-[32px] top-[6.33px] text-[14px] font-medium leading-[20px] text-white">
              新建用例
            </span>
          </button>
        </div>
      </div>

      <div ref="filterAreaRef" class="w-full overflow-hidden rounded-[14px] border border-black/10 bg-white">
        <div class="flex w-full items-center justify-between gap-[12px] px-[16.67px] py-[16.67px]">
          <div class="relative h-[32px] w-[240px] shrink-0 rounded-[10px] bg-[#ECECF0] md:w-[260px]">
            <img :src="filterSearch" alt="" class="absolute left-[12px] top-[9px] h-[14px] w-[14px]" />
            <input
              v-model="searchQuery"
              class="h-full w-full rounded-[10px] bg-transparent pl-[32px] pr-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none placeholder:text-[#0A0A0A]"
              placeholder="搜索用例标题..."
              type="text"
            />
          </div>

          <button
            type="button"
            class="relative h-[32px] w-[90.33px] shrink-0 rounded-[10px] border border-black/10 bg-white"
            @click.stop="toggleFilter"
          >
            <img :src="filterIcon" alt="" class="absolute left-[12.67px] top-[9.5px] h-[13px] w-[13px]" />
            <span class="absolute left-[31.67px] top-[6.33px] text-[14px] font-medium leading-[20px] text-[#717182]">筛选</span>
            <span
              v-if="selectedFiltersCount > 0"
              class="absolute left-[54px] top-[2px] flex h-[16px] min-w-[16px] items-center justify-center rounded-full bg-[#155DFC] px-[4px] text-[12px] font-medium leading-[16px] text-white"
            >
              {{ selectedFiltersCount }}
            </span>
            <img
              :src="filterChevron"
              alt=""
              class="absolute left-[65.67px] top-[10px] h-[12px] w-[12px] transition-transform"
              :class="isFilterOpen ? 'rotate-180' : ''"
            />
          </button>
        </div>

        <div v-if="isFilterOpen" class="border-t border-black/10 px-[16.67px] pt-[12.67px] pb-[16px]">
          <div class="flex flex-col gap-[12.67px] md:flex-row md:items-start md:gap-[16px]">
            <div class="flex flex-col gap-[8px] md:w-[195.1px]">
              <div class="text-[12px] font-medium leading-[16px] text-[#717182]">类型</div>
              <div class="flex flex-wrap gap-[6px]">
                <button
                  v-for="t in typeOptions"
                  :key="t"
                  type="button"
                  class="h-[25.33px] rounded-[8px] border px-[8.67px] text-[12px] font-medium leading-[16px]"
                  :class="pillClass(selectedTypes.includes(t))"
                  @click.stop="toggleValue(selectedTypes, t)"
                >
                  {{ t }}
                </button>
              </div>
            </div>

            <div class="flex flex-col gap-[8px] md:w-[195.11px]">
              <div class="text-[12px] font-medium leading-[16px] text-[#717182]">状态</div>
              <div class="flex flex-wrap gap-[6px]">
                <button
                  v-for="s in statusOptions"
                  :key="s"
                  type="button"
                  class="h-[25.33px] rounded-[8px] border px-[8.67px] text-[12px] font-medium leading-[16px]"
                  :class="pillClass(selectedStatuses.includes(s))"
                  @click.stop="toggleValue(selectedStatuses, s)"
                >
                  {{ s }}
                </button>
              </div>
            </div>

            <div class="flex flex-col gap-[8px] md:w-[195.1px]">
              <div class="text-[12px] font-medium leading-[16px] text-[#717182]">优先级</div>
              <div class="flex flex-wrap gap-[6px]">
                <button
                  v-for="p in priorityOptions"
                  :key="p"
                  type="button"
                  class="h-[25.33px] rounded-[8px] border px-[8.67px] text-[12px] font-medium leading-[16px]"
                  :class="pillClass(selectedPriorities.includes(p))"
                  @click.stop="toggleValue(selectedPriorities, p)"
                >
                  {{ p }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        v-if="selectedCount > 0"
        class="flex h-[37.33px] w-full items-center justify-between rounded-[10px] border border-[#BEDBFF] bg-[#EFF6FF] px-[16.67px]"
      >
        <div class="text-[14px] leading-[20px] text-[#1447E6]">已选 {{ selectedCount }} 条</div>

        <div class="flex items-center gap-[16px]">
          <button type="button" class="flex items-center gap-[6px]" @click="bulkTagSelected">
            <img :src="modalTagsIcon" alt="" class="h-[14px] w-[14px]" />
            <span class="text-[12px] font-medium leading-[16px] text-[#2B7FFF]">打标签</span>
          </button>
          <button type="button" class="flex items-center gap-[6px]" @click="bulkAddToSuiteSelected">
            <img :src="navSuite" alt="" class="h-[14px] w-[14px]" />
            <span class="text-[12px] font-medium leading-[16px] text-[#2B7FFF]">加入套件</span>
          </button>
          <button type="button" class="flex items-center gap-[6px]" @click="bulkDeprecateSelected">
            <img :src="apiRowRemove" alt="" class="h-[14px] w-[14px]" />
            <span class="text-[12px] font-medium leading-[16px] text-[#FB2C36]">弃用</span>
          </button>
        </div>

        <button type="button" class="text-[12px] font-medium leading-[16px] text-[#2B7FFF]" @click="clearSelection">
          取消
        </button>
      </div>

      <div class="w-full rounded-[14px] border border-black/10 bg-white p-[0.67px]">
        <CasesTable
          v-model:selectedIds="selectedCaseIds"
          :rows="displayRows"
          @delete="deleteCase"
          @edit="openEditCase"
          @manage-bindings="openBindingsModal"
        />
      </div>

      <div class="flex items-center justify-between">
        <div class="text-[14px] leading-[20px] text-[#717182]">
          共 {{ totalCasesLabel }} 条
          <span v-if="isLoadingCases"> · 加载中...</span>
          <span v-else> · 第 {{ page }}/{{ totalPages }} 页</span>
        </div>
        <div class="flex h-[28px] w-[92px] items-center gap-[4px]">
          <button type="button" class="relative h-[28px] w-[28px] rounded-[4px] opacity-30">
            <span class="absolute left-[11.93px] top-[6px] text-[12px] font-medium leading-[16px] text-[#717182]">‹</span>
          </button>
          <button type="button" class="relative h-[28px] w-[28px] rounded-[4px] bg-[#155DFC]">
            <span class="absolute left-[11.48px] top-[6px] text-[12px] font-medium leading-[16px] text-white">1</span>
          </button>
          <button type="button" class="relative h-[28px] w-[28px] rounded-[4px] opacity-30">
            <span class="absolute left-[11.93px] top-[6px] text-[12px] font-medium leading-[16px] text-[#717182]">›</span>
          </button>
        </div>
      </div>
    </div>
  </div>

  <CreateCaseModal
    :is-open="isCreateCaseOpen"
    :default-owner-id="currentUserId"
    :owner-options="ownerOptions"
    @close="closeCreateCase"
    @save="saveCreateCase"
  />
  <EditCaseModal
    :is-open="isEditCaseOpen"
    :initial-data="editingInitialData"
    :owner-options="ownerOptions"
    @close="closeEditCase"
    @save="saveEditCase"
  />
  <AiGenerateCaseModal
    :is-open="isAiGenerateOpen"
    @close="closeAiGenerateCase"
    @start="startAiGenerateCase"
  />
  <BatchRunModal
    :is-open="isBatchRunOpen"
    :selected-count="selectedCount"
    :project-id="String(route.params.projectId || '').trim()"
    :rows="batchRunRows"
    @close="closeBatchRun"
    @next="nextBatchRunStep"
    @execute="executeBatchRun"
  />
  <TestcaseBindingsModal
    :is-open="isBindingsModalOpen"
    :project-id="String(route.params.projectId || '').trim()"
    :testcase-id="bindingsModalCaseId"
    :testcase-title="bindingsModalCaseTitle"
    @close="closeBindingsModal"
    @changed="refreshBindingCounts"
  />
</template>
