<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import apiSend from '@/assets/figma/ai-testing-platform/api-send.svg'
import apiRowRemove1 from '@/assets/figma/ai-testing-platform/api-row-remove-1.svg'
import apiRowRemove2 from '@/assets/figma/ai-testing-platform/api-row-remove-2.svg'
import apiRowRemove3 from '@/assets/figma/ai-testing-platform/api-row-remove-3.svg'
import apiExportCurl from '@/assets/figma/ai-testing-platform/api-export-curl.svg'
import { fetchCollectionRequest, type CollectionRequest } from '@/lib/aiTestingPlatformApi'

const props = defineProps<{
  collectionId: string
  requestId: string
}>()

type TabKey = 'request' | 'assert' | 'response'
const activeTab = ref<TabKey>('request')
const loading = ref(false)
const loadError = ref('')
const requestData = ref<CollectionRequest | null>(null)

const requestHeaders = computed(() => {
  const h = requestData.value?.headers || {}
  return Object.entries(h).map(([key, value], index) => ({
    key,
    value: String(value),
    removeIcon: [apiRowRemove1, apiRowRemove2, apiRowRemove3][index % 3]
  }))
})

const authType = computed(() => {
  const auth = requestData.value?.auth || {}
  if (auth.type) return String(auth.type)
  if (auth.token) return 'Bearer'
  return ''
})

const authToken = computed(() => {
  const auth = requestData.value?.auth || {}
  if (auth.token) return String(auth.token)
  return ''
})

const requestBody = computed(() => {
  const body = requestData.value?.body
  if (!body || Object.keys(body).length === 0) return ''
  try {
    return JSON.stringify(body, null, 2)
  } catch {
    return String(body)
  }
})

const assertionRules = computed(() => {
  const asserts = requestData.value?.asserts || {}
  const rules: Array<{ tag: string; op: string; value: string }> = []
  if (asserts.statusCode) {
    rules.push({ tag: '状态码', op: '==', value: String(asserts.statusCode) })
  }
  if (asserts.jsonPath) {
    rules.push({ tag: 'JSONPath', op: 'exists', value: String(asserts.jsonPath) })
  }
  if (rules.length === 0) {
    rules.push({ tag: '状态码', op: '==', value: '200' })
  }
  return rules
})

const methodStyle = computed(() => {
  const m = (requestData.value?.method || 'GET').toUpperCase()
  if (m === 'GET') return { bg: '#F0FDF4', fg: '#00A63E' }
  if (m === 'PUT') return { bg: '#FEFCE8', fg: '#D08700' }
  if (m === 'PATCH') return { bg: '#FFEDD4', fg: '#F54900' }
  if (m === 'DELETE') return { bg: '#FFE2E2', fg: '#E7000B' }
  return { bg: '#EFF6FF', fg: '#155DFC' }
})

async function loadRequest() {
  if (!props.collectionId || !props.requestId) {
    requestData.value = null
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    requestData.value = await fetchCollectionRequest(props.collectionId, props.requestId)
  } catch (err: any) {
    loadError.value = err.message || '加载接口详情失败'
  } finally {
    loading.value = false
  }
}

watch(() => [props.collectionId, props.requestId], () => {
  loadRequest()
}, { immediate: true })

function addAssertion() {
  // assertionRules is computed, so add is a no-op until asserts are editable
}
</script>

