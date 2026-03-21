<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import suiteDetailBack from '@/assets/figma/ai-testing-platform/suite-detail-back.svg'
import suiteDetailRun from '@/assets/figma/ai-testing-platform/suite-detail-run.svg'
import suiteDetailSave from '@/assets/figma/ai-testing-platform/suite-detail-save.svg'
import chevronDownSmall from '@/assets/figma/ai-testing-platform/chevron-down-small.svg'
import modalTagsIcon from '@/assets/figma/ai-testing-platform/modal-tags-icon.svg'
import btnAiGenerate from '@/assets/figma/ai-testing-platform/btn-ai-generate.svg'

type CaseType = 'API' | 'UI' | 'PERF' | 'MIX'
type CasePriority = 'P0' | 'P1' | 'P2' | 'P3'
type CaseStatus = '已评审' | '草稿' | '已弃用'
type CaseStatusCode = 'DRAFT' | 'REVIEWED' | 'DEPRECATED'

type TabKey = 'basic' | 'content' | 'ai' | 'history'
type ApiResponse<T> = {
  code?: number
  message?: string
  data?: T
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
  type: CaseType
  priority: CasePriority
  status: CaseStatusCode
  tags: string[]
  ownerId?: string | null
  ownerName?: string | null
  contentMd: string
  feature?: string | null
  apiMethod?: string | null
  apiUrl?: string | null
  apiParams?: Record<string, unknown>
  apiHeaders?: Record<string, string>
  expectedResult?: string | null
}

const router = useRouter()
const route = useRoute()
const isLoading = ref(false)
const isSaving = ref(false)
const loadError = ref('')
const currentDetail = ref<TestCaseDetail | null>(null)

const projectId = computed(() => {
  const value = route.params.projectId
  return typeof value === 'string' && value.length > 0 ? value : '1'
})

const caseId = computed(() => {
  const value = route.params.id
  return typeof value === 'string' && value.length > 0 ? value : '1'
})

function showToast(message: string, type: 'success' | 'error' = 'success') {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, type } }))
}

function goBack() {
  router.push(`/projects/${projectId.value}/assets/testcases`)
}

function debugRun() {
  showToast('调试运行已触发')
}

const activeTab = ref<TabKey>('basic')
const caseVersion = ref('v1.0')
const tabKeys: TabKey[] = ['basic', 'content', 'ai', 'history']
const statusLabelMap: Record<CaseStatusCode, CaseStatus> = {
  DRAFT: '草稿',
  REVIEWED: '已评审',
  DEPRECATED: '已弃用'
}
const statusCodeMap: Record<CaseStatus, CaseStatusCode> = {
  草稿: 'DRAFT',
  已评审: 'REVIEWED',
  已弃用: 'DEPRECATED'
}

const form = reactive({
  testCaseId: '',
  expectedStatusCodeInput: '',
  preconditions: '',
  postconditions: '',
  feature: '',
  title: '',
  apiMethod: '',
  apiUrl: '',
  apiParamsInput: '',
  apiHeadersInput: '',
  expectedResult: '',
  type: 'API' as CaseType,
  priority: 'P0' as CasePriority,
  status: '草稿' as CaseStatus,
  tags: '',
  owner: '',
  contentMd: ''
})

const meta = computed(() => ({
  version: caseVersion.value,
  status: form.status
}))

function tabButtonClass(tab: TabKey) {
  if (activeTab.value === tab) {
    return 'border-[#155DFC] text-[#155DFC]'
  }
  return 'border-transparent text-[#717182]'
}

function resolveApiBaseUrl() {
  const envBase = String(import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!envBase) return ''
  return envBase.endsWith('/') ? envBase.slice(0, -1) : envBase
}

function resolveApiUrl(path: string) {
  return `${resolveApiBaseUrl()}${path}`
}

function resolveAuthHeader() {
  const accessToken = localStorage.getItem('accessToken')
  if (!accessToken) {
    throw new Error('登录状态已失效，请重新登录')
  }
  return `Bearer ${accessToken}`
}

