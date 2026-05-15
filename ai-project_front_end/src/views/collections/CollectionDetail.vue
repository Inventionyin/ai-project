<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  exportCollection,
  fetchCollectionDetail,
  fetchCollectionRequestDetail,
  importCollection,
  runCollectionRequest,
  updateCollectionRequest,
  type CollectionDetail
} from '@/lib/api/collections'

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

type RequestForm = {
  requestId: string
  groupId: string
  name: string
  method: Method
  url: string
  headersText: string
  authText: string
  bodyText: string
  assertsText: string
}

const route = useRoute()

const projectId = computed(() => String(route.params.projectId || '').trim())
const collectionId = computed(() => String(route.params.id || '').trim())
const requestIdFromQuery = computed(() => String(route.query.requestId || '').trim())

const loading = ref(false)
const saving = ref(false)
const running = ref(false)
const importSubmitting = ref(false)
const exporting = ref(false)

const error = ref('')
const success = ref('')
const runResultText = ref('')
const exportText = ref('')

const detail = ref<CollectionDetail | null>(null)
const selectedRequestId = ref('')
const requestForm = ref<RequestForm | null>(null)

const importFormat = ref<'postman' | 'swagger'>('postman')
const importContent = ref('')

const allRequests = computed(() => {
  const d = detail.value
  if (!d) return []
  const grouped = d.groups.flatMap((g) => g.requests.map((r) => ({ ...r, groupName: g.name })))
  const ungrouped = d.requests.map((r) => ({ ...r, groupName: '未分组' }))
  return [...grouped, ...ungrouped]
})

function formatJson(data: unknown) {
  return JSON.stringify(data ?? {}, null, 2)
}

function parseJsonOrThrow(text: string, label: string) {
  const trimmed = String(text || '').trim()
  if (!trimmed) return {}
  try {
    const parsed = JSON.parse(trimmed)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error(`${label} 必须是 JSON 对象`)
    }
    return parsed as Record<string, unknown>
  } catch {
    throw new Error(`${label} 不是合法 JSON`)
  }
}

function toMethod(value: string): Method {
  const upper = String(value || '').toUpperCase()
  if (upper === 'GET' || upper === 'POST' || upper === 'PUT' || upper === 'PATCH' || upper === 'DELETE') return upper
  return 'GET'
}

