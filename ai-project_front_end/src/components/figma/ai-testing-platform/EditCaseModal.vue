<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import modalClose from '@/assets/figma/ai-testing-platform/modal-close.svg'
import modalOwnerIcon from '@/assets/figma/ai-testing-platform/modal-owner-icon.svg'
import modalTagsIcon from '@/assets/figma/ai-testing-platform/modal-tags-icon.svg'

type CaseType = 'API' | 'UI' | 'PERF' | 'MIX'
type CasePriority = 'P0' | 'P1' | 'P2' | 'P3'
type CaseStatus = 'DRAFT' | 'REVIEWED' | 'DEPRECATED'

type EditCaseInitialData = {
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
  type: CaseType
  priority: CasePriority
  status: CaseStatus
  tags: string[]
  contentMd: string
  ownerId?: string | null
}

const props = defineProps<{
  isOpen: boolean
  initialData: EditCaseInitialData
  ownerOptions: Array<{ id: string; username: string }>
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save', payload: {
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
    type: CaseType
    priority: CasePriority
    status: CaseStatus
    tags: string[]
    contentMd: string
    ownerId: string
  }): void
}>()

const typeOptions: Array<{ label: string; value: CaseType }> = [
  { label: 'API', value: 'API' },
  { label: 'UI', value: 'UI' },
  { label: 'PERF', value: 'PERF' },
  { label: 'MIX', value: 'MIX' }
]
const priorityOptions: CasePriority[] = ['P0', 'P1', 'P2', 'P3']
const statusOptions: Array<{ label: string; value: CaseStatus }> = [
  { label: '草稿', value: 'DRAFT' },
  { label: '已评审', value: 'REVIEWED' },
  { label: '已弃用', value: 'DEPRECATED' }
]

const feature = ref('')
const title = ref('')
const apiMethod = ref('')
const apiUrl = ref('')
const apiParamsInput = ref('')
const apiHeadersInput = ref('')
const expectedResultInput = ref('')
const type = ref<CaseType>('API')
const priority = ref<CasePriority>('P0')
const status = ref<CaseStatus>('DRAFT')
const tagsInput = ref('')
const contentMd = ref('')
const ownerId = ref('')
const testCaseId = ref('')
const expectedStatusCodeInput = ref('')
const preconditions = ref('')
const postconditions = ref('')
const ownerOptions = computed(() => {
  if (!ownerId.value || props.ownerOptions.some((item) => item.id === ownerId.value)) {
    return props.ownerOptions
  }
  return [{ id: ownerId.value, username: ownerId.value }, ...props.ownerOptions]
})
const isGetMethod = computed(() => apiMethod.value.trim().toUpperCase() === 'GET')

function showToast(message: string, type: 'success' | 'error' = 'success') {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, type } }))
}

watch(
  () => props.initialData,
  (next) => {
    testCaseId.value = next.testCaseId || ''
    expectedStatusCodeInput.value = next.expectedStatusCode == null ? '' : String(next.expectedStatusCode)
    preconditions.value = next.preconditions || ''
    postconditions.value = next.postconditions || ''
    feature.value = next.feature || ''
    title.value = next.title
    apiMethod.value = next.apiMethod || ''
    apiUrl.value = next.apiUrl || ''
    apiParamsInput.value = Object.keys(next.apiParams || {}).length ? JSON.stringify(next.apiParams, null, 2) : ''
    apiHeadersInput.value = Object.keys(next.apiHeaders || {}).length ? JSON.stringify(next.apiHeaders, null, 2) : ''
    expectedResultInput.value = next.expectedResult || ''
    type.value = next.type
    priority.value = next.priority
    status.value = next.status
    tagsInput.value = next.tags.join(', ')
    contentMd.value = next.contentMd || ''
    ownerId.value = next.ownerId || ''
  },
  { immediate: true, deep: true }
)