function parseTags(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function parseJsonObject(value: string, field: string): Record<string, unknown> {
  const text = value.trim()
  if (!text) {
    throw new Error(`${field}不能为空`)
  }
  let parsed: unknown
  try {
    parsed = JSON.parse(text)
  } catch {
    throw new Error(`${field}需为合法JSON对象`)
  }
  if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
    throw new Error(`${field}需为合法JSON对象`)
  }
  return parsed as Record<string, unknown>
}

function parseHeaderObject(value: string): Record<string, string> {
  const text = value.trim()
  if (!text) {
    return {}
  }
  let parsed: unknown
  try {
    parsed = JSON.parse(text)
  } catch {
    throw new Error('Header需为合法JSON对象')
  }
  if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
    throw new Error('Header需为合法JSON对象')
  }
  const headers: Record<string, string> = {}
  for (const [key, item] of Object.entries(parsed as Record<string, unknown>)) {
    const headerKey = String(key || '').trim()
    if (!headerKey) {
      throw new Error('Header键不能为空')
    }
    if (typeof item !== 'string') {
      throw new Error('Header值必须为字符串')
    }
    headers[headerKey] = item
  }
  return headers
}

async function saveCase() {
  const feature = form.feature.trim()
  const title = form.title.trim()
  const apiMethod = form.apiMethod.trim()
  const apiUrl = form.apiUrl.trim()
  const expectedResult = form.expectedResult.trim()
  const contentMd = form.contentMd.trim()
  const rawExpectedStatusCode = form.expectedStatusCodeInput.trim()
  let expectedStatusCode: number | null = null
  if (rawExpectedStatusCode) {
    const parsed = Number.parseInt(rawExpectedStatusCode, 10)
    if (!Number.isFinite(parsed) || parsed < 100 || parsed > 599) {
      showToast('期望状态码需为 100-599 的整数', 'error')
      return
    }
    expectedStatusCode = parsed
  }
  const testCaseId = form.testCaseId.trim()
  const preconditions = form.preconditions.trim()
  const postconditions = form.postconditions.trim()
  let apiParams: Record<string, unknown> = {}
  let apiHeaders: Record<string, string> = {}
  try {
    apiParams = parseJsonObject(form.apiParamsInput, '接口参数')
    apiHeaders = parseHeaderObject(form.apiHeadersInput)
  } catch (error) {
    showToast(error instanceof Error ? error.message : '接口参数校验失败', 'error')
    return
  }
  if (!feature) {
    showToast('功能模块不能为空', 'error')
    return
  }
  if (!title) {
    showToast('标题不能为空', 'error')
    return
  }
  if (!apiMethod) {
    showToast('调用方式不能为空', 'error')
    return
  }
  if (!apiUrl) {
    showToast('interfaceUrl不能为空', 'error')
    return
  }
  if (!expectedResult) {
    showToast('预期结果不能为空', 'error')
    return
  }
  if (!contentMd) {
    showToast('用例内容不能为空', 'error')
    return
  }
  if (isSaving.value) {
    return
  }

  isSaving.value = true
  try {
    const response = await fetch(resolveApiUrl(`/api/testcases/${caseId.value}`), {
      method: 'PUT',
      headers: {
        Authorization: resolveAuthHeader(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        projectId: currentDetail.value?.projectId || projectId.value,
        testCaseId: testCaseId || null,
        expectedStatusCode,
        preconditions: preconditions || null,
        postconditions: postconditions || null,
        title,
        type: form.type,
        priority: form.priority,
        status: statusCodeMap[form.status],
        tags: parseTags(form.tags),
        contentMd,
        ownerId: currentDetail.value?.ownerId || null,
        feature,
        apiMethod,
        apiUrl,
        apiParams,
        apiHeaders,
        expectedResult
      })
    })
    const payload = await response.json() as ApiResponse<TestCaseDetail>
    if (!response.ok || payload.code !== 0 || !payload.data) {
      throw new Error(payload.message || '保存失败')
    }
    const detail = payload.data
    currentDetail.value = detail
    form.testCaseId = detail.testCaseId || ''
    form.expectedStatusCodeInput = detail.expectedStatusCode == null ? '' : String(detail.expectedStatusCode)
    form.preconditions = detail.preconditions || ''
    form.postconditions = detail.postconditions || ''
    form.title = detail.title
    form.feature = detail.feature || ''
    form.apiMethod = detail.apiMethod || ''
    form.apiUrl = detail.apiUrl || ''
    form.apiParamsInput = JSON.stringify(detail.apiParams || {}, null, 2)
    form.apiHeadersInput = Object.keys(detail.apiHeaders || {}).length ? JSON.stringify(detail.apiHeaders, null, 2) : ''
    form.expectedResult = detail.expectedResult || ''
    form.type = detail.type
    form.priority = detail.priority
    form.status = statusLabelMap[detail.status]
    form.tags = (detail.tags || []).join(', ')
    form.owner = detail.ownerName || form.owner
    form.contentMd = detail.contentMd
    caseVersion.value = detail.version
    showToast('用例已保存')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '保存失败', 'error')
  } finally {
    isSaving.value = false
  }
}

