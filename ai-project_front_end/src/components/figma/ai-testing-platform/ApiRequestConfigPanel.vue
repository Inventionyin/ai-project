<script setup lang="ts">
import { computed, ref } from 'vue'
import apiSend from '@/assets/figma/ai-testing-platform/api-send.svg'
import apiRowRemove1 from '@/assets/figma/ai-testing-platform/api-row-remove-1.svg'
import apiRowRemove2 from '@/assets/figma/ai-testing-platform/api-row-remove-2.svg'
import apiRowRemove3 from '@/assets/figma/ai-testing-platform/api-row-remove-3.svg'
import apiExportCurl from '@/assets/figma/ai-testing-platform/api-export-curl.svg'

type TabKey = 'request' | 'assert' | 'response'
type ResponseTabKey = 'body' | 'headers'
const activeTab = ref<TabKey>('request')
const activeResponseTab = ref<ResponseTabKey>('body')
const actionMessage = ref('')

const responseStatusCode = 200

const responseStatusText = computed(() => `${responseStatusCode} OK`)

const requestHeaders = ref([
  { key: 'Content-Type', value: 'application/json', removeIcon: apiRowRemove1 },
  { key: 'Authorization', value: 'Bearer {{token}}', removeIcon: apiRowRemove2 },
  { key: 'X-Tenant-Id', value: '{{tenantId}}', removeIcon: apiRowRemove3 }
])

const authType = ref('Bearer')
const authToken = ref('{{authToken}}')

const requestBody = ref('')

const assertionRules = ref<Array<{ tag: string; op: string; value: string }>>([
  { tag: '状态码', op: '==', value: '200' },
  { tag: 'JSONPath', op: 'exists', value: '$.data.orderId' },
  { tag: 'JSONPath', op: '==', value: '$.code → 0' },
  { tag: 'JSON Schema', op: 'validates', value: 'OrderSchema v1' },
  { tag: '响应时间', op: '<=', value: '2000ms' }
])

function removeHeader(index: number) {
  requestHeaders.value.splice(index, 1)
}

function addAssertion() {
  assertionRules.value.push({ tag: '', op: '', value: '' })
}

function removeAssertion(index: number) {
  assertionRules.value.splice(index, 1)
}

function sendRequest() {
  activeTab.value = 'response'
  activeResponseTab.value = 'body'
  actionMessage.value = '请求已发送，响应结果已更新'
}

function buildCurlCommand() {
  const headers = requestHeaders.value
    .filter((item) => item.key.trim())
    .map((item) => `-H "${item.key.trim()}: ${item.value.trim()}"`)
    .join(' ')
  const body = requestBody.value.trim() ? ` -d '${requestBody.value.trim()}'` : ''
  return `curl -X POST "{{baseUrl}}/api/v2/orders" ${headers}${body}`.trim()
}

