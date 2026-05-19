<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import btnAiGenerate from '@/assets/figma/ai-testing-platform/btn-ai-generate.svg'
import btnPlus from '@/assets/figma/ai-testing-platform/btn-plus.svg'
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
import UploadCasesModal from '@/components/figma/ai-testing-platform/UploadCasesModal.vue'
import BatchRunDrawer from '@/components/figma/ai-testing-platform/BatchRunDrawer.vue'
import { buildRunPayloadDirect, fetchProjectEnvironments, fetchRunCaseRuns, runFromTestcasesHttp, type BatchRunDirectFormItem, type BatchRunDirectFormState } from '@/lib/aiTestingPlatformApi'

const route = useRoute()
const isCreateCaseOpen = ref(false)
const isAiGenerateOpen = ref(false)
const isEditCaseOpen = ref(false)
const isUploadCasesOpen = ref(false)
const editingCaseId = ref<string | null>(null)
const isLoadingCases = ref(false)
const searchQuery = ref('')
const rows = ref<Row[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const selectedCaseIds = ref<string[]>([])
const selectedCaseMap = ref<Record<string, Row>>({})
const currentUserId = ref('')
const currentUserName = ref('我')
const ownerOptions = ref<Array<{ id: string; username: string }>>([])
const ownerOptionsProjectId = ref('')
const isBatchRunDrawerOpen = ref(false)
const batchRunDrawerState = ref<'closed' | 'preview' | 'executing' | 'completed'>('closed')
const batchRunRunId = ref('')
const batchRunEnvId = ref('')
const batchRunEnvironments = ref<Array<{ id: string; name: string; baseUrl: string }>>([])
const isLoadingBatchRunEnvironments = ref(false)
let batchRunPollingTimer = 0

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
  testCaseId?: string | null
  expectedStatusCode?: number | null
  preconditions?: string | null
  postconditions?: string | null
  title: string
  version: string
  type: Row['type']
  priority: Row['priority']
  status: 'DRAFT' | 'REVIEWED' | 'DEPRECATED' | 'ARCHIVED'
  lastRun?: 'QUEUED' | 'RUNNING' | 'PASSED' | 'FAILED' | 'SKIPPED' | null
  updatedAt: number
  tags: string[]
  feature?: string | null
  apiMethod?: string | null
  apiUrl?: string | null
  apiParams?: Record<string, unknown>
  apiHeaders?: Record<string, string>
  expectedResult?: string | null
  ownerId?: string | null
}

type TestCaseDetail = {
  id: string
  projectId: string
  testCaseId?: string | null
  expectedStatusCode?: number | null
  preconditions?: string | null
  postconditions?: string | null
  title: string
  version: string
  type: TestCaseListItem['type']
  priority: TestCaseListItem['priority']
  status: 'DRAFT' | 'REVIEWED' | 'DEPRECATED' | 'ARCHIVED'
  tags: string[]
  ownerId?: string | null
  contentMd: string
  feature?: string | null
  apiMethod?: string | null
  apiUrl?: string | null
  apiParams?: Record<string, unknown>
  apiHeaders?: Record<string, string>
  expectedResult?: string | null
}

type CreateCasePayload = {
  testCaseId: string
  expectedStatusCode: number | null
  preconditions: string
  postconditions: string
  title: string
  type: TestCaseListItem['type']
  priority: TestCaseListItem['priority']
  status: TestCaseListItem['status']
  tags: string[]
  contentMd: string
  ownerId: string
  feature?: string
  apiMethod?: string
  apiUrl?: string
  apiParams: Record<string, unknown>
  apiHeaders: Record<string, string>
  expectedResult: string
}

type EditCasePayload = {
  testCaseId: string
  expectedStatusCode: number | null
  preconditions: string
  postconditions: string
  feature: string
  title: string
  apiMethod: string
  apiUrl: string
  apiParams: Record<string, unknown>
  apiHeaders: Record<string, string>
  expectedResult: string
  type: TestCaseListItem['type']
  priority: TestCaseListItem['priority']
  status: TestCaseListItem['status']
  tags: string[]
  contentMd: string
  ownerId: string
}