<template>
  <section class="flex w-full flex-col bg-white md:flex-1 md:min-w-0 md:h-full">
    <!-- No selection placeholder -->
    <div v-if="!requestId" class="flex flex-1 items-center justify-center text-[14px] text-[#717182]">
      请在左侧选择一个接口查看详情
    </div>

    <!-- Loading -->
    <div v-else-if="loading" class="flex flex-1 items-center justify-center text-[14px] text-[#717182]">
      加载中...
    </div>

    <!-- Error -->
    <div v-else-if="loadError" class="flex flex-1 items-center justify-center text-[14px] text-[#E7000B]">
      {{ loadError }}
    </div>

    <!-- Request detail -->
    <template v-else-if="requestData">
      <div class="flex h-[60.67px] w-full items-center gap-[8px] border-b-[0.6667px] border-black/10 px-[12px]">
        <div class="flex h-[36px] w-[88.67px] items-center justify-center rounded-[10px] border border-black/10" :style="{ background: methodStyle.bg }">
          <span class="text-[12px] font-medium leading-[16px]" :style="{ color: methodStyle.fg, fontFamily: 'Consolas' }">{{ requestData.method }}</span>
        </div>

        <div class="flex h-[36px] min-w-0 flex-1 items-center rounded-[10px] border border-black/10 bg-white px-[12px]">
          <span class="truncate text-[14px] leading-[20px] text-[#0A0A0A]" style="font-family: Consolas">
            {{ requestData.url }}
          </span>
        </div>

        <button type="button" class="relative h-[36px] w-[79px] rounded-[10px] bg-[#155DFC]">
          <img :src="apiSend" alt="" class="absolute left-[16px] top-[11.5px] h-[13px] w-[13px]" />
          <span class="absolute left-[35px] top-[8.33px] text-[14px] font-medium leading-[20px] text-white">发送</span>
        </button>
      </div>

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
        </button>
      </div>

      <div v-if="activeTab === 'request'" class="flex flex-1 flex-col gap-[16px] overflow-auto p-[16px] pr-[32.67px]">
        <div class="flex flex-col gap-[8px]">
          <div class="w-full text-left text-[12px] font-medium leading-[16px] text-[#717182]">请求头</div>

          <div v-if="requestHeaders.length > 0" class="w-full overflow-hidden rounded-[10px] border border-black/10 bg-white">
            <div
              v-for="(header, index) in requestHeaders"
              :key="`${header.key}-${index}`"
              class="flex h-[32px] w-full items-center"
              :class="index !== requestHeaders.length - 1 ? 'border-b-[0.6667px] border-black/10' : ''"
            >
              <div class="flex h-full w-[148px] items-center border-r border-black/10 px-[12px]">
                <input
                  :value="header.key"
                  class="h-full w-full bg-transparent text-[12px] leading-[16px] text-[#0A0A0A] outline-none"
                  style="font-family: Consolas"
                  type="text"
                  readonly
                />
              </div>
              <div class="flex min-w-0 flex-1 items-center px-[12px]">
                <input
                  :value="header.value"
                  class="h-full w-full min-w-0 bg-transparent text-[12px] leading-[16px] text-[#717182] outline-none"
                  style="font-family: Consolas"
                  type="text"
                  readonly
                />
              </div>
            </div>
          </div>
          <div v-else class="text-[12px] text-[#717182]">暂无请求头</div>
        </div>

        <div v-if="authType" class="flex flex-col gap-[8px]">
          <div class="w-full text-left text-[12px] font-medium leading-[16px] text-[#717182]">鉴权</div>
          <div class="flex items-center gap-[8px]">
            <div class="flex h-[36px] w-[120px] items-center justify-center rounded-[10px] border border-black/10 bg-white">
              <input :value="authType" class="h-full w-full bg-transparent text-center text-[12px] font-medium leading-[16px] text-[#0A0A0A] outline-none" type="text" readonly />
            </div>
            <div class="flex h-[36px] min-w-0 flex-1 items-center rounded-[10px] border border-black/10 bg-white px-[12px]">
              <input
                :value="authToken"
                class="h-full w-full min-w-0 bg-transparent text-[12px] leading-[16px] text-[#0A0A0A] outline-none"
                style="font-family: Consolas"
                type="text"
                readonly
              />
            </div>
          </div>
        </div>

        <div class="flex flex-col gap-[8px]">
          <div class="flex items-center justify-between">
            <div class="text-left text-[12px] font-medium leading-[16px] text-[#717182]">请求体 (JSON)</div>
            <button type="button" class="flex items-center gap-[6px]">
              <img :src="apiExportCurl" alt="" class="h-[12px] w-[12px]" />
              <span class="text-[12px] font-medium leading-[16px] text-[#717182]">导出 cURL</span>
            </button>
          </div>

          <textarea
            :value="requestBody"
            class="min-h-[209.33px] w-full resize-none rounded-[10px] border border-black/10 bg-white px-[12px] py-[8px] text-[12px] leading-[16px] text-[#0A0A0A] outline-none"
            style="font-family: Consolas"
            readonly
          />
        </div>
      </div>

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

        <div v-if="assertionRules.length > 0" class="flex flex-col gap-[12px]">
          <div
            v-for="(rule, index) in assertionRules"
            :key="`${rule.tag}-${rule.op}-${rule.value}-${index}`"
            class="flex items-center gap-[12px] rounded-[10px] border border-black/10 px-[12px]"
            style="height:45.33px"
          >
            <div class="h-[13px] w-[13px] rounded-[3px] border border-black/10 bg-white" />

            <input
              :value="rule.tag"
              class="h-[20px] w-[84px] rounded-[4px] bg-[#F3F4F6] px-[8px] text-[12px] leading-[16px] text-[#4A5565] outline-none"
              type="text"
              readonly
            />

            <input
              :value="rule.op"
              class="h-[16px] w-[60px] bg-transparent text-[12px] leading-[16px] text-[#717182] outline-none"
              style="font-family: Consolas"
              type="text"
              readonly
            />

            <input
              :value="rule.value"
              class="h-[16px] min-w-0 flex-1 bg-transparent text-[12px] leading-[16px] text-[#0A0A0A] outline-none"
              style="font-family: Consolas"
              type="text"
              readonly
            />
          </div>
        </div>
        <div v-else class="text-[12px] text-[#717182]">暂无断言规则</div>

        <div class="relative h-[41.33px] w-full rounded-[10px] border border-[#BEDBFF] bg-[#EFF6FF]">
          <div class="absolute left-[12.67px] top-1/2 -translate-y-1/2 h-[13px] w-[13px]">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path
                d="M6.5 11.5C9.26142 11.5 11.5 9.26142 11.5 6.5C11.5 3.73858 9.26142 1.5 6.5 1.5C3.73858 1.5 1.5 3.73858 1.5 6.5C1.5 9.26142 3.73858 11.5 6.5 11.5Z"
                stroke="#1447E6"
                stroke-width="1.08333"
              />
              <path d="M6.5 5.75V9" stroke="#1447E6" stroke-width="1.08333" stroke-linecap="round" />
              <path d="M6.5 4.0625H6.505" stroke="#1447E6" stroke-width="1.08333" stroke-linecap="round" />
            </svg>
          </div>
          <div class="absolute left-[33.67px] top-[12.67px] text-[12px] leading-[16px] text-[#1447E6]">
            预置常见校验：状态码、关键字段存在性、响应时间阈值
          </div>
        </div>
      </div>

      <div v-else class="flex flex-1 flex-col items-center justify-center gap-[12px] overflow-auto p-[16px]">
        <div class="text-[14px] text-[#717182]">点击"发送"按钮执行请求后查看响应结果</div>
      </div>
    </template>
  </section>
</template>