async function exportCurl() {
  const curl = buildCurlCommand()
  try {
    await navigator.clipboard?.writeText(curl)
    actionMessage.value = 'cURL 已复制'
  } catch {
    const blob = new Blob([curl], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'orders-request.curl.txt'
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    actionMessage.value = 'cURL 已导出'
  }
}
</script>

<template>
  <section class="flex w-full flex-col bg-white md:flex-1 md:min-w-0 md:h-full">
    <div class="flex h-[60.67px] w-full items-center gap-[8px] border-b-[0.6667px] border-black/10 px-[12px]">
      <div class="flex h-[36px] w-[88.67px] items-center justify-center rounded-[10px] border border-black/10 bg-[#EFF6FF]">
        <span class="text-[12px] font-medium leading-[16px] text-[#155DFC]" style="font-family: Consolas">POST</span>
      </div>

      <div class="flex h-[36px] min-w-0 flex-1 items-center rounded-[10px] border border-black/10 bg-white px-[12px]">
        <span v-pre class="truncate text-[14px] leading-[20px] text-[#0A0A0A]" style="font-family: Consolas">
          {{baseUrl}}/api/v2/orders
        </span>
      </div>

      <button type="button" class="relative h-[36px] w-[79px] rounded-[10px] bg-[#155DFC]" @click="sendRequest">
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
        <span
          v-if="activeTab === 'response'"
          class="ml-[6px] rounded-full bg-[#DCFCE7] px-[6px] py-[2px] text-[12px] font-medium leading-[16px] text-[#008236]"
        >
          {{ responseStatusCode }}
        </span>
      </button>
    </div>

    <div v-if="activeTab === 'request'" class="flex flex-1 flex-col gap-[16px] overflow-auto p-[16px] pr-[32.67px]">
      <div class="flex flex-col gap-[8px]">
        <div class="w-full text-left text-[12px] font-medium leading-[16px] text-[#717182]">请求头</div>

        <div class="w-full overflow-hidden rounded-[10px] border border-black/10 bg-white">
          <div
            v-for="(header, index) in requestHeaders"
            :key="`${header.key}-${index}`"
            class="flex h-[32px] w-full items-center"
            :class="index !== requestHeaders.length - 1 ? 'border-b-[0.6667px] border-black/10' : ''"
          >
            <div class="flex h-full w-[148px] items-center border-r border-black/10 px-[12px]">
              <input
                v-model="header.key"
                class="h-full w-full bg-transparent text-[12px] leading-[16px] text-[#0A0A0A] outline-none"
                style="font-family: Consolas"
                type="text"
              />
            </div>
            <div class="flex min-w-0 flex-1 items-center px-[12px]">
              <input
                v-model="header.value"
                class="h-full w-full min-w-0 bg-transparent text-[12px] leading-[16px] text-[#717182] outline-none"
                style="font-family: Consolas"
                type="text"
              />
            </div>
            <button type="button" class="flex h-[32px] w-[32px] items-center justify-center" @click="removeHeader(index)">
              <img :src="header.removeIcon" alt="" class="h-[32px] w-[32px]" />
            </button>
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-[8px]">
        <div class="w-full text-left text-[12px] font-medium leading-[16px] text-[#717182]">鉴权</div>
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
            />
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-[8px]">
        <div class="flex items-center justify-between">
          <div class="text-left text-[12px] font-medium leading-[16px] text-[#717182]">请求体 (JSON)</div>
          <button type="button" class="flex items-center gap-[6px] rounded-[4px] px-[4px] hover:bg-[#F8FAFC]" @click="exportCurl">
            <img :src="apiExportCurl" alt="" class="h-[12px] w-[12px]" />
            <span class="text-[12px] font-medium leading-[16px] text-[#717182]">导出 cURL</span>
          </button>
        </div>

        <div v-if="actionMessage" role="status" class="rounded-[8px] border border-[#BFDBFE] bg-[#EFF6FF] px-[12px] py-[8px] text-[12px] text-[#155DFC]">
          {{ actionMessage }}
        </div>

        <textarea
          v-model="requestBody"
          class="min-h-[209.33px] w-full resize-none rounded-[10px] border border-black/10 bg-white px-[12px] py-[8px] text-[12px] leading-[16px] text-[#0A0A0A] outline-none"
          style="font-family: Consolas"
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

      <div class="flex flex-col gap-[12px]">
        <div
          v-for="(rule, index) in assertionRules"
          :key="`${rule.tag}-${rule.op}-${rule.value}-${index}`"
          class="flex items-center gap-[12px] rounded-[10px] border border-black/10 px-[12px]"
          style="height:45.33px"
        >
          <div class="h-[13px] w-[13px] rounded-[3px] border border-black/10 bg-white" />

          <input
            v-model="rule.tag"
            class="h-[20px] w-[84px] rounded-[4px] bg-[#F3F4F6] px-[8px] text-[12px] leading-[16px] text-[#4A5565] outline-none"
            type="text"
          />

          <input
            v-model="rule.op"
            class="h-[16px] w-[60px] bg-transparent text-[12px] leading-[16px] text-[#717182] outline-none"
            style="font-family: Consolas"
            type="text"
          />

          <input
            v-model="rule.value"
            class="h-[16px] min-w-0 flex-1 bg-transparent text-[12px] leading-[16px] text-[#0A0A0A] outline-none"
            style="font-family: Consolas"
            type="text"
          />

          <button type="button" class="flex h-[13px] w-[13px] items-center justify-center" @click="removeAssertion(index)">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path d="M3.25 3.25L9.75 9.75" stroke="#717182" stroke-width="1.08333" stroke-linecap="round" stroke-linejoin="round" />
              <path d="M9.75 3.25L3.25 9.75" stroke="#717182" stroke-width="1.08333" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
        </div>

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
    </div>

    <div v-else class="flex flex-1 flex-col gap-[12px] overflow-auto p-[16px]">
      <div class="flex items-center justify-between" style="height:24px">
        <div class="flex items-center gap-[4px]">
          <div class="flex items-center gap-[4px]">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path
                d="M13.3333 4L6.66666 10.6667L3.33333 7.33333"
                stroke="#00A63E"
                stroke-width="1.33333"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            <div class="text-[14px] font-semibold leading-[20px] text-[#00A63E]">{{ responseStatusText }}</div>
          </div>
          <div class="ml-[8px] text-[12px] leading-[16px] text-[#717182]">238ms</div>
        </div>

        <div class="flex h-[24px] items-center gap-[4px]">
          <button
            type="button"
            class="h-[24px] rounded-[4px] px-[8px] text-[12px] font-medium leading-[16px]"
            :class="activeResponseTab === 'body' ? 'bg-[#DBEAFE] text-[#1447E6]' : 'text-[#717182]'"
            @click="activeResponseTab = 'body'"
          >
            响应体
          </button>
          <button
            type="button"
            class="h-[24px] rounded-[4px] px-[8px] text-[12px] font-medium leading-[16px]"
            :class="activeResponseTab === 'headers' ? 'bg-[#DBEAFE] text-[#1447E6]' : 'text-[#717182]'"
            @click="activeResponseTab = 'headers'"
          >
            响应头
          </button>
        </div>
      </div>

      <div class="w-full rounded-[14px] bg-[rgba(236,236,240,0.5)] p-[16px]" style="height:208px">
        <pre v-if="activeResponseTab === 'body'" class="whitespace-pre-wrap text-[12px] leading-[16px] text-[rgba(10,10,10,0.8)]" style="font-family: Consolas">{{
`{
  "code": 0,
  "message": "ok",
  "data": {
    "orderId": "ORD-2024031412345",
    "status": "PENDING",
    "totalAmount": 299,
    "createdAt": "2024-03-14T12:00:00Z"
  },
  "requestId": "req_abc123"
}` }}</pre>
        <pre v-else class="whitespace-pre-wrap text-[12px] leading-[16px] text-[rgba(10,10,10,0.8)]" style="font-family: Consolas">{{
`content-type: application/json
x-request-id: req_abc123
x-response-time: 238ms` }}</pre>
      </div>
    </div>
  </section>
</template>