const statusLabelMap: Record<TestCaseListItem['status'], Row['status']> = {
  DRAFT: '草稿',
  REVIEWED: '已评审',
  DEPRECATED: '已弃用',
  ARCHIVED: '已归档'
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

function openUploadCases() {
  isUploadCasesOpen.value = true
}

function closeUploadCases() {
  isUploadCasesOpen.value = false
}

function handleImportedCases(data: { importedCount: number; failedCount: number }) {
  const imported = Number(data.importedCount || 0)
  const failed = Number(data.failedCount || 0)
  if (imported > 0 && failed === 0) {
    showToast(`成功导入 ${imported} 条用例`, 'success')
  } else if (imported > 0 && failed > 0) {
    showToast(`已导入 ${imported} 条，失败 ${failed} 条`, 'error')
  } else {
    showToast('导入失败', 'error')
  }
  page.value = 1
  clearSelection()
  void loadCases()
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
const selectedRows = computed(() => {
  if (!selectedCaseIds.value.length) return []
  return selectedCaseIds.value
    .map((id) => selectedCaseMap.value[id])
    .filter((row): row is Row => Boolean(row))
})

type PaginationItem = number | '...'

const paginationItems = computed<PaginationItem[]>(() => {
  const totalValue = totalPages.value
  const current = page.value
  if (totalValue <= 7) {
    return Array.from({ length: totalValue }, (_, idx) => idx + 1)
  }

  const items: PaginationItem[] = [1]
  if (current > 4) items.push('...')

  const start = current <= 4 ? 2 : Math.max(2, Math.min(totalValue - 4, current - 1))
  const end = current >= totalValue - 3 ? totalValue - 1 : Math.min(totalValue - 1, Math.max(5, current + 1))
  for (let p = start; p <= end; p += 1) {
    items.push(p)
  }

  if (current < totalValue - 3) items.push('...')
  items.push(totalValue)
  return items
})

function goToPage(nextPage: number) {
  const nextValue = Math.max(1, Math.min(totalPages.value, Math.floor(nextPage)))
  if (nextValue === page.value) return
  page.value = nextValue
  void loadCases()
}

const canGoPrev = computed(() => page.value > 1 && !isLoadingCases.value)
const canGoNext = computed(() => page.value < totalPages.value && !isLoadingCases.value)

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
          : selectedStatuses.value[0] === '已归档'
            ? 'ARCHIVED'
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
      testCaseId: item.testCaseId || '-',
      module: item.feature || item.tags?.[0] || '-',
      title: item.title,
      type: item.type,
      priority: item.priority,
      status: statusLabelMap[item.status],
      interfaceUrl: item.apiUrl || '-',
      method: String(item.apiMethod || '').toUpperCase() || '-',
      apiParams: item.apiParams || null,
      expectedResult: item.expectedResult || null,
      owner: resolveOwnerDisplayName(item.ownerId),
      lastRun: resolveLastRunLabel(item.lastRun),
      updatedAt: formatDateTime(item.updatedAt)
    }))
    if (selectedCaseIds.value.length) {
      const selectedSet = new Set(selectedCaseIds.value)
      const nextMap: Record<string, Row> = { ...selectedCaseMap.value }
      for (const row of rows.value) {
        if (selectedSet.has(row.id)) nextMap[row.id] = row
      }
      selectedCaseMap.value = nextMap
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '获取用例列表失败，请稍后重试'
    showToast(errorMessage, 'error')
  } finally {
    isLoadingCases.value = false
  }
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
  selectedCaseMap.value = {}
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

function clearBatchRunPolling() {
  window.clearTimeout(batchRunPollingTimer)
  batchRunPollingTimer = 0
}

function openBatchRunDrawer() {
  if (!selectedCount.value) return
  batchRunRunId.value = ''
  batchRunDrawerState.value = 'preview'
  isBatchRunDrawerOpen.value = true
  void loadBatchRunEnvironments()
}

