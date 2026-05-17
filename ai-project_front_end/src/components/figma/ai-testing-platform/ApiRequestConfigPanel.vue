<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import apiSend from '@/assets/figma/ai-testing-platform/api-send.svg'
import apiExportCurl from '@/assets/figma/ai-testing-platform/api-export-curl.svg'
import {
  fetchCollectionRequestDetail,
  runCollectionRequest,
  updateCollectionRequest,
  type CollectionRequest
} from '@/lib/api/collections'

const props = defineProps<{
  collectionId: string
  requestId: string
}>()

type TabKey = 'request' | 'assert' | 'response'
const activeTab = ref<TabKey>('request')

const loading = ref(false)
const saving = ref(false)
const running = ref(false)
const loadError = ref('')
const request = ref<CollectionRequest | null>(null)

const method = ref('GET')
const url = ref('')
const requestHeaders = ref<Array<{ key: string; value: string }>>([])
const authType = ref('Bearer')
const authToken = ref('')
const requestBody = ref('')
const assertionRules = ref<Array<{ tag: string; op: string; value: string }>>([])

const responseStatusCode = ref<number | null>(null)
const responseStatusText = ref('')
const responseTime = ref<number | null>(null)
const responseBody = ref('')
const responseError = ref('')

const methodColors: Record<string, { bg: string; fg: string }> = {
  GET: { bg: '#F0FDF4', fg: '#00A63E' },
  POST: { bg: '#EFF6FF', fg: '#155DFC' },
  PUT: { bg: '#FEFCE8', fg: '#D08700' },
  PATCH: { bg: '#FFEDD4', fg: '#F54900' },
  DELETE: { bg: '#FFE2E2', fg: '#E7000B' }
}

const currentMethodColor = computed(() => methodColors[method.value.toUpperCase()] || methodColors.GET)

async function loadRequest() {
  if (!props.collectionId || !props.requestId) {
    request.value = null
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    const data = await fetchCollectionRequestDetail(props.collectionId, props.requestId)
    request.value = data
    method.value = (data.method || 'GET').toUpperCase()
    url.value = data.url || ''

    // Parse headers
    const hdrs = data.headers || {}
    requestHeaders.value = Object.entries(hdrs).map(([key, value]) => ({ key, value: String(value) }))
    if (requestHeaders.value.length === 0) {
      requestHeaders.value = [{ key: 'Content-Type', value: 'application/json' }]
    }

    // Parse auth
    const auth = data.auth || {}
    authType.value = String(auth.type || auth.authType || 'Bearer')
    authToken.value = String(auth.token || auth.value || '')

    // Parse body
    if (data.body && typeof data.body === 'object') {
      requestBody.value = JSON.stringify(data.body, null, 2)
    } else {
      requestBody.value = ''
    }

    // Parse asserts
    const asserts = data.asserts || {}
    assertionRules.value = []
    if (asserts.statusCode) {
      assertionRules.value.push({ tag: '状态码', op: '==', value: String(asserts.statusCode) })
    }
    if (asserts.timeoutMs) {
      assertionRules.value.push({ tag: '响应时间', op: '<=', value: `${asserts.timeoutMs}ms` })
    }
    const jsonpath = Array.isArray(asserts.jsonpath) ? asserts.jsonpath : []
    for (const jp of jsonpath) {
      assertionRules.value.push({ tag: 'JSONPath', op: jp.op || '==', value: `${jp.path} -> ${jp.value}` })
    }
    if (assertionRules.value.length === 0) {
      assertionRules.value = [{ tag: '状态码', op: '==', value: '200' }]
    }

    // Reset response
    responseStatusCode.value = null
    responseStatusText.value = ''
    responseTime.value = null
    responseBody.value = ''
    responseError.value = ''
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '加载请求失败'
    request.value = null
  } finally {
    loading.value = false
  }
}

async function handleSend() {
  if (!props.collectionId || !props.requestId) return
  running.value = true
  responseError.value = ''
  activeTab.value = 'response'
  try {
    const result = await runCollectionRequest(props.collectionId, props.requestId)
    responseStatusCode.value = typeof result.status === 'number' ? result.status : null
    responseStatusText.value = result.status ? `${result.status} ${result.statusText || 'OK'}` : '未知'
    responseTime.value = typeof result.elapsed_ms === 'number' ? result.elapsed_ms : null
    if (typeof result.body === 'string') {
      responseBody.value = result.body
    } else if (result.body) {
      responseBody.value = JSON.stringify(result.body, null, 2)
    } else {
      responseBody.value = JSON.stringify(result, null, 2)
    }
  } catch (error) {
    responseError.value = error instanceof Error ? error.message : '请求执行失败'
  } finally {
    running.value = false
  }
}