async function loadCollection() {
  if (!collectionId.value) return
  loading.value = true
  error.value = ''
  success.value = ''
  runResultText.value = ''
  try {
    const data = await fetchCollectionDetail(collectionId.value)
    detail.value = data
    const candidate = requestIdFromQuery.value || selectedRequestId.value || allRequests.value[0]?.id || ''
    selectedRequestId.value = candidate
    if (candidate) {
      await loadRequestDetail(candidate)
    } else {
      requestForm.value = null
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '集合加载失败'
  } finally {
    loading.value = false
  }
}

async function loadRequestDetail(requestId: string) {
  if (!collectionId.value || !requestId) return
  error.value = ''
  try {
    const data = await fetchCollectionRequestDetail(collectionId.value, requestId)
    requestForm.value = {
      requestId: data.id,
      groupId: data.groupId || '',
      name: data.name,
      method: toMethod(data.method),
      url: data.url,
      headersText: formatJson(data.headers),
      authText: formatJson(data.auth),
      bodyText: formatJson(data.body),
      assertsText: formatJson(data.asserts)
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '请求详情加载失败'
  }
}

async function onSelectRequest(requestId: string) {
  selectedRequestId.value = requestId
  success.value = ''
  runResultText.value = ''
  await loadRequestDetail(requestId)
}

async function saveRequest() {
  if (!collectionId.value || !requestForm.value) return
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const payload = {
      groupId: requestForm.value.groupId || null,
      name: requestForm.value.name.trim(),
      method: requestForm.value.method,
      url: requestForm.value.url.trim(),
      headers: parseJsonOrThrow(requestForm.value.headersText, '请求头'),
      auth: parseJsonOrThrow(requestForm.value.authText, '鉴权'),
      body: parseJsonOrThrow(requestForm.value.bodyText, '请求体'),
      asserts: parseJsonOrThrow(requestForm.value.assertsText, '断言')
    }
    if (!payload.name) throw new Error('请求名称不能为空')
    if (!payload.url) throw new Error('请求 URL 不能为空')
    await updateCollectionRequest(collectionId.value, requestForm.value.requestId, payload)
    success.value = '保存成功'
    await loadCollection()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function runSingleRequest() {
  if (!collectionId.value || !requestForm.value) return
  running.value = true
  error.value = ''
  runResultText.value = ''
  try {
    const result = await runCollectionRequest(collectionId.value, requestForm.value.requestId, { envId: null })
    runResultText.value = JSON.stringify(result, null, 2)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '运行失败'
  } finally {
    running.value = false
  }
}

async function handleExport(format: 'postman' | 'swagger' | 'curl') {
  if (!collectionId.value) return
  exporting.value = true
  error.value = ''
  try {
    const data = await exportCollection(collectionId.value, format)
    exportText.value = data.content
    success.value = `导出成功（${data.format}）`
  } catch (e) {
    error.value = e instanceof Error ? e.message : '导出失败'
  } finally {
    exporting.value = false
  }
}

async function handleImport() {
  if (!projectId.value) return
  importSubmitting.value = true
  error.value = ''
  success.value = ''
  try {
    const content = String(importContent.value || '').trim()
    if (!content) throw new Error('导入内容不能为空')
    const created = await importCollection({
      projectId: projectId.value,
      format: importFormat.value,
      content
    })
    success.value = `导入成功：${created.name}`
    importContent.value = ''
    await loadCollection()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '导入失败'
  } finally {
    importSubmitting.value = false
  }
}

watch([collectionId, requestIdFromQuery], () => {
  void loadCollection()
}, { immediate: true })
</script>

<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-4">
    <div class="grid grid-cols-1 gap-4 xl:grid-cols-[300px_minmax(0,1fr)]">
      <section class="rounded-[10px] border border-black/10 bg-white">
        <div class="border-b border-black/10 px-4 py-3 text-[13px] font-semibold text-[#0A0A0A]">集合信息</div>
        <div class="space-y-3 p-4 text-[12px] leading-[16px] text-[#4A5565]">
          <div>项目：{{ projectId || '-' }}</div>
          <div>集合：{{ detail?.name || '-' }}</div>
          <div>请求数：{{ allRequests.length }}</div>
          <div>分组数：{{ detail?.groups?.length || 0 }}</div>
          <div class="rounded-[8px] bg-[#F8FAFC] p-2">
            <div class="mb-1 text-[#717182]">变量</div>
            <pre class="max-h-[160px] overflow-auto whitespace-pre-wrap text-[11px] text-[#0A0A0A]">{{ formatJson(detail?.variables || {}) }}</pre>
          </div>
        </div>
      </section>

      <section class="rounded-[10px] border border-black/10 bg-white">
        <div class="flex items-center justify-between border-b border-black/10 px-4 py-3">
          <div class="text-[13px] font-semibold text-[#0A0A0A]">Collection 详情</div>
          <div class="flex gap-2">
            <button class="rounded-[8px] border border-black/10 px-3 py-1 text-[12px]" :disabled="exporting" @click="handleExport('postman')">导出 Postman</button>
            <button class="rounded-[8px] border border-black/10 px-3 py-1 text-[12px]" :disabled="exporting" @click="handleExport('swagger')">导出 Swagger</button>
            <button class="rounded-[8px] border border-black/10 px-3 py-1 text-[12px]" :disabled="exporting" @click="handleExport('curl')">导出 cURL</button>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 p-4 xl:grid-cols-[280px_minmax(0,1fr)]">
          <aside class="space-y-3">
            <div class="rounded-[8px] border border-black/10 p-2">
              <div class="mb-2 text-[12px] font-medium text-[#717182]">分组树 / 请求列表</div>
              <div v-if="loading" class="text-[12px] text-[#717182]">加载中...</div>
              <div v-else class="max-h-[420px] space-y-2 overflow-auto">
                <div v-for="group in detail?.groups || []" :key="group.id">
                  <div class="px-2 text-[12px] font-medium text-[#4A5565]">{{ group.name }}</div>
                  <button
                    v-for="req in group.requests"
                    :key="req.id"
                    class="mt-1 block w-full rounded-[6px] px-2 py-1 text-left text-[12px]"
                    :class="selectedRequestId === req.id ? 'bg-[#EFF6FF] text-[#155DFC]' : 'text-[#0A0A0A] hover:bg-[#F8FAFC]'"
                    @click="onSelectRequest(req.id)"
                  >
                    {{ req.method }} {{ req.name }}
                  </button>
                </div>
                <div v-if="(detail?.requests?.length || 0) > 0">
                  <div class="px-2 text-[12px] font-medium text-[#4A5565]">未分组</div>
                  <button
                    v-for="req in detail?.requests || []"
                    :key="req.id"
                    class="mt-1 block w-full rounded-[6px] px-2 py-1 text-left text-[12px]"
                    :class="selectedRequestId === req.id ? 'bg-[#EFF6FF] text-[#155DFC]' : 'text-[#0A0A0A] hover:bg-[#F8FAFC]'"
                    @click="onSelectRequest(req.id)"
                  >
                    {{ req.method }} {{ req.name }}
                  </button>
                </div>
              </div>
            </div>

            <div class="rounded-[8px] border border-black/10 p-2">
              <div class="mb-2 text-[12px] font-medium text-[#717182]">导入（简化）</div>
              <select v-model="importFormat" class="mb-2 w-full rounded-[6px] border border-black/10 px-2 py-1 text-[12px]">
                <option value="postman">postman</option>
                <option value="swagger">swagger</option>
              </select>
              <textarea v-model="importContent" class="h-[120px] w-full rounded-[6px] border border-black/10 p-2 text-[12px]" placeholder="粘贴导入 JSON 内容" />
              <button class="mt-2 w-full rounded-[6px] bg-[#155DFC] px-2 py-1 text-[12px] text-white disabled:opacity-60" :disabled="importSubmitting" @click="handleImport">
                导入集合
              </button>
            </div>
          </aside>

          <main class="space-y-3">
            <div v-if="requestForm" class="rounded-[8px] border border-black/10 p-3">
              <div class="mb-3 text-[12px] font-medium text-[#717182]">请求详情表单（可编辑）</div>
              <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
                <input v-model="requestForm.name" class="rounded-[6px] border border-black/10 px-2 py-1 text-[12px]" placeholder="请求名称" />
                <select v-model="requestForm.method" class="rounded-[6px] border border-black/10 px-2 py-1 text-[12px]">
                  <option value="GET">GET</option>
                  <option value="POST">POST</option>
                  <option value="PUT">PUT</option>
                  <option value="PATCH">PATCH</option>
                  <option value="DELETE">DELETE</option>
                </select>
              </div>
              <input v-model="requestForm.url" class="mt-3 w-full rounded-[6px] border border-black/10 px-2 py-1 text-[12px]" placeholder="URL" />
              <div class="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                <div>
                  <div class="mb-1 text-[12px] text-[#717182]">headers(JSON)</div>
                  <textarea v-model="requestForm.headersText" class="h-[120px] w-full rounded-[6px] border border-black/10 p-2 text-[12px] font-mono" />
                </div>
                <div>
                  <div class="mb-1 text-[12px] text-[#717182]">auth(JSON)</div>
                  <textarea v-model="requestForm.authText" class="h-[120px] w-full rounded-[6px] border border-black/10 p-2 text-[12px] font-mono" />
                </div>
              </div>
              <div class="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                <div>
                  <div class="mb-1 text-[12px] text-[#717182]">body(JSON)</div>
                  <textarea v-model="requestForm.bodyText" class="h-[140px] w-full rounded-[6px] border border-black/10 p-2 text-[12px] font-mono" />
                </div>
                <div>
                  <div class="mb-1 text-[12px] text-[#717182]">asserts(JSON)</div>
                  <textarea v-model="requestForm.assertsText" class="h-[140px] w-full rounded-[6px] border border-black/10 p-2 text-[12px] font-mono" />
                </div>
              </div>
              <div class="mt-3 flex gap-2">
                <button class="rounded-[6px] bg-[#155DFC] px-3 py-1 text-[12px] text-white disabled:opacity-60" :disabled="saving" @click="saveRequest">保存</button>
                <button class="rounded-[6px] border border-black/10 px-3 py-1 text-[12px] disabled:opacity-60" :disabled="running" @click="runSingleRequest">单请求运行</button>
              </div>
            </div>
            <div v-else class="rounded-[8px] border border-black/10 p-3 text-[12px] text-[#717182]">请选择一个请求</div>

            <div v-if="runResultText" class="rounded-[8px] border border-black/10 bg-[#F8FAFC] p-3">
              <div class="mb-1 text-[12px] font-medium text-[#717182]">运行结果</div>
              <pre class="max-h-[220px] overflow-auto whitespace-pre-wrap text-[11px] text-[#0A0A0A]">{{ runResultText }}</pre>
            </div>

            <div v-if="exportText" class="rounded-[8px] border border-black/10 bg-[#F8FAFC] p-3">
              <div class="mb-1 text-[12px] font-medium text-[#717182]">导出内容</div>
              <pre class="max-h-[220px] overflow-auto whitespace-pre-wrap text-[11px] text-[#0A0A0A]">{{ exportText }}</pre>
            </div>
          </main>
        </div>

        <div v-if="error" class="border-t border-black/10 px-4 py-2 text-[12px] text-[#E7000B]">{{ error }}</div>
        <div v-else-if="success" class="border-t border-black/10 px-4 py-2 text-[12px] text-[#008236]">{{ success }}</div>
      </section>
    </div>
  </div>
</template>
