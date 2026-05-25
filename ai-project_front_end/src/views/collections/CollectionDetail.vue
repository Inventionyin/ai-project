<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createTestcaseBinding } from '@/lib/aiTestingPlatformApi'
import {
  exportCollection,
  fetchCollectionBindings,
  fetchCollectionDetail,
  fetchCollectionRequestDetail,
  fetchRequestBindings,
  importCollection,
  runCollectionRequest,
  updateCollectionRequest,
  type ApiAssetBinding,
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
const router = useRouter()

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
const collectionBindings = ref<ApiAssetBinding[]>([])
const requestBindings = ref<ApiAssetBinding[]>([])
const collectionBindingsLoading = ref(false)
const requestBindingsLoading = ref(false)
const bindingSubmitting = ref(false)
const collectionBindingsError = ref('')
const requestBindingsError = ref('')
const bindingError = ref('')
const bindingSuccess = ref('')

const bindingForm = reactive({
  testcaseId: '',
  name: '',
  assertSummary: ''
})

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

function formatUnixTime(timestamp?: number | null) {
  if (!timestamp || timestamp <= 0) return '-'
  const date = new Date(timestamp * 1000)
  if (Number.isNaN(date.getTime())) return '-'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date)
}

function linkTypeLabel(type?: string | null) {
  if (type === 'REQUEST') return '请求'
  if (type === 'COLLECTION') return '集合'
  return '接口目标'
}