function handleSave() {
  const cleanTestCaseId = testCaseId.value.trim()
  const cleanFeature = feature.value.trim()
  const cleanTitle = title.value.trim()
  const cleanApiMethod = apiMethod.value.trim()
  const cleanApiUrl = apiUrl.value.trim()
  const rawApiParams = apiParamsInput.value.trim()
  const rawApiHeaders = apiHeadersInput.value.trim()
  const cleanExpectedResult = expectedResultInput.value.trim()
  const cleanContentMd = contentMd.value.trim()
  const rawExpectedStatusCode = expectedStatusCodeInput.value.trim()
  let expectedStatusCode: number | null = null
  if (rawExpectedStatusCode) {
    const parsed = Number.parseInt(rawExpectedStatusCode, 10)
    if (!Number.isFinite(parsed) || parsed < 100 || parsed > 599) {
      showToast('期望状态码需为 100-599 的整数', 'error')
      return
    }
    expectedStatusCode = parsed
  }
  const cleanPreconditions = preconditions.value.trim()
  const cleanPostconditions = postconditions.value.trim()
  if (!cleanFeature) {
    showToast('请输入功能模块', 'error')
    return
  }
  if (!cleanTitle) {
    showToast('请输入用例标题', 'error')
    return
  }
  if (!cleanApiMethod) {
    showToast('请输入请求方法', 'error')
    return
  }
  if (!cleanApiUrl) {
    showToast('请输入接口地址', 'error')
    return
  }
  if (!cleanExpectedResult) {
    showToast('请输入预期结果', 'error')
    return
  }
  if (!cleanContentMd) {
    showToast('请输入用例内容', 'error')
    return
  }
  let parsedApiParams: Record<string, unknown> = {}
  if (rawApiParams) {
    try {
      const parsed = JSON.parse(rawApiParams) as unknown
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
        showToast('请求参数需为合法 JSON 对象', 'error')
        return
      }
      parsedApiParams = parsed as Record<string, unknown>
    } catch {
      showToast('请求参数需为合法 JSON 对象', 'error')
      return
    }
  } else if (!isGetMethod.value) {
    showToast('请输入请求参数', 'error')
    return
  }
  let parsedApiHeaders: Record<string, string> = {}
  if (rawApiHeaders) {
    try {
      const parsed = JSON.parse(rawApiHeaders) as unknown
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
        showToast('Header 需为合法JSON对象', 'error')
        return
      }
      const nextHeaders: Record<string, string> = {}
      for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
        const headerKey = String(key || '').trim()
        if (!headerKey) {
          showToast('Header 键不能为空', 'error')
          return
        }
        if (typeof value !== 'string') {
          showToast('Header 值必须为字符串', 'error')
          return
        }
        nextHeaders[headerKey] = value
      }
      parsedApiHeaders = nextHeaders
    } catch {
      showToast('Header 需为合法JSON对象', 'error')
      return
    }
  }
  emit('save', {
    testCaseId: cleanTestCaseId,
    expectedStatusCode,
    preconditions: cleanPreconditions,
    postconditions: cleanPostconditions,
    feature: cleanFeature,
    title: cleanTitle,
    apiMethod: cleanApiMethod,
    apiUrl: cleanApiUrl,
    apiParams: parsedApiParams,
    apiHeaders: parsedApiHeaders,
    expectedResult: cleanExpectedResult,
    type: type.value,
    priority: priority.value,
    status: status.value,
    tags: tagsInput.value.split(',').map((item) => item.trim()).filter(Boolean),
    contentMd: cleanContentMd,
    ownerId: ownerId.value.trim()
  })
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
    <button class="absolute inset-0 bg-black/40" type="button" aria-label="Close" @click="emit('close')" />

    <div class="relative max-h-[calc(100vh-32px)] w-full max-w-[calc(100vw-32px)] overflow-auto rounded-[16px] bg-white px-[24px] pt-[24px] shadow-[0px_25px_50px_-12px_rgba(0,0,0,0.25)] sm:h-[calc(100vh-64px)] sm:w-[560px] sm:max-w-[560px]">
      <div class="flex items-center justify-between">
        <div class="h-[20px] w-[56px]">
          <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">编辑用例</div>
        </div>
        <button type="button" class="h-[18px] w-[18px]" aria-label="Close" @click="emit('close')">
          <img :src="modalClose" alt="" class="h-full w-full" />
        </button>
      </div>

      <div class="mt-[20px] flex flex-col gap-[16px] pb-[4px]">
        <div class="flex flex-col gap-[6px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
            测试用例ID
          </div>
          <input
            v-model="testCaseId"
            class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            type="text"
            placeholder="请输入业务编号，例如：TC001001"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
            功能模块 <span class="text-[#FB2C36]">*</span>
          </div>
          <input
            v-model="feature"
            class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            type="text"
            placeholder="请输入用例所属模块"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
            标题 <span class="text-[#FB2C36]">*</span>
          </div>
          <input
            v-model="title"
            class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            type="text"
            placeholder="请输入用例标题"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
            请求方法 <span class="text-[#FB2C36]">*</span>
          </div>
          <input
            v-model="apiMethod"
            class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            type="text"
            placeholder="例如：POST、GET"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
            接口地址 <span class="text-[#FB2C36]">*</span>
          </div>
          <input
            v-model="apiUrl"
            class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            type="text"
            placeholder="例如：/api/auth/login"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
            期望状态码
          </div>
          <input
            v-model="expectedStatusCodeInput"
            class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            type="text"
            placeholder="例如：200"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
            请求参数 <span v-if="!isGetMethod" class="text-[#FB2C36]">*</span>
          </div>
          <textarea
            v-model="apiParamsInput"
            class="h-[88px] w-full resize-none rounded-[10px] border border-black/10 bg-white px-[12px] py-[8px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            placeholder="可选（GET可不填）；如需传参请输入 JSON 对象，例如：{&quot;userId&quot;:&quot;123&quot;,&quot;page&quot;:1}"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
            Header
          </div>
          <textarea
            v-model="apiHeadersInput"
            class="h-[88px] w-full resize-none rounded-[10px] border border-black/10 bg-white px-[12px] py-[8px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            placeholder="可选，JSON对象，例如：{&quot;Authorization&quot;:&quot;Bearer xxx&quot;,&quot;X-Trace-Id&quot;:&quot;abc&quot;}"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
            预期结果 <span class="text-[#FB2C36]">*</span>
          </div>
          <textarea
            v-model="expectedResultInput"
            class="h-[88px] w-full resize-none rounded-[10px] border border-black/10 bg-white px-[12px] py-[8px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            placeholder="请输入预期结果，用于自动化断言校验，例如：code=0"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
            前置条件
          </div>
          <textarea
            v-model="preconditions"
            class="h-[88px] w-full resize-none rounded-[10px] border border-black/10 bg-white px-[12px] py-[8px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            placeholder="请输入前置条件"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
            后置条件
          </div>
          <textarea
            v-model="postconditions"
            class="h-[88px] w-full resize-none rounded-[10px] border border-black/10 bg-white px-[12px] py-[8px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            placeholder="请输入后置条件"
          />
        </div>

        <div class="grid grid-cols-1 gap-x-[16px] gap-y-[16px] sm:grid-cols-2">
          <div class="flex flex-col gap-[6px]">
            <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
              类型 <span class="text-[#FB2C36]">*</span>
            </div>
            <select
              v-model="type"
              class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            >
              <option v-for="item in typeOptions" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </div>

          <div class="flex flex-col gap-[6px]">
            <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
              优先级 <span class="text-[#FB2C36]">*</span>
            </div>
            <select
              v-model="priority"
              class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            >
              <option v-for="item in priorityOptions" :key="item" :value="item">
                {{ item }}
              </option>
            </select>
          </div>

          <div class="flex flex-col gap-[6px]">
            <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
              状态 <span class="text-[#FB2C36]">*</span>
            </div>
            <select
              v-model="status"
              class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            >
              <option v-for="item in statusOptions" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </div>

          <div class="flex flex-col gap-[6px]">
            <div class="relative h-[16px] w-full">
              <img :src="modalOwnerIcon" alt="" class="absolute left-0 top-[2.5px] h-[11px] w-[11px]" />
              <div class="absolute left-[15px] top-0 text-[12px] font-medium leading-[16px] text-[#0A0A0A]">维护人</div>
            </div>
            <select
              v-model="ownerId"
              class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            >
              <option v-for="item in ownerOptions" :key="item.id" :value="item.id">
                {{ item.username }}
              </option>
            </select>
          </div>
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
            用例内容 <span class="text-[#FB2C36]">*</span>
          </div>
          <textarea
            v-model="contentMd"
            class="h-[88px] w-full resize-none rounded-[10px] border border-black/10 bg-white px-[12px] py-[8px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            placeholder="请输入用例步骤、预期结果等内容"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="relative h-[16px] w-full">
            <img :src="modalTagsIcon" alt="" class="absolute left-0 top-[2.5px] h-[11px] w-[11px]" />
            <div class="absolute left-[15px] top-0 text-[12px] font-medium leading-[16px] text-[#0A0A0A]">标签</div>
          </div>
          <input
            v-model="tagsInput"
            class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            type="text"
            placeholder="多个标签用英文逗号分隔，如 smoke, order"
          />
        </div>
      </div>

      <div class="mt-[20px] flex gap-[8px]">
        <button type="button" class="h-[36px] flex-1 rounded-[10px] border border-black/10 bg-white text-[14px] font-medium leading-[20px] text-[#0A0A0A]" @click="emit('close')">
          取消
        </button>
        <button
          type="button"
          class="h-[36px] flex-1 rounded-[10px] bg-[#155DFC] text-[14px] font-medium leading-[20px] text-white"
          @click="handleSave"
        >
          保存
        </button>
      </div>
    </div>
  </div>
</template>