function closeBatchRunDrawer() {
  isBatchRunDrawerOpen.value = false
  if (batchRunDrawerState.value === 'preview' || batchRunDrawerState.value === 'closed') {
    clearBatchRunPolling()
    batchRunRunId.value = ''
    batchRunDrawerState.value = 'closed'
  }
}

async function loadBatchRunEnvironments() {
  const projectId = String(route.params.projectId || '').trim()
  if (!projectId) return
  isLoadingBatchRunEnvironments.value = true
  try {
    const envs = await fetchProjectEnvironments(projectId)
    const options = Array.isArray(envs)
      ? envs
          .map((env) => {
            if (!env || typeof env !== 'object') return null
            const data = env as { id?: unknown; name?: unknown; baseUrl?: unknown }
            const id = String(data.id || '').trim()
            const name = String(data.name || '').trim()
            const baseUrl = String(data.baseUrl || '').trim()
            if (!id || !name || !baseUrl) return null
            return { id, name, baseUrl }
          })
          .filter((v): v is { id: string; name: string; baseUrl: string } => Boolean(v))
      : []
    batchRunEnvironments.value = options
    if (!batchRunEnvId.value || !options.some((opt) => opt.id === batchRunEnvId.value)) {
      batchRunEnvId.value = options[0]?.id || ''
    }
  } catch (error) {
    batchRunEnvironments.value = []
    batchRunEnvId.value = ''
    showToast(error instanceof Error ? error.message : '加载执行环境失败', 'error')
  } finally {
    isLoadingBatchRunEnvironments.value = false
  }
}

function extractRunId(payload: unknown) {
  if (!payload || typeof payload !== 'object') return ''
  const data = payload as { runId?: unknown; id?: unknown }
  if (typeof data.runId === 'string' && data.runId.trim()) return data.runId.trim()
  if (typeof data.id === 'string' && data.id.trim()) return data.id.trim()
  return ''
}

function scheduleBatchRunStatusPoll(runId: string) {
  clearBatchRunPolling()
  const poll = async () => {
    if (batchRunRunId.value !== runId) return
    try {
      const caseRuns = await fetchRunCaseRuns(runId)
      if (!caseRuns.length) {
        batchRunPollingTimer = window.setTimeout(() => {
          void poll()
        }, 2000)
        return
      }
      const terminalStatuses = new Set(['PASSED', 'FAILED', 'SKIPPED', 'CANCELED', 'CANCELLED'])
      const isCompleted = caseRuns.every((item) => terminalStatuses.has(String(item.status || '').toUpperCase()))
      if (isCompleted) {
        batchRunDrawerState.value = 'completed'
        showToast('用例执行完成，可以查看报告')
        clearBatchRunPolling()
        return
      }
      batchRunPollingTimer = window.setTimeout(() => {
        void poll()
      }, 2000)
    } catch {
      batchRunPollingTimer = window.setTimeout(() => {
        void poll()
      }, 2000)
    }
  }
  void poll()
}

async function executeBatchRunFromDrawer(options?: { onStart?: () => void }) {
  const projectId = String(route.params.projectId || '').trim()
  if (!projectId) {
    showToast('缺少项目 ID', 'error')
    return false
  }
  if (!selectedRows.value.length) {
    showToast('请先勾选需要执行的用例', 'error')
    return false
  }
  const envId = String(batchRunEnvId.value || '').trim()
  if (!envId) {
    showToast(isLoadingBatchRunEnvironments.value ? '执行环境加载中，请稍后重试' : '请选择执行环境', 'error')
    return false
  }
  batchRunDrawerState.value = 'executing'
  batchRunRunId.value = ''
  clearBatchRunPolling()
  try {
    const items: BatchRunDirectFormItem[] = []
    for (const row of selectedRows.value) {
      const item: BatchRunDirectFormItem = { testcaseId: row.id }
      if (row.apiParams && typeof row.apiParams === 'object' && !Array.isArray(row.apiParams)) {
        item.overrideParams = row.apiParams
      }
      items.push(item)
    }
    const state: BatchRunDirectFormState = {
      projectId,
      envId,
      triggerType: 'MANUAL',
      meta: { source: 'cases_panel_drawer', runnerType: 'PYTEST_ALLURE' },
      concurrency: 5,
      stopOnFailure: false,
      items
    }
    buildRunPayloadDirect(state)
    options?.onStart?.()
    const response = await runFromTestcasesHttp(state, `ik_cases_drawer_${Date.now()}`)
    const runId = extractRunId(response)
    batchRunRunId.value = runId
    if (!runId) {
      throw new Error('批量执行未返回 runId')
    }
    scheduleBatchRunStatusPoll(runId)
    return true
  } catch (error) {
    batchRunDrawerState.value = 'preview'
    const message = error instanceof Error ? error.message : '批量执行失败'
    showToast(message, 'error')
    return false
  }
}