async function loadCaseDetail() {
  isLoading.value = true
  loadError.value = ''
  try {
    const response = await fetch(resolveApiUrl(`/api/testcases/${caseId.value}`), {
      method: 'GET',
      headers: {
        Authorization: resolveAuthHeader()
      }
    })
    const payload = await response.json() as ApiResponse<TestCaseDetail>
    if (!response.ok || payload.code !== 0 || !payload.data) {
      throw new Error(payload.message || '获取用例详情失败')
    }
    const detail = payload.data
    currentDetail.value = detail
    form.testCaseId = detail.testCaseId || ''
    form.expectedStatusCodeInput = detail.expectedStatusCode == null ? '' : String(detail.expectedStatusCode)
    form.preconditions = detail.preconditions || ''
    form.postconditions = detail.postconditions || ''
    form.title = detail.title
    form.feature = detail.feature || ''
    form.apiMethod = detail.apiMethod || ''
    form.apiUrl = detail.apiUrl || ''
    form.apiParamsInput = JSON.stringify(detail.apiParams || {}, null, 2)
    form.apiHeadersInput = Object.keys(detail.apiHeaders || {}).length ? JSON.stringify(detail.apiHeaders, null, 2) : ''
    form.expectedResult = detail.expectedResult || ''
    form.type = detail.type
    form.priority = detail.priority
    form.status = statusLabelMap[detail.status]
    form.tags = (detail.tags || []).join(', ')
    form.owner = detail.ownerName || ''
    form.contentMd = detail.contentMd
    caseVersion.value = detail.version
  } catch (error) {
    currentDetail.value = null
    loadError.value = error instanceof Error ? error.message : '获取用例详情失败'
  } finally {
    isLoading.value = false
  }
}

function resolveTabFromRoute(): TabKey {
  const tab = route.query.tab
  if (typeof tab !== 'string') return 'basic'
  if (!tabKeys.includes(tab as TabKey)) return 'basic'
  return tab as TabKey
}

onMounted(() => {
  activeTab.value = resolveTabFromRoute()
  void loadCaseDetail()
})

watch(() => route.params.id, () => {
  activeTab.value = resolveTabFromRoute()
  void loadCaseDetail()
})