async function handleSave() {
  if (!props.collectionId || !props.requestId) return
  saving.value = true
  try {
    const headers: Record<string, string> = {}
    for (const h of requestHeaders.value) {
      if (h.key.trim()) headers[h.key.trim()] = h.value
    }

    let body: Record<string, unknown> = {}
    if (requestBody.value.trim()) {
      try { body = JSON.parse(requestBody.value) } catch { body = { _raw: requestBody.value } }
    }

    const asserts: Record<string, unknown> = {}
    for (const rule of assertionRules.value) {
      if (rule.tag === '状态码' && rule.value) asserts.statusCode = Number(rule.value)
      if (rule.tag === '响应时间' && rule.value) asserts.timeoutMs = Number(rule.value.replace('ms', ''))
    }

    await updateCollectionRequest(props.collectionId, props.requestId, {
      name: request.value?.name || '',
      method: method.value,
      url: url.value,
      headers,
      auth: { type: authType.value, token: authToken.value },
      body,
      asserts
    })
  } catch (error) {
    // save error is non-blocking
  } finally {
    saving.value = false
  }
}

function addHeader() {
  requestHeaders.value.push({ key: '', value: '' })
}

function removeHeader(index: number) {
  requestHeaders.value.splice(index, 1)
}

function addAssertion() {
  assertionRules.value.push({ tag: '', op: '', value: '' })
}

function removeAssertion(index: number) {
  assertionRules.value.splice(index, 1)
}

watch(() => [props.collectionId, props.requestId], () => {
  void loadRequest()
}, { immediate: true })
</script>