async function handleBatchRunDrawerExecute() {
  let closedByExecute = false
  const started = await executeBatchRunFromDrawer({
    onStart: () => {
      closedByExecute = true
      closeBatchRunDrawer()
    }
  })
  if (!started && closedByExecute) {
    isBatchRunDrawerOpen.value = true
  }
}

function closeAiGenerateCase() {
  isAiGenerateOpen.value = false
}

function closeCreateCase() {
  isCreateCaseOpen.value = false
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
        testCaseId: payload.testCaseId.trim() || null,
        expectedStatusCode: payload.expectedStatusCode ?? null,
        preconditions: payload.preconditions.trim() || null,
        postconditions: payload.postconditions.trim() || null,
        title: payload.title,
        type: payload.type,
        priority: payload.priority,
        status: payload.status,
        tags: payload.tags,
        contentMd: payload.contentMd,
        ownerId: payload.ownerId || null,
        feature: payload.feature || null,
        apiMethod: payload.apiMethod || null,
        apiUrl: payload.apiUrl || null,
        apiParams: payload.apiParams || {},
        apiHeaders: payload.apiHeaders || {},
        expectedResult: payload.expectedResult
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
  if (!window.confirm(`该用例存在执行记录，是否确定删除？\n\n用例名称：${target.title}`)) return
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
    if (selectedCaseIds.value.includes(target.id)) {
      selectedCaseIds.value = selectedCaseIds.value.filter((id) => id !== target.id)
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

async function archiveOrRestoreCase(index: number) {
  const target = displayRows.value[index]
  if (!target) return
  const isArchived = target.status === '已归档'
  const action = isArchived ? 'unarchive' : 'archive'
  const label = isArchived ? '恢复' : '归档'
  if (!window.confirm(`确定要${label}用例 "${target.title}" 吗？`)) return
  try {
    const authorization = resolveAuthHeader()
    const response = await fetch(`${resolveApiBaseUrl()}/api/testcases/${target.id}/${action}`, {
      method: 'POST',
      headers: {
        Authorization: authorization
      }
    })
    const payload = await response.json() as ApiResponse<Record<string, never>>
    if (!response.ok || payload.code !== 0) {
      throw new Error(payload.message || `${label}用例失败，请稍后重试`)
    }
    showToast(`用例已${label}`)
    await loadCases()
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : `${label}用例失败，请稍后重试`
    showToast(errorMessage, 'error')
  }
}

async function saveEditCase(payload: EditCasePayload) {
  if (!editingCaseId.value || !editingCaseDetail.value) return
  const title = payload.title.trim()
  const feature = payload.feature.trim()
  const apiMethod = payload.apiMethod.trim()
  const apiUrl = payload.apiUrl.trim()
  const expectedResult = payload.expectedResult.trim()
  const contentMd = payload.contentMd.trim()
  if (!title) {
    window.alert('请输入用例标题')
    return
  }
  if (!feature) {
    window.alert('请输入功能模块')
    return
  }
  if (!apiMethod) {
    window.alert('请输入调用方式')
    return
  }
  if (!apiUrl) {
    window.alert('请输入interfaceUrl')
    return
  }
  if (!expectedResult) {
    window.alert('请输入预期结果')
    return
  }
  if (!contentMd) {
    window.alert('请输入用例内容')
    return
  }
  try {
    const authorization = resolveAuthHeader()
    const ownerId = payload.ownerId.trim()
    const response = await fetch(`${resolveApiBaseUrl()}/api/testcases/${editingCaseId.value}`, {
      method: 'PUT',
      headers: {
        Authorization: authorization,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        projectId: editingCaseDetail.value.projectId,
        testCaseId: payload.testCaseId.trim() || null,
        expectedStatusCode: payload.expectedStatusCode ?? null,
        preconditions: payload.preconditions.trim() || null,
        postconditions: payload.postconditions.trim() || null,
        title,
        type: payload.type,
        priority: payload.priority,
        status: payload.status,
        tags: payload.tags,
        contentMd,
        ownerId: ownerId || null,
        feature,
        apiMethod,
        apiUrl,
        apiParams: payload.apiParams || {},
        apiHeaders: payload.apiHeaders || {},
        expectedResult
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
      testCaseId: '',
      expectedStatusCode: null,
      preconditions: '',
      postconditions: '',
      feature: '',
      title: '',
      apiMethod: '',
      apiUrl: '',
      apiParams: {} as Record<string, unknown>,
      apiHeaders: {} as Record<string, string>,
      expectedResult: '',
      type: 'API' as const,
      priority: 'P0' as const,
      status: 'DRAFT' as const,
      tags: [] as string[],
      contentMd: '',
      ownerId: ''
    }
  }
  return {
    testCaseId: editingCaseDetail.value.testCaseId || '',
    expectedStatusCode: editingCaseDetail.value.expectedStatusCode ?? null,
    preconditions: editingCaseDetail.value.preconditions || '',
    postconditions: editingCaseDetail.value.postconditions || '',
    feature: editingCaseDetail.value.feature || '',
    title: editingCaseDetail.value.title,
    apiMethod: editingCaseDetail.value.apiMethod || '',
    apiUrl: editingCaseDetail.value.apiUrl || '',
    apiParams: editingCaseDetail.value.apiParams || {},
    apiHeaders: editingCaseDetail.value.apiHeaders || {},
    expectedResult: editingCaseDetail.value.expectedResult || '',
    type: editingCaseDetail.value.type,
    priority: editingCaseDetail.value.priority,
    status: editingCaseDetail.value.status,
    tags: editingCaseDetail.value.tags || [],
    contentMd: editingCaseDetail.value.contentMd || '',
    ownerId: editingCaseDetail.value.ownerId || ''
  }
})

const isFilterOpen = ref(false)
const filterAreaRef = ref<HTMLElement | null>(null)

const typeOptions = ['API', 'UI', 'PERF', 'MIX'] as const
const statusOptions = ['草稿', '已评审', '已弃用', '已归档'] as const
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
  clearBatchRunPolling()
})

watch(selectedCaseIds, (next, prev) => {
  const prevIds = Array.isArray(prev) ? prev : []
  const nextSet = new Set(next)
  const prevSet = new Set(prevIds)

  const nextMap: Record<string, Row> = { ...selectedCaseMap.value }

  for (const id of prevSet) {
    if (!nextSet.has(id)) delete nextMap[id]
  }

  for (const id of nextSet) {
    if (prevSet.has(id)) continue
    const row = rows.value.find((item) => item.id === id)
    if (row) nextMap[id] = row
  }

  selectedCaseMap.value = nextMap
})

let searchTimer = 0
watch(searchQuery, () => {
  page.value = 1
  clearSelection()
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    void loadCases()
  }, 300)
})