watch(() => route.query.tab, () => {
  const tab = resolveTabFromRoute()
  if (tab !== activeTab.value) activeTab.value = tab
})
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)] md:min-h-[calc(100vh-48px)] md:pr-[16.67px]">
    <div class="flex h-[62.67px] w-full items-center justify-between border-b-[0.6667px] border-black/10 bg-white px-[16px] md:px-[24px]">
      <div class="flex items-center gap-[12px]">
        <button type="button" class="h-[18px] w-[18px]" aria-label="Back" @click="goBack">
          <img :src="suiteDetailBack" alt="" class="h-[18px] w-[18px]" />
        </button>

        <div class="flex flex-col gap-[2px]">
          <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">{{ form.title }}</div>
          <div class="flex items-center gap-[8px] text-[12px] leading-[16px]">
            <span class="text-[#717182]">{{ meta.version }}</span>
            <span class="text-[#717182]">·</span>
            <span class="text-[#00A63E]">{{ meta.status }}</span>
            <span class="hidden text-[#717182]">#{{ caseId }}</span>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-[8px]">
        <button
          type="button"
          class="relative h-[32px] rounded-[10px] border-[0.6667px] border-black/10 bg-transparent px-[12px] pr-[14px]"
          @click="debugRun"
        >
          <div class="flex items-center gap-[6px]">
            <img :src="suiteDetailRun" alt="" class="h-[13px] w-[13px]" />
            <span class="text-[14px] font-medium leading-[20px] text-[#717182]">调试运行</span>
          </div>
        </button>

        <button
          type="button"
          class="relative h-[32px] rounded-[10px] bg-[#155DFC] px-[12px] pr-[14px] disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="isLoading || isSaving"
          @click="saveCase"
        >
          <div class="flex items-center gap-[6px]">
            <img :src="suiteDetailSave" alt="" class="h-[13px] w-[13px]" />
            <span class="text-[14px] font-medium leading-[20px] text-white">保存</span>
          </div>
        </button>
      </div>
    </div>

    <div class="flex h-[56px] items-end gap-[0px] border-b-[0.6667px] border-black/10 bg-white px-[16px] md:px-[24px]">
      <button
        type="button"
        class="h-[56px] border-b-[2px] px-[12px] text-[14px] font-medium leading-[20px]"
        :class="tabButtonClass('basic')"
        @click="activeTab = 'basic'"
      >
        基本信息
      </button>

      <button
        type="button"
        class="h-[56px] border-b-[2px] px-[12px] text-[14px] font-medium leading-[20px]"
        :class="tabButtonClass('content')"
        @click="activeTab = 'content'"
      >
        用例内容
      </button>

      <button
        type="button"
        class="flex h-[56px] items-center gap-[6px] border-b-[2px] px-[12px] text-[14px] font-medium leading-[20px]"
        :class="tabButtonClass('ai')"
        @click="activeTab = 'ai'"
      >
        <span>AI 辅助</span>
        <img :src="btnAiGenerate" alt="" class="h-[14px] w-[14px]" />
      </button>

      <button
        type="button"
        class="h-[56px] border-b-[2px] px-[12px] text-[14px] font-medium leading-[20px]"
        :class="tabButtonClass('history')"
        @click="activeTab = 'history'"
      >
        历史运行
      </button>
    </div>

    <div class="w-full px-[16px] pb-[16px] pt-[24px] md:px-[24px]">
      <div v-if="isLoading" class="mb-[16px] text-[14px] leading-[20px] text-[#717182]">详情加载中...</div>
      <div v-else-if="loadError" class="mb-[16px] text-[14px] leading-[20px] text-[#FB2C36]">{{ loadError }}</div>
      <div v-if="activeTab === 'basic'" class="w-full max-w-[715.33px]">
        <form class="w-full">
          <div class="grid grid-cols-1 gap-[16px] md:grid-cols-2">
            <div class="flex flex-col gap-[6px]">
              <label for="case-test-case-id" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">测试用例ID</label>
              <input
                id="case-test-case-id"
                v-model="form.testCaseId"
                type="text"
                class="h-[36px] w-full rounded-[10px] border-[0.6667px] border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              />
            </div>

            <div class="flex flex-col gap-[6px]">
              <label for="case-expected-status-code" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">期望状态码</label>
              <input
                id="case-expected-status-code"
                v-model="form.expectedStatusCodeInput"
                type="text"
                class="h-[36px] w-full rounded-[10px] border-[0.6667px] border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
                placeholder="例如：200"
              />
            </div>

            <div class="flex flex-col gap-[6px]">
              <label for="case-feature" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">功能模块 <span class="text-[#FB2C36]">*</span></label>
              <input
                id="case-feature"
                v-model="form.feature"
                type="text"
                class="h-[36px] w-full rounded-[10px] border-[0.6667px] border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              />
            </div>

            <div class="flex flex-col gap-[6px]">
              <label for="case-title" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">标题 <span class="text-[#FB2C36]">*</span></label>
              <input
                id="case-title"
                v-model="form.title"
                type="text"
                class="h-[36px] w-full rounded-[10px] border-[0.6667px] border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              />
            </div>

            <div class="flex flex-col gap-[6px]">
              <label for="case-type" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">类型 <span class="text-[#FB2C36]">*</span></label>
              <div class="relative">
                <select
                  id="case-type"
                  v-model="form.type"
                  class="h-[36px] w-full appearance-none rounded-[10px] border-[0.6667px] border-black/10 bg-white px-[12px] pr-[36px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
                >
                  <option value="API">API</option>
                  <option value="UI">UI</option>
                  <option value="PERF">PERF</option>
                  <option value="MIX">MIX</option>
                </select>
                <img :src="chevronDownSmall" alt="" class="pointer-events-none absolute right-[12px] top-1/2 h-[13px] w-[13px] -translate-y-1/2" />
              </div>
            </div>

            <div class="flex flex-col gap-[6px]">
              <label for="case-priority" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">优先级 <span class="text-[#FB2C36]">*</span></label>
              <div class="relative">
                <select
                  id="case-priority"
                  v-model="form.priority"
                  class="h-[36px] w-full appearance-none rounded-[10px] border-[0.6667px] border-black/10 bg-white px-[12px] pr-[36px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
                >
                  <option value="P0">P0</option>
                  <option value="P1">P1</option>
                  <option value="P2">P2</option>
                  <option value="P3">P3</option>
                </select>
                <img :src="chevronDownSmall" alt="" class="pointer-events-none absolute right-[12px] top-1/2 h-[13px] w-[13px] -translate-y-1/2" />
              </div>
            </div>

            <div class="flex flex-col gap-[6px]">
              <label for="case-status" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">状态 <span class="text-[#FB2C36]">*</span></label>
              <div class="relative">
                <select
                  id="case-status"
                  v-model="form.status"
                  class="h-[36px] w-full appearance-none rounded-[10px] border-[0.6667px] border-black/10 bg-white px-[12px] pr-[36px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
                >
                  <option value="草稿">草稿</option>
                  <option value="已评审">已评审</option>
                  <option value="已弃用">已弃用</option>
                </select>
                <img :src="chevronDownSmall" alt="" class="pointer-events-none absolute right-[12px] top-1/2 h-[13px] w-[13px] -translate-y-1/2" />
              </div>
            </div>

            <div class="flex flex-col gap-[6px]">
              <div class="flex items-center gap-[6px]">
                <img :src="modalTagsIcon" alt="" class="h-[13px] w-[13px]" />
                <label for="case-tags" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">标签</label>
              </div>
              <input
                id="case-tags"
                v-model="form.tags"
                type="text"
                class="h-[36px] w-full rounded-[10px] border-[0.6667px] border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              />
            </div>
          </div>

          <div class="mt-[16px] flex flex-col gap-[6px]">
            <label for="case-api-method" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">调用方式 <span class="text-[#FB2C36]">*</span></label>
            <input
              id="case-api-method"
              v-model="form.apiMethod"
              type="text"
              class="h-[36px] w-full rounded-[10px] border-[0.6667px] border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            />
          </div>

          <div class="mt-[16px] flex flex-col gap-[6px]">
            <label for="case-api-url" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">interfaceUrl <span class="text-[#FB2C36]">*</span></label>
            <input
              id="case-api-url"
              v-model="form.apiUrl"
              type="text"
              class="h-[36px] w-full rounded-[10px] border-[0.6667px] border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            />
          </div>

          <div class="mt-[16px] flex flex-col gap-[6px]">
            <label for="case-api-params" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">接口参数 <span class="text-[#FB2C36]">*</span></label>
            <textarea
              id="case-api-params"
              v-model="form.apiParamsInput"
              class="h-[128px] w-full resize-y rounded-[10px] border-[0.6667px] border-black/10 bg-white p-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            />
          </div>

          <div class="mt-[16px] flex flex-col gap-[6px]">
            <label for="case-api-headers" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">Header</label>
            <textarea
              id="case-api-headers"
              v-model="form.apiHeadersInput"
              class="h-[128px] w-full resize-y rounded-[10px] border-[0.6667px] border-black/10 bg-white p-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            />
          </div>

          <div class="mt-[16px] flex flex-col gap-[6px]">
            <label for="case-expected-result" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">预期结果 <span class="text-[#FB2C36]">*</span></label>
            <textarea
              id="case-expected-result"
              v-model="form.expectedResult"
              class="h-[128px] w-full resize-y rounded-[10px] border-[0.6667px] border-black/10 bg-white p-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            />
          </div>

          <div class="mt-[16px] flex flex-col gap-[6px]">
            <label for="case-preconditions" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">前置条件</label>
            <textarea
              id="case-preconditions"
              v-model="form.preconditions"
              class="h-[128px] w-full resize-y rounded-[10px] border-[0.6667px] border-black/10 bg-white p-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            />
          </div>

          <div class="mt-[16px] flex flex-col gap-[6px]">
            <label for="case-postconditions" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">后置条件</label>
            <textarea
              id="case-postconditions"
              v-model="form.postconditions"
              class="h-[128px] w-full resize-y rounded-[10px] border-[0.6667px] border-black/10 bg-white p-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            />
          </div>

          <div class="mt-[16px] flex flex-col gap-[6px]">
            <label for="case-owner" class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">维护人</label>
            <input
              id="case-owner"
              v-model="form.owner"
              type="text"
              class="h-[36px] w-full rounded-[10px] border-[0.6667px] border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              readonly
            />
          </div>
        </form>
      </div>

      <div v-else-if="activeTab === 'content'" class="w-full max-w-[715.33px]">
        <div class="rounded-[14px] border border-black/10 bg-white p-[16px] md:p-[24px]">
          <div class="mb-[8px] flex items-center justify-between">
            <div class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">用例内容（Markdown）</div>
            <div class="text-[12px] leading-[16px] text-[#717182]">支持 Markdown 格式</div>
          </div>
          <textarea
            v-model="form.contentMd"
            class="h-[240px] w-full resize-y rounded-[10px] border-[0.6667px] border-black/10 bg-white p-[12px] text-[13px] leading-[20px] text-[#0A0A0A] outline-none"
          />
        </div>
      </div>

      <div v-else-if="activeTab === 'ai'" class="w-full max-w-[715.33px]">
        <div class="rounded-[14px] border border-black/10 bg-white p-[16px] md:p-[24px]">
          <div class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">AI 辅助</div>
          <div class="mt-[8px] text-[13px] leading-[20px] text-[#717182]">请选择左侧操作或在顶部点击“调试运行”。</div>
        </div>
      </div>

      <div v-else-if="activeTab === 'history'" class="w-full max-w-[715.33px]">
        <div class="rounded-[14px] border border-black/10 bg-white p-[16px] md:p-[24px]">
          <div class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">历史运行</div>
          <div class="mt-[8px] text-[13px] leading-[20px] text-[#717182]">暂无数据。</div>
        </div>
      </div>

      <div v-else class="w-full max-w-[715.33px]" />
    </div>
  </div>
</template>
