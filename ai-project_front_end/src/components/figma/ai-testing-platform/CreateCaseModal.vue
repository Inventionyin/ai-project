<script setup lang="ts">
import { ref, watch } from 'vue'
import modalClose from '@/assets/figma/ai-testing-platform/modal-close.svg'
import modalOwnerIcon from '@/assets/figma/ai-testing-platform/modal-owner-icon.svg'
import modalTagsIcon from '@/assets/figma/ai-testing-platform/modal-tags-icon.svg'

type CaseType = 'API' | 'UI' | 'PERF' | 'MIX'
type CasePriority = 'P0' | 'P1' | 'P2' | 'P3'
type CaseStatus = 'DRAFT' | 'REVIEWED' | 'DEPRECATED'

const props = defineProps<{
  isOpen: boolean
  defaultOwnerId: string
  ownerOptions: Array<{ id: string; username: string }>
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save', payload: {
    testCaseId: string
    title: string
    type: CaseType
    priority: CasePriority
    status: CaseStatus
    tags: string[]
    contentMd: string
    ownerId: string
    expectedStatusCode: number | null
    preconditions: string
    postconditions: string
    feature?: string
    apiMethod?: string
    apiUrl?: string
    apiParams: Record<string, unknown>
    apiHeaders: Record<string, string>
    expectedResult: string
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

const title = ref('')
const type = ref<CaseType>('API')
const priority = ref<CasePriority>('P0')
const status = ref<CaseStatus>('DRAFT')
const tagsInput = ref('')
const contentMd = ref('')
const ownerId = ref('')
const testCaseId = ref('')
const feature = ref('')
const apiMethod = ref('')
const apiUrl = ref('')
const apiParamsInput = ref('')
const apiHeadersInput = ref('')
const expectedResultInput = ref('')
const expectedStatusCodeInput = ref('')
const preconditions = ref('')
const postconditions = ref('')

function resetForm() {
  title.value = ''
  type.value = 'API'
  priority.value = 'P0'
  status.value = 'DRAFT'
  tagsInput.value = ''
  contentMd.value = ''
  ownerId.value = props.defaultOwnerId
  testCaseId.value = ''
  expectedStatusCodeInput.value = ''
  preconditions.value = ''
  postconditions.value = ''
  feature.value = ''
  apiMethod.value = ''
  apiUrl.value = ''
  apiParamsInput.value = ''
  apiHeadersInput.value = ''
  expectedResultInput.value = ''
}

function handleSave() {
  const cleanTestCaseId = testCaseId.value.trim()
  const cleanTitle = title.value.trim()
  const cleanContent = contentMd.value.trim()
  const cleanFeature = feature.value.trim()
  const cleanApiMethod = apiMethod.value.trim()
  const cleanApiUrl = apiUrl.value.trim()
  const rawApiParams = apiParamsInput.value.trim()
  const rawApiHeaders = apiHeadersInput.value.trim()
  const cleanExpectedResult = expectedResultInput.value.trim()
  const rawExpectedStatusCode = expectedStatusCodeInput.value.trim()
  let expectedStatusCode: number | null = null
  if (rawExpectedStatusCode) {
    const parsed = Number.parseInt(rawExpectedStatusCode, 10)
    if (!Number.isFinite(parsed) || parsed < 100 || parsed > 599) {
      window.alert('期望状态码需为 100-599 的整数')
      return
    }
    expectedStatusCode = parsed
  }
  const cleanPreconditions = preconditions.value.trim()
  const cleanPostconditions = postconditions.value.trim()
  if (!cleanFeature) {
    window.alert('请输入功能模块')
    return
  }
  if (!cleanTitle) {
    window.alert('请输入用例标题')
    return
  }
  if (!cleanApiMethod) {
    window.alert('请输入调用方式')
    return
  }
  if (!cleanApiUrl) {
    window.alert('请输入interfaceUrl')
    return
  }
  if (!cleanExpectedResult) {
    window.alert('请输入预期结果')
    return
  }
  let parsedApiParams: Record<string, unknown> = {}
  if (rawApiParams) {
    try {
      const parsed = JSON.parse(rawApiParams) as unknown
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
        window.alert('接口参数需为合法JSON对象')
        return
      }
      parsedApiParams = parsed as Record<string, unknown>
    } catch {
      window.alert('接口参数需为合法JSON对象')
      return
    }
  }
  let parsedApiHeaders: Record<string, string> = {}
  if (rawApiHeaders) {
    try {
      const parsed = JSON.parse(rawApiHeaders) as unknown
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
        window.alert('Header 需为合法JSON对象')
        return
      }
      const nextHeaders: Record<string, string> = {}
      for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
        const headerKey = String(key || '').trim()
        if (!headerKey) {
          window.alert('Header 键不能为空')
          return
        }
        if (typeof value !== 'string') {
          window.alert('Header 值必须为字符串')
          return
        }
        nextHeaders[headerKey] = value
      }
      parsedApiHeaders = nextHeaders
    } catch {
      window.alert('Header 需为合法JSON对象')
      return
    }
  }
  emit('save', {
    testCaseId: cleanTestCaseId,
    title: cleanTitle,
    type: type.value,
    priority: priority.value,
    status: status.value,
    tags: tagsInput.value.split(',').map((item) => item.trim()).filter(Boolean),
    contentMd: cleanContent,
    ownerId: ownerId.value,
    expectedStatusCode,
    preconditions: cleanPreconditions,
    postconditions: cleanPostconditions,
    feature: cleanFeature || undefined,
    apiMethod: cleanApiMethod || undefined,
    apiUrl: cleanApiUrl || undefined,
    apiParams: parsedApiParams,
    apiHeaders: parsedApiHeaders,
    expectedResult: cleanExpectedResult
  })
}