watch([selectedTypes, selectedStatuses], () => {
  page.value = 1
  clearSelection()
  void loadCases()
}, { deep: true })

watch(() => route.params.projectId, () => {
  page.value = 1
  clearSelection()
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
            class="h-[32px] rounded-[10px] border border-[#BEDBFF] bg-white px-[14px] text-[14px] font-medium leading-[20px] text-[#155DFC]"
            @click="openUploadCases"
          >
            上传用例
          </button>
          <button
            type="button"
            class="h-[32px] rounded-[10px] border border-[#BEDBFF] bg-white px-[14px] text-[14px] font-medium leading-[20px] text-[#155DFC] disabled:cursor-not-allowed disabled:border-black/10 disabled:text-[#A1A1AA]"
            :disabled="selectedCount === 0"
            @click="openBatchRunDrawer"
          >
            批量执行
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
          v-if="displayRows.length > 0"
          v-model:selectedIds="selectedCaseIds"
          :rows="displayRows"
          @delete="deleteCase"
          @edit="openEditCase"
          @archive="archiveOrRestoreCase"
        />
        <div
          v-else
          class="flex h-[120px] items-center justify-center text-[14px] leading-[20px] text-[#717182]"
        >
          {{ isLoadingCases ? '加载中...' : '暂无用例' }}
        </div>
      </div>

      <div class="flex items-center justify-between">
        <div class="text-[14px] leading-[20px] text-[#717182]">
          共 {{ totalCasesLabel }} 条
          <span v-if="isLoadingCases"> · 加载中...</span>
          <span v-else> · 第 {{ page }}/{{ totalPages }} 页</span>
        </div>
        <div class="flex h-[28px] items-center gap-[4px]">
          <button
            type="button"
            class="relative h-[28px] w-[28px] rounded-[4px]"
            :class="canGoPrev ? 'bg-white hover:bg-black/5' : 'opacity-30'"
            :disabled="!canGoPrev"
            aria-label="上一页"
            @click="goToPage(page - 1)"
          >
            <span class="absolute left-[11.93px] top-[6px] text-[12px] font-medium leading-[16px] text-[#717182]">‹</span>
          </button>
          <template v-for="(item, idx) in paginationItems" :key="`${item}-${idx}`">
            <span
              v-if="item === '...'"
              class="flex h-[28px] min-w-[28px] items-center justify-center text-[12px] font-medium leading-[16px] text-[#717182]"
            >
              ...
            </span>
            <button
              v-else
              type="button"
              class="relative h-[28px] min-w-[28px] rounded-[4px] px-[8px]"
              :class="item === page ? 'bg-[#155DFC]' : 'bg-white hover:bg-black/5'"
              :disabled="isLoadingCases"
              :aria-label="`第 ${item} 页`"
              @click="goToPage(item)"
            >
              <span
                class="absolute left-1/2 top-[6px] -translate-x-1/2 text-[12px] font-medium leading-[16px]"
                :class="item === page ? 'text-white' : 'text-[#717182]'"
              >
                {{ item }}
              </span>
            </button>
          </template>
          <button
            type="button"
            class="relative h-[28px] w-[28px] rounded-[4px]"
            :class="canGoNext ? 'bg-white hover:bg-black/5' : 'opacity-30'"
            :disabled="!canGoNext"
            aria-label="下一页"
            @click="goToPage(page + 1)"
          >
            <span class="absolute left-[11.93px] top-[6px] text-[12px] font-medium leading-[16px] text-[#717182]">›</span>
          </button>
        </div>
      </div>
    </div>
  </div>

  <UploadCasesModal
    :is-open="isUploadCasesOpen"
    :project-id="String(route.params.projectId || '')"
    @close="closeUploadCases"
    @imported="handleImportedCases"
  />
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
    :project-id="String(route.params.projectId || '')"
    @close="closeAiGenerateCase"
    @imported="handleImportedCases"
  />
  <BatchRunDrawer
    :is-open="isBatchRunDrawerOpen"
    :rows="selectedRows"
    :env-id="batchRunEnvId"
    :environments="batchRunEnvironments"
    :state="batchRunDrawerState === 'closed' ? 'preview' : batchRunDrawerState"
    :run-id="batchRunRunId"
    @close="closeBatchRunDrawer"
    @update:env-id="batchRunEnvId = $event"
    @execute="handleBatchRunDrawerExecute"
  />
</template>