<template>
  <section class="flex w-full flex-col bg-white md:flex-1 md:min-w-0 md:h-full">
    <!-- Loading state -->
    <div v-if="loading" class="flex flex-1 items-center justify-center">
      <span class="text-[14px] text-[#717182]">加载中...</span>
    </div>

    <!-- Empty state -->
    <div v-else-if="!request && !loadError" class="flex flex-1 items-center justify-center">
      <span class="text-[14px] text-[#717182]">请从左侧选择一个接口</span>
    </div>

    <!-- Error state -->
    <div v-else-if="loadError" class="flex flex-1 items-center justify-center">
      <span class="text-[14px] text-[#E7000B]">{{ loadError }}</span>
    </div>

    <!-- Main content -->
    <template v-else>
      <!-- Method + URL + Send -->
      <div class="flex h-[60.67px] w-full items-center gap-[8px] border-b-[0.6667px] border-black/10 px-[12px]">
        <div
          class="flex h-[36px] w-[88.67px] items-center justify-center rounded-[10px] border border-black/10"
          :style="{ background: currentMethodColor.bg }"
        >
          <span class="text-[12px] font-medium leading-[16px]" :style="{ color: currentMethodColor.fg }" style="font-family: Consolas">{{ method }}</span>
        </div>

        <div class="flex h-[36px] min-w-0 flex-1 items-center rounded-[10px] border border-black/10 bg-white px-[12px]">
          <input
            v-model="url"
            class="h-full w-full min-w-0 bg-transparent text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            style="font-family: Consolas"
            type="text"
            placeholder="请求 URL"
          />
        </div>

        <button
          type="button"
          class="relative flex h-[36px] w-[79px] items-center justify-center rounded-[10px] bg-[#155DFC]"
          :disabled="running"
          @click="handleSend"
        >
          <img :src="apiSend" alt="" class="mr-[4px] h-[13px] w-[13px]" />
          <span class="text-[14px] font-medium leading-[20px] text-white">{{ running ? '发送中...' : '发送' }}</span>
        </button>

        <button
          type="button"
          class="flex h-[36px] items-center justify-center rounded-[10px] border border-black/10 px-[12px]"
          :disabled="saving"
          @click="handleSave"
        >
          <span class="text-[12px] font-medium leading-[16px] text-[#717182]">{{ saving ? '保存中...' : '保存' }}</span>
        </button>
      </div>

      <!-- Tabs -->
      <div class="flex h-[38.67px] w-full items-center gap-[4px] border-b-[0.6667px] border-black/10 pl-[12px]">
        <button
          type="button"
          class="flex h-[38px] w-[80px] items-center justify-center border-b-[2px]"
          :class="activeTab === 'request' ? 'border-[#155DFC]' : 'border-transparent'"
          @click="activeTab = 'request'"
        >
          <span class="text-[12px] font-medium leading-[16px]" :class="activeTab === 'request' ? 'text-[#155DFC]' : 'text-[#717182]'">请求配置</span>
        </button>
        <button
          type="button"
          class="flex h-[38px] w-[80px] items-center justify-center border-b-[2px]"
          :class="activeTab === 'assert' ? 'border-[#155DFC]' : 'border-transparent'"
          @click="activeTab = 'assert'"
        >
          <span class="text-[12px] font-medium leading-[16px]" :class="activeTab === 'assert' ? 'text-[#155DFC]' : 'text-[#717182]'">断言模板</span>
        </button>
        <button
          type="button"
          class="flex h-[38px] items-center justify-center border-b-[2px] px-[16px]"
          :class="activeTab === 'response' ? 'border-[#155DFC]' : 'border-transparent'"
          @click="activeTab = 'response'"
        >
          <span class="text-[12px] font-medium leading-[16px]" :class="activeTab === 'response' ? 'text-[#155DFC]' : 'text-[#717182]'">响应结果</span>
          <span
            v-if="activeTab === 'response' && responseStatusCode"
            class="ml-[6px] rounded-full px-[6px] py-[2px] text-[12px] font-medium leading-[16px]"
            :class="responseStatusCode >= 200 && responseStatusCode < 300 ? 'bg-[#DCFCE7] text-[#008236]' : 'bg-[#FFE2E2] text-[#E7000B]'"
          >
            {{ responseStatusCode }}
          </span>
        </button>
      </div>

      <!-- Request tab -->
      <div v-if="activeTab === 'request'" class="flex flex-1 flex-col gap-[16px] overflow-auto p-[16px] pr-[32.67px]">
        <!-- Headers -->
        <div class="flex flex-col gap-[8px]">
          <div class="flex items-center justify-between">
            <div class="text-left text-[12px] font-medium leading-[16px] text-[#717182]">请求头</div>
            <button type="button" class="text-[12px] font-medium leading-[16px] text-[#155DFC]" @click="addHeader">+ 添加</button>
          </div>

          <div class="w-full overflow-hidden rounded-[10px] border border-black/10 bg-white">
            <div
              v-for="(header, index) in requestHeaders"
              :key="index"
              class="flex h-[32px] w-full items-center"
              :class="index !== requestHeaders.length - 1 ? 'border-b-[0.6667px] border-black/10' : ''"
            >
              <div class="flex h-full w-[148px] items-center border-r border-black/10 px-[12px]">
                <input
                  v-model="header.key"
                  class="h-full w-full bg-transparent text-[12px] leading-[16px] text-[#0A0A0A] outline-none"
                  style="font-family: Consolas"
                  type="text"
                  placeholder="Key"
                />
              </div>
              <div class="flex min-w-0 flex-1 items-center px-[12px]">
                <input
                  v-model="header.value"
                  class="h-full w-full min-w-0 bg-transparent text-[12px] leading-[16px] text-[#717182] outline-none"
                  style="font-family: Consolas"
                  type="text"
                  placeholder="Value"
                />
              </div>
              <button type="button" class="flex h-[32px] w-[32px] items-center justify-center text-[#717182]" @click="removeHeader(index)">
                &times;
              </button>
            </div>
          </div>
        </div>

        <!-- Auth -->
        <div class="flex flex-col gap-[8px]">
          <div class="text-left text-[12px] font-medium leading-[16px] text-[#717182]">鉴权</div>
          <div class="flex items-center gap-[8px]">
            <div class="flex h-[36px] w-[120px] items-center justify-center rounded-[10px] border border-black/10 bg-white">
              <input v-model="authType" class="h-full w-full bg-transparent text-center text-[12px] font-medium leading-[16px] text-[#0A0A0A] outline-none" type="text" />
            </div>
            <div class="flex h-[36px] min-w-0 flex-1 items-center rounded-[10px] border border-black/10 bg-white px-[12px]">
              <input
                v-model="authToken"
                class="h-full w-full min-w-0 bg-transparent text-[12px] leading-[16px] text-[#0A0A0A] outline-none"
                style="font-family: Consolas"
                type="text"
                placeholder="Token"
              />
            </div>
          </div>
        </div>

        <!-- Body -->
        <div class="flex flex-col gap-[8px]">
          <div class="flex items-center justify-between">
            <div class="text-left text-[12px] font-medium leading-[16px] text-[#717182]">请求体 (JSON)</div>
            <button type="button" class="flex items-center gap-[6px]">
              <img :src="apiExportCurl" alt="" class="h-[12px] w-[12px]" />
              <span class="text-[12px] font-medium leading-[16px] text-[#717182]">导出 cURL</span>
            </button>
          </div>

          <textarea
            v-model="requestBody"
            class="min-h-[209.33px] w-full resize-none rounded-[10px] border border-black/10 bg-white px-[12px] py-[8px] text-[12px] leading-[16px] text-[#0A0A0A] outline-none"
            style="font-family: Consolas"
            placeholder='{"key": "value"}'
          />
        </div>
      </div>

      <!-- Assert tab -->
      <div v-else-if="activeTab === 'assert'" class="flex flex-1 flex-col gap-[16px] overflow-auto p-[16px]">
        <div class="flex items-center justify-between">
          <div class="text-[12px] font-medium leading-[16px] text-[#717182]">断言规则</div>
          <button type="button" class="flex items-center gap-[6px]" @click="addAssertion">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path d="M6 2V10" stroke="#155DFC" stroke-width="1.08333" stroke-linecap="round" stroke-linejoin="round" />
              <path d="M2 6H10" stroke="#155DFC" stroke-width="1.08333" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="text-[12px] font-medium leading-[16px] text-[#155DFC]">添加断言</span>
          </button>
        </div>

        <div class="flex flex-col gap-[12px]">
          <div
            v-for="(rule, index) in assertionRules"
            :key="index"
            class="flex items-center gap-[12px] rounded-[10px] border border-black/10 px-[12px]"
            style="height:45.33px"
          >
            <input
              v-model="rule.tag"
              class="h-[20px] w-[84px] rounded-[4px] bg-[#F3F4F6] px-[8px] text-[12px] leading-[16px] text-[#4A5565] outline-none"
              type="text"
              placeholder="类型"
            />

            <input
              v-model="rule.op"
              class="h-[16px] w-[60px] bg-transparent text-[12px] leading-[16px] text-[#717182] outline-none"
              style="font-family: Consolas"
              type="text"
              placeholder="op"
            />

            <input
              v-model="rule.value"
              class="h-[16px] min-w-0 flex-1 bg-transparent text-[12px] leading-[16px] text-[#0A0A0A] outline-none"
              style="font-family: Consolas"
              type="text"
              placeholder="值"
            />

            <button type="button" class="flex h-[13px] w-[13px] items-center justify-center text-[#717182]" @click="removeAssertion(index)">
              &times;
            </button>
          </div>
        </div>
      </div>

      <!-- Response tab -->
      <div v-else class="flex flex-1 flex-col gap-[12px] overflow-auto p-[16px]">
        <div class="flex items-center justify-between" style="height:24px">
          <div class="flex items-center gap-[4px]">
            <template v-if="responseStatusCode">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path
                  d="M13.3333 4L6.66666 10.6667L3.33333 7.33333"
                  :stroke="responseStatusCode >= 200 && responseStatusCode < 300 ? '#00A63E' : '#E7000B'"
                  stroke-width="1.33333"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
              <div
                class="text-[14px] font-semibold leading-[20px]"
                :class="responseStatusCode >= 200 && responseStatusCode < 300 ? 'text-[#00A63E]' : 'text-[#E7000B]'"
              >
                {{ responseStatusText }}
              </div>
            </template>
            <span v-else class="text-[14px] text-[#717182]">尚未发送请求</span>
            <div v-if="responseTime !== null" class="ml-[8px] text-[12px] leading-[16px] text-[#717182]">{{ responseTime }}ms</div>
          </div>

          <div class="flex h-[24px] items-center gap-[4px]">
            <button type="button" class="h-[24px] rounded-[4px] bg-[#DBEAFE] px-[8px] text-[12px] font-medium leading-[16px] text-[#1447E6]">响应体</button>
          </div>
        </div>

        <div v-if="responseError" class="w-full rounded-[14px] bg-[#FFE2E2] p-[16px]">
          <pre class="whitespace-pre-wrap text-[12px] leading-[16px] text-[#E7000B]" style="font-family: Consolas">{{ responseError }}</pre>
        </div>

        <div v-else-if="responseBody" class="w-full rounded-[14px] bg-[rgba(236,236,240,0.5)] p-[16px]" style="min-height:208px">
          <pre class="whitespace-pre-wrap text-[12px] leading-[16px] text-[rgba(10,10,10,0.8)]" style="font-family: Consolas">{{ responseBody }}</pre>
        </div>

        <div v-else-if="running" class="flex items-center justify-center py-[40px]">
          <span class="text-[14px] text-[#717182]">请求执行中...</span>
        </div>
      </div>
    </template>
  </section>
</template>