watch(
  () => props.isOpen,
  (next) => {
    if (next) {
      resetForm()
    }
  }
)

watch(
  () => props.defaultOwnerId,
  (next) => {
    if (props.isOpen) {
      ownerId.value = next
    }
  }
)
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50">
    <button class="absolute inset-0 bg-black/40" type="button" aria-label="Close" @click="emit('close')" />

    <div class="absolute inset-y-0 right-0 z-10 flex h-full w-full max-w-[560px] flex-col bg-white px-[24px] pb-[24px] pt-[24px] shadow-[-10px_0_30px_-12px_rgba(0,0,0,0.3)]">
      <div class="flex items-center justify-between">
        <div class="h-[20px] w-[56px]">
          <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">新建用例</div>
        </div>
        <button type="button" class="h-[18px] w-[18px]" aria-label="Close" @click="emit('close')">
          <img :src="modalClose" alt="" class="h-full w-full" />
        </button>
      </div>

      <div class="mt-[20px] flex-1 overflow-auto">
        <div class="flex flex-col gap-[16px] pb-[4px]">
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
              调用方式 <span class="text-[#FB2C36]">*</span>
            </div>
            <input
              v-model="apiMethod"
              class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              type="text"
              placeholder="请输入调用方式,例如：post、get"
            />
          </div>

          <div class="flex flex-col gap-[6px]">
            <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
              interfaceUrl <span class="text-[#FB2C36]">*</span>
            </div>
            <input
              v-model="apiUrl"
              class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              type="text"
              placeholder="请输入接口url"
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
              接口参数
            </div>
            <textarea
              v-model="apiParamsInput"
              class="h-[88px] w-full resize-none rounded-[10px] border border-black/10 bg-white px-[12px] py-[8px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              placeholder="可选；如需传参请输入 JSON 对象，例如：{&quot;userId&quot;:&quot;123&quot;,&quot;page&quot;:1}"
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

          </div>

          <div class="flex flex-col gap-[6px]">
            <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">
              用例内容
            </div>
            <textarea
              v-model="contentMd"
              class="h-[88px] w-full resize-none rounded-[10px] border border-black/10 bg-white px-[12px] py-[8px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              placeholder="请输入用例步骤、预期结果等内容"
            />
          </div>

          <div class="grid grid-cols-1 gap-x-[16px] gap-y-[16px] sm:grid-cols-2">
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
      </div>

      <div class="mt-[20px] flex gap-[8px]">
        <button type="button" class="h-[36px] flex-1 rounded-[10px] border border-black/10 bg-white text-[14px] font-medium leading-[20px] text-[#0A0A0A]" @click="emit('close')">
          取消
        </button>
        <button type="button" class="h-[36px] flex-1 rounded-[10px] bg-[#155DFC] text-[14px] font-medium leading-[20px] text-white" @click="handleSave">
          保存
        </button>
      </div>
    </div>
  </div>
</template>