function runStatusLabel(status?: string | null) {
  if (status === 'PASSED') return '通过'
  if (status === 'FAILED') return '失败'
  if (status === 'RUNNING') return '执行中'
  return '未执行'
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

async function loadCollectionBindings() {
  const pid = projectId.value
  const cid = collectionId.value
  collectionBindings.value = []
  collectionBindingsError.value = ''
  if (!pid || !cid) return
  collectionBindingsLoading.value = true
  try {
    collectionBindings.value = await fetchCollectionBindings(pid, cid)
  } catch (e) {
    collectionBindingsError.value = e instanceof Error ? e.message : '集合绑定加载失败'
  } finally {
    collectionBindingsLoading.value = false
  }
}

async function loadRequestBindings(requestId: string) {
  const pid = projectId.value
  const rid = String(requestId || '').trim()
  requestBindings.value = []
  requestBindingsError.value = ''
  if (!pid || !rid) return
  requestBindingsLoading.value = true
  try {
    const rows = await fetchRequestBindings(pid, rid)
    if (selectedRequestId.value === rid) {
      requestBindings.value = rows
    }
  } catch (e) {
    if (selectedRequestId.value === rid) {
      requestBindingsError.value = e instanceof Error ? e.message : '请求绑定加载失败'
    }
  } finally {
    if (selectedRequestId.value === rid) {
      requestBindingsLoading.value = false
    }
  }
}

async function loadCollection() {
  if (!collectionId.value) return
  loading.value = true
  error.value = ''
  runResultText.value = ''
  try {
    const data = await fetchCollectionDetail(collectionId.value)
    detail.value = data
    void loadCollectionBindings()
    const currentRequestStillExists = allRequests.value.some((item) => item.id === selectedRequestId.value)
    const candidate = requestIdFromQuery.value || (currentRequestStillExists ? selectedRequestId.value : '') || allRequests.value[0]?.id || ''
    selectedRequestId.value = candidate
    if (candidate) {
      await loadRequestDetail(candidate)
    } else {
      requestForm.value = null
      requestBindings.value = []
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
  bindingError.value = ''
  bindingSuccess.value = ''
  requestBindingsError.value = ''
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
    bindingForm.name = `${data.name}-接口绑定`
    void loadRequestBindings(data.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '请求详情加载失败'
  }
}

async function onSelectRequest(requestId: string) {
  selectedRequestId.value = requestId
  success.value = ''
  runResultText.value = ''
  bindingSuccess.value = ''
  bindingError.value = ''
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
    await loadCollection()
    success.value = '保存成功'
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

async function createRequestBinding() {
  const testcaseId = bindingForm.testcaseId.trim()
  if (!projectId.value || !collectionId.value || !requestForm.value) return
  if (!testcaseId) {
    bindingError.value = 'TestCase ID 不能为空'
    return
  }
  bindingSubmitting.value = true
  bindingError.value = ''
  bindingSuccess.value = ''
  try {
    await createTestcaseBinding(testcaseId, {
      name: bindingForm.name.trim() || `${requestForm.value.name}-接口绑定`,
      requestId: requestForm.value.requestId,
      collectionId: collectionId.value,
      linkType: 'REQUEST',
      sourceType: 'MANUAL',
      assertSummary: bindingForm.assertSummary.trim(),
      params: {},
      priority: 100,
      enabled: true
    })
    bindingSuccess.value = '绑定已创建'
    bindingForm.testcaseId = ''
    bindingForm.assertSummary = ''
    await Promise.all([
      loadRequestBindings(requestForm.value.requestId),
      loadCollectionBindings()
    ])
  } catch (e) {
    bindingError.value = e instanceof Error ? e.message : '绑定创建失败'
  } finally {
    bindingSubmitting.value = false
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
    const newId = String(created?.id || '').trim()
    if (newId && newId !== collectionId.value) {
      await router.replace({
        path: `/projects/${projectId.value}/assets/apis/${newId}`,
        query: {}
      })
    } else {
      await loadCollection()
    }
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
          <div class="rounded-[8px] bg-[#F8FAFC] p-2">
            <div class="mb-1 flex items-center justify-between text-[#717182]">
              <span>集合绑定</span>
              <span>{{ collectionBindingsLoading ? '加载中' : `${collectionBindings.length} 个` }}</span>
            </div>
            <div v-if="collectionBindingsError" class="text-[11px] text-[#E7000B]">{{ collectionBindingsError }}</div>
            <div v-else-if="collectionBindings.length" class="space-y-1">
              <div v-for="binding in collectionBindings.slice(0, 4)" :key="binding.id" class="rounded-[6px] bg-white px-2 py-1">
                <div class="truncate text-[#0A0A0A]">{{ binding.name }}</div>
                <div class="truncate text-[11px] text-[#717182]">{{ linkTypeLabel(binding.linkType) }} · {{ binding.testcaseId }}</div>
              </div>
            </div>
            <div v-else class="text-[11px] text-[#717182]">暂无绑定</div>
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

              <div class="mt-4 border-t border-black/10 pt-3">
                <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div class="text-[12px] font-medium text-[#0A0A0A]">接口绑定</div>
                    <div class="mt-1 text-[11px] text-[#717182]">
                      {{ requestBindingsLoading ? '绑定加载中...' : `当前请求 ${requestBindings.length} 个 TestCase 绑定` }}
                    </div>
                  </div>
                  <button
                    class="rounded-[6px] bg-[#155DFC] px-3 py-1 text-[12px] text-white disabled:opacity-60"
                    :disabled="bindingSubmitting"
                    @click="createRequestBinding"
                  >
                    {{ bindingSubmitting ? '绑定中...' : '绑定 TestCase' }}
                  </button>
                </div>

                <div class="grid grid-cols-1 gap-2 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                  <input
                    v-model="bindingForm.testcaseId"
                    class="rounded-[6px] border border-black/10 px-2 py-1 text-[12px]"
                    placeholder="TestCase ID"
                  />
                  <input
                    v-model="bindingForm.name"
                    class="rounded-[6px] border border-black/10 px-2 py-1 text-[12px]"
                    placeholder="绑定名称"
                  />
                </div>
                <textarea
                  v-model="bindingForm.assertSummary"
                  class="mt-2 h-[64px] w-full rounded-[6px] border border-black/10 p-2 text-[12px]"
                  placeholder="断言摘要，可留空"
                />
                <div v-if="bindingError" class="mt-2 text-[12px] text-[#E7000B]">{{ bindingError }}</div>
                <div v-else-if="bindingSuccess" class="mt-2 text-[12px] text-[#008236]">{{ bindingSuccess }}</div>
                <div v-if="requestBindingsError" class="mt-2 text-[12px] text-[#E7000B]">{{ requestBindingsError }}</div>

                <div class="mt-3 overflow-hidden rounded-[8px] border border-black/10">
                  <div class="grid grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_96px] bg-[#F8FAFC] px-3 py-2 text-[11px] font-medium text-[#717182]">
                    <div>绑定名称</div>
                    <div>TestCase</div>
                    <div>最近运行</div>
                  </div>
                  <div v-if="requestBindings.length">
                    <div v-for="binding in requestBindings" :key="binding.id" class="grid grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_96px] border-t border-black/10 px-3 py-2 text-[12px]">
                      <div class="min-w-0">
                        <div class="truncate text-[#0A0A0A]">{{ binding.name }}</div>
                        <div class="truncate text-[11px] text-[#717182]">{{ binding.assertSummary || '暂无断言摘要' }}</div>
                      </div>
                      <div class="break-all font-mono text-[11px] text-[#4A5565]">{{ binding.testcaseId }}</div>
                      <div class="text-[11px] text-[#717182]">
                        <div>{{ runStatusLabel(binding.lastRunStatus) }}</div>
                        <div>{{ formatUnixTime(binding.lastRunAt || binding.updatedAt) }}</div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="border-t border-black/10 px-3 py-3 text-[12px] text-[#717182]">暂无请求级绑定</div>
                </div>
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
