<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createDefect, listDefects, type DefectListItem, type DefectStatus } from '@/lib/api/defects'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => String(route.params.projectId || '').trim())

const loading = ref(false)
const creating = ref(false)
const error = ref('')
const createError = ref('')

const q = ref('')
const status = ref('')
const page = ref(1)
const pageSize = ref(20)

const items = ref<DefectListItem[]>([])
const total = ref(0)

const createForm = ref({
  title: '',
  description: '',
  severity: 'P2',
  runId: '',
  caseRunId: '',
  testcaseId: '',
  errorMessage: ''
})

const statusOptions: Array<{ label: string; value: DefectStatus | '' }> = [
  { label: '全部状态', value: '' },
  { label: 'OPEN', value: 'OPEN' },
  { label: 'IN_PROGRESS', value: 'IN_PROGRESS' },
  { label: 'RESOLVED', value: 'RESOLVED' },
  { label: 'CLOSED', value: 'CLOSED' }
]
const validStatusValues = new Set<string>(statusOptions.map((item) => item.value).filter(Boolean))

const pageStart = computed(() => (total.value === 0 ? 0 : (page.value - 1) * pageSize.value + 1))
const pageEnd = computed(() => Math.min(total.value, page.value * pageSize.value))
const hasPrev = computed(() => page.value > 1)
const hasNext = computed(() => page.value * pageSize.value < total.value)

function formatTime(ts?: number | null) {
  if (!ts) return '-'
  const value = ts < 100000000000 ? ts * 1000 : ts
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(
    date.getHours()
  ).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function statusClass(value?: string) {
  if (value === 'OPEN' || value === 'REOPENED') return 'bg-[#FEE2E2] text-[#B91C1C]'
  if (value === 'IN_PROGRESS') return 'bg-[#DBEAFE] text-[#1D4ED8]'
  if (value === 'RESOLVED') return 'bg-[#FEF3C7] text-[#92400E]'
  if (value === 'CLOSED') return 'bg-[#DCFCE7] text-[#166534]'
  return 'bg-[#E5E7EB] text-[#4B5563]'
}

async function loadDefects() {
  const pid = projectId.value
  if (!pid) return
  loading.value = true
  error.value = ''
  try {
    const data = await listDefects({
      projectId: pid,
      page: page.value,
      pageSize: pageSize.value,
      status: status.value || undefined,
      q: q.value.trim() || undefined,
      runId: String(route.query.runId || '').trim() || undefined,
      caseRunId: String(route.query.caseRunId || '').trim() || undefined,
      testcaseId: String(route.query.testcaseId || '').trim() || undefined
    })
    items.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载缺陷列表失败'
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function syncCreatePrefillFromQuery() {
  const statusQuery = String(route.query.status || '').trim().toUpperCase()
  status.value = validStatusValues.has(statusQuery) ? statusQuery : ''
  const runId = String(route.query.runId || '').trim()
  const caseRunId = String(route.query.caseRunId || '').trim()
  const testcaseId = String(route.query.testcaseId || '').trim()
  const errorMessage = String(route.query.errorMessage || '').trim()
  const title = String(route.query.title || '').trim()
  const description = String(route.query.description || '').trim()
  const severity = String(route.query.severity || '').trim().toUpperCase()
  createForm.value.runId = runId
  createForm.value.caseRunId = caseRunId
  createForm.value.testcaseId = testcaseId
  createForm.value.errorMessage = errorMessage
  if (title) {
    createForm.value.title = title
  }
  if (description) {
    createForm.value.description = description
  }
  if (['P0', 'P1', 'P2', 'P3'].includes(severity)) {
    createForm.value.severity = severity
  }
  if (!createForm.value.title && errorMessage) {
    createForm.value.title = `失败用例缺陷：${errorMessage.slice(0, 60)}`
  }
  if (!createForm.value.description && errorMessage) {
    createForm.value.description = errorMessage
  }
}

async function submitCreate() {
  const pid = projectId.value
  if (!pid) return
  creating.value = true
  createError.value = ''
  try {
    const title = createForm.value.title.trim()
    if (!title) throw new Error('标题不能为空')
    const created = await createDefect({
      projectId: pid,
      title,
      description: createForm.value.description.trim(),
      severity: createForm.value.severity,
      runId: createForm.value.runId.trim() || null,
      caseRunId: createForm.value.caseRunId.trim() || null,
      testcaseId: createForm.value.testcaseId.trim() || null,
      errorMessage: createForm.value.errorMessage.trim() || null
    })
    void router.push(`/projects/${encodeURIComponent(pid)}/defects/${encodeURIComponent(created.id)}`)
  } catch (e) {
    createError.value = e instanceof Error ? e.message : '创建缺陷失败'
  } finally {
    creating.value = false
  }
}

function search() {
  page.value = 1
  void loadDefects()
}

function openDetail(item: DefectListItem) {
  void router.push(`/projects/${encodeURIComponent(projectId.value)}/defects/${encodeURIComponent(item.id)}`)
}

watch(
  () => [
    projectId.value,
    route.query.status,
    route.query.runId,
    route.query.caseRunId,
    route.query.testcaseId,
    route.query.errorMessage,
    route.query.title,
    route.query.description,
    route.query.severity
  ],
  () => {
    syncCreatePrefillFromQuery()
    page.value = 1
    void loadDefects()
  },
  { immediate: true }
)
</script>

<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-4 md:p-6">
    <div class="rounded-[12px] border border-black/10 bg-white">
      <div class="border-b border-black/10 px-4 py-3">
        <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">缺陷管理</div>
        <div class="mt-1 text-[12px] leading-[16px] text-[#717182]">
          runId={{ String(route.query.runId || '-') }} · caseRunId={{ String(route.query.caseRunId || '-') }} · testcaseId={{ String(route.query.testcaseId || '-') }}
        </div>
      </div>

      <div class="grid grid-cols-1 gap-3 border-b border-black/10 p-4 md:grid-cols-[minmax(0,1fr)_180px_auto]">
        <input v-model="q" class="h-9 rounded-[8px] border border-black/10 px-3 text-[13px]" placeholder="搜索缺陷标题/ID" @keyup.enter="search" />
        <select v-model="status" class="h-9 rounded-[8px] border border-black/10 px-2 text-[13px]">
          <option v-for="option in statusOptions" :key="option.value || 'ALL'" :value="option.value">{{ option.label }}</option>
        </select>
        <button class="h-9 rounded-[8px] border border-black/10 px-3 text-[13px]" @click="search">查询</button>
      </div>

      <div class="border-b border-black/10 bg-[#FAFAFA] p-4">
        <div class="mb-2 text-[13px] font-medium text-[#0A0A0A]">快速新建缺陷</div>
        <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
          <input v-model="createForm.title" class="h-9 rounded-[8px] border border-black/10 px-3 text-[13px]" placeholder="缺陷标题（必填）" />
          <select v-model="createForm.severity" class="h-9 rounded-[8px] border border-black/10 px-2 text-[13px]">
            <option value="P0">严重级别 P0</option>
            <option value="P1">严重级别 P1</option>
            <option value="P2">严重级别 P2</option>
            <option value="P3">严重级别 P3</option>
          </select>
          <input v-model="createForm.runId" class="h-9 rounded-[8px] border border-black/10 px-3 text-[13px]" placeholder="runId（可选）" />
          <input v-model="createForm.caseRunId" class="h-9 rounded-[8px] border border-black/10 px-3 text-[13px]" placeholder="caseRunId（可选）" />
          <input v-model="createForm.testcaseId" class="h-9 rounded-[8px] border border-black/10 px-3 text-[13px]" placeholder="testcaseId（可选）" />
          <input v-model="createForm.errorMessage" class="h-9 rounded-[8px] border border-black/10 px-3 text-[13px]" placeholder="错误信息（可选）" />
        </div>
        <textarea v-model="createForm.description" class="mt-3 min-h-[88px] w-full rounded-[8px] border border-black/10 px-3 py-2 text-[13px]" placeholder="缺陷描述" />
        <div class="mt-3 flex items-center gap-3">
          <button class="h-9 rounded-[8px] bg-[#155DFC] px-4 text-[13px] text-white disabled:opacity-60" :disabled="creating" @click="submitCreate">
            {{ creating ? '创建中...' : '新建缺陷' }}
          </button>
          <div v-if="createError" class="text-[12px] text-[#B91C1C]">{{ createError }}</div>
        </div>
      </div>

      <div v-if="loading" class="px-4 py-6 text-[13px] text-[#717182]">加载中...</div>
      <div v-else-if="error" class="px-4 py-6 text-[13px] text-[#B91C1C]">{{ error }}</div>
      <div v-else-if="items.length === 0" class="px-4 py-8 text-center text-[13px] text-[#717182]">暂无缺陷</div>
      <div v-else class="overflow-x-auto">
        <table class="w-full min-w-[900px] border-collapse">
          <thead>
            <tr class="bg-[rgba(236,236,240,0.3)]">
              <th class="px-4 py-2 text-left text-[12px] font-medium text-[#717182]">ID</th>
              <th class="px-4 py-2 text-left text-[12px] font-medium text-[#717182]">标题</th>
              <th class="px-4 py-2 text-left text-[12px] font-medium text-[#717182]">状态</th>
              <th class="px-4 py-2 text-left text-[12px] font-medium text-[#717182]">指派人</th>
              <th class="px-4 py-2 text-left text-[12px] font-medium text-[#717182]">关联对象</th>
              <th class="px-4 py-2 text-left text-[12px] font-medium text-[#717182]">更新时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id" class="cursor-pointer border-t border-black/10 hover:bg-[#F8FAFC]" @click="openDetail(item)">
              <td class="px-4 py-3 font-mono text-[12px] text-[#0A0A0A]">{{ item.id }}</td>
              <td class="px-4 py-3 text-[13px] text-[#0A0A0A]">{{ item.title }}</td>
              <td class="px-4 py-3">
                <span class="rounded-full px-2 py-[2px] text-[11px] font-medium" :class="statusClass(item.status)">{{ item.status || '-' }}</span>
              </td>
              <td class="px-4 py-3 text-[12px] text-[#4A5565]">{{ item.assigneeName || item.assigneeId || '-' }}</td>
              <td class="px-4 py-3 text-[12px] text-[#4A5565]">run={{ item.runId || '-' }} · case={{ item.caseRunId || '-' }} · tc={{ item.testcaseId || '-' }}</td>
              <td class="px-4 py-3 text-[12px] text-[#717182]">{{ formatTime(item.updatedAt ?? item.createdAt) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="flex items-center justify-between border-t border-black/10 px-4 py-3">
        <div class="text-[12px] text-[#717182]">第 {{ pageStart }}-{{ pageEnd }} 条，共 {{ total }} 条</div>
        <div class="flex items-center gap-2">
          <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px] disabled:opacity-50" :disabled="!hasPrev" @click="page -= 1; loadDefects()">
            上一页
          </button>
          <div class="text-[12px] text-[#4A5565]">第 {{ page }} 页</div>
          <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px] disabled:opacity-50" :disabled="!hasNext" @click="page += 1; loadDefects()">
            下一页
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
