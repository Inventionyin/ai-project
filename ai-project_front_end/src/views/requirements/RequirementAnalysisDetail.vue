<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  bulkApproveRequirementCaseDrafts,
  fetchRequirementAnalysis,
  fetchRequirementCaseLinks,
  fetchRequirementCaseDrafts,
  fetchRequirementTestPoints,
  generateRequirementCaseDrafts,
  syncRequirementTestPoints,
  updateRequirementAnalysis,
  updateRequirementTestPoint,
  type GeneratedCaseDraft,
  type RequirementAnalysis,
  type RequirementAnalysisPayload,
  type RequirementCaseLink,
  type RequirementTestPoint,
  type RequirementTestPointStatus
} from '@/lib/api/requirements'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => String(route.params.projectId || '').trim())
const analysisId = computed(() => String(route.params.analysisId || '').trim())

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const success = ref('')
const detail = ref<RequirementAnalysis | null>(null)
const summary = ref('')
const status = ref<'DRAFT' | 'GENERATED' | 'REVIEWED' | 'ARCHIVED'>('GENERATED')
const riskLevel = ref<'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'>('MEDIUM')
const coverageScore = ref(0)
const analysisText = ref('')

const testPoints = ref<RequirementTestPoint[]>([])
const testPointFilter = ref<'ALL' | RequirementTestPointStatus>('ALL')
const syncingTestPoints = ref(false)
const updatingTestPointId = ref('')

const generatingDrafts = ref(false)
const caseDrafts = ref<GeneratedCaseDraft[]>([])
const caseLinks = ref<RequirementCaseLink[]>([])
const selectedDraftIds = ref<string[]>([])
const approvingDrafts = ref(false)

function pretty(value: unknown) {
  return JSON.stringify(value || {}, null, 2)
}

function fill(data: RequirementAnalysis) {
  detail.value = data
  summary.value = data.summary || ''
  status.value = data.status || 'GENERATED'
  riskLevel.value = data.riskLevel || 'MEDIUM'
  coverageScore.value = Number(data.coverageScore || 0)
  analysisText.value = pretty(data.analysis)
}

function normalizeAnalysisPayload(raw: Record<string, unknown>): RequirementAnalysisPayload {
  const list = (value: unknown) => (Array.isArray(value) ? (value as Array<Record<string, unknown>>) : [])
  return {
    featurePoints: list(raw.featurePoints),
    businessRules: list(raw.businessRules),
    testPoints: list(raw.testPoints),
    riskPoints: list(raw.riskPoints),
    boundaryCases: list(raw.boundaryCases),
    coverageSuggestions: list(raw.coverageSuggestions)
  }
}

const filteredTestPoints = computed(() => {
  if (testPointFilter.value === 'ALL') return testPoints.value
  return testPoints.value.filter((item) => item.status === testPointFilter.value)
})
const acceptedTestPointCount = computed(() => testPoints.value.filter((item) => item.status === 'ACCEPTED').length)
const pendingTestPointCount = computed(() => testPoints.value.filter((item) => item.status === 'DRAFT').length)
const selectedDraftCount = computed(() => selectedDraftIds.value.length)
const selectableCaseDrafts = computed(() => caseDrafts.value.filter((row) => row.status === 'PENDING'))
const pendingCaseDraftCount = computed(() => caseDrafts.value.filter((row) => row.status === 'PENDING').length)
const committedCaseDraftCount = computed(() => caseDrafts.value.filter((row) => row.status === 'COMMITTED').length)
const caseLinkCount = computed(() => caseLinks.value.length)
const allSelectableDraftChecked = computed(() => {
  const selectableIds = selectableCaseDrafts.value.map((row) => row.id)
  if (selectableIds.length === 0) return false
  return selectableIds.every((id) => selectedDraftIds.value.includes(id))
})

async function load() {
  if (!projectId.value || !analysisId.value) return
  loading.value = true
  error.value = ''
  try {
    fill(await fetchRequirementAnalysis(projectId.value, analysisId.value))
    const [points, drafts, links] = await Promise.all([
      fetchRequirementTestPoints(projectId.value, analysisId.value),
      fetchRequirementCaseDrafts(projectId.value, analysisId.value),
      fetchRequirementCaseLinks(projectId.value, analysisId.value)
    ])
    testPoints.value = points
    caseDrafts.value = drafts
    caseLinks.value = links
    selectedDraftIds.value = []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载需求分析失败'
    detail.value = null
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!projectId.value || !analysisId.value) return
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    let parsed: Record<string, unknown>
    try {
      parsed = JSON.parse(analysisText.value || '{}') as Record<string, unknown>
    } catch {
      throw new Error('分析 JSON 格式不正确')
    }
    const analysis = normalizeAnalysisPayload(parsed)
    const updated = await updateRequirementAnalysis(projectId.value, analysisId.value, {
      status: status.value,
      summary: summary.value,
      riskLevel: riskLevel.value,
      coverageScore: coverageScore.value,
      analysis
    })
    fill(updated)
    success.value = '分析结果已保存'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function syncTestPoints() {
  if (!projectId.value || !analysisId.value) return
  syncingTestPoints.value = true
  error.value = ''
  success.value = ''
  try {
    testPoints.value = await syncRequirementTestPoints(projectId.value, analysisId.value)
    success.value = '测试点已同步'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '同步测试点失败'
  } finally {
    syncingTestPoints.value = false
  }
}

async function reviewTestPoint(row: RequirementTestPoint, nextStatus: RequirementTestPointStatus) {
  if (!projectId.value || !row.id) return
  updatingTestPointId.value = row.id
  error.value = ''
  success.value = ''
  try {
    const updated = await updateRequirementTestPoint(projectId.value, row.id, { status: nextStatus })
    testPoints.value = testPoints.value.map((item) => (item.id === updated.id ? updated : item))
    success.value = `测试点已${nextStatus === 'ACCEPTED' ? '接受' : '拒绝'}`
  } catch (e) {
    error.value = e instanceof Error ? e.message : '更新测试点状态失败'
  } finally {
    updatingTestPointId.value = ''
  }
}

async function generateDrafts() {
  if (!projectId.value || !analysisId.value) return
  generatingDrafts.value = true
  error.value = ''
  success.value = ''
  try {
    caseDrafts.value = await generateRequirementCaseDrafts(projectId.value, analysisId.value)
    selectedDraftIds.value = []
    success.value = '用例草稿生成完成'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '生成用例草稿失败'
  } finally {
    generatingDrafts.value = false
  }
}

async function approveDrafts() {
  if (!projectId.value || selectedDraftIds.value.length === 0) return
  approvingDrafts.value = true
  error.value = ''
  success.value = ''
  try {
    await bulkApproveRequirementCaseDrafts(projectId.value, selectedDraftIds.value)
    const [drafts, links] = await Promise.all([
      fetchRequirementCaseDrafts(projectId.value, analysisId.value),
      fetchRequirementCaseLinks(projectId.value, analysisId.value)
    ])
    caseDrafts.value = drafts
    caseLinks.value = links
    selectedDraftIds.value = []
    success.value = '已审核入库'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '审核入库失败'
  } finally {
    approvingDrafts.value = false
  }
}

function isDraftSelected(draftId: string) {
  return selectedDraftIds.value.includes(draftId)
}

function toggleDraftSelection(draftId: string, checked: boolean) {
  if (!caseDrafts.value.some((row) => row.id === draftId && row.status === 'PENDING')) return
  if (checked) {
    if (!selectedDraftIds.value.includes(draftId)) selectedDraftIds.value = [...selectedDraftIds.value, draftId]
    return
  }
  selectedDraftIds.value = selectedDraftIds.value.filter((id) => id !== draftId)
}

function toggleSelectAllDrafts(checked: boolean) {
  if (!checked) {
    selectedDraftIds.value = []
    return
  }
  selectedDraftIds.value = selectableCaseDrafts.value.map((row) => row.id)
}

function backToDoc() {
  if (!detail.value) return
  void router.push(`/projects/${encodeURIComponent(projectId.value)}/requirements/docs/${encodeURIComponent(detail.value.docId)}`)
}

function formatTime(ts?: number | null) {
  if (!ts) return '-'
  const value = ts < 100000000000 ? ts * 1000 : ts
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(
    date.getHours()
  ).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

watch(
  () => [projectId.value, analysisId.value],
  () => {
    void load()
  },
  { immediate: true }
)
</script>

<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-4 md:p-6">
    <div v-if="loading" class="rounded-[12px] border border-black/10 bg-white px-4 py-5 text-[13px] text-[#717182]">加载中...</div>
    <div v-else-if="error && !detail" class="rounded-[12px] border border-black/10 bg-white px-4 py-5 text-[13px] text-[#B91C1C]">{{ error }}</div>
    <div v-else-if="detail" class="grid grid-cols-1 gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
      <section class="rounded-[12px] border border-black/10 bg-white p-4">
        <div class="mb-3 flex items-center justify-between gap-2">
          <h2 class="text-[14px] font-semibold text-[#0A0A0A]">需求分析</h2>
          <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px]" @click="backToDoc">返回文档</button>
        </div>

        <div class="space-y-3">
          <label class="block text-[12px] text-[#717182]">
            状态
            <select v-model="status" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-2 text-[13px] text-[#0A0A0A]">
              <option value="DRAFT">草稿</option>
              <option value="GENERATED">已生成</option>
              <option value="REVIEWED">已复核</option>
              <option value="ARCHIVED">已归档</option>
            </select>
          </label>
          <label class="block text-[12px] text-[#717182]">
            风险等级
            <select v-model="riskLevel" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-2 text-[13px] text-[#0A0A0A]">
              <option value="LOW">低</option>
              <option value="MEDIUM">中</option>
              <option value="HIGH">高</option>
              <option value="CRITICAL">严重</option>
            </select>
          </label>
          <label class="block text-[12px] text-[#717182]">
            覆盖评分
            <input v-model.number="coverageScore" type="number" min="0" max="1" step="0.01" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px]" />
          </label>
          <label class="block text-[12px] text-[#717182]">
            摘要
            <textarea v-model="summary" class="mt-1 min-h-[120px] w-full resize-y rounded-[8px] border border-black/10 px-3 py-2 text-[13px]" />
          </label>
        </div>

        <button class="mt-4 h-9 rounded-[8px] bg-[#155DFC] px-4 text-[13px] text-white disabled:opacity-60" :disabled="saving" @click="save">
          {{ saving ? '保存中...' : '保存分析' }}
        </button>
      </section>

      <section class="rounded-[12px] border border-black/10 bg-white">
        <div class="border-b border-black/10 px-4 py-3">
          <div class="text-[14px] font-semibold text-[#0A0A0A]">结构化分析 JSON</div>
          <div class="mt-1 text-[12px] text-[#717182]">包含功能点、业务规则、测试点、风险点、边界场景和覆盖建议；保存前会校验 JSON 格式。</div>
        </div>
        <div class="p-4">
          <textarea
            v-model="analysisText"
            spellcheck="false"
            class="min-h-[640px] w-full resize-y rounded-[8px] border border-black/10 bg-[#0B1220] p-4 font-mono text-[12px] leading-5 text-[#D7E3F4] outline-none"
          />
        </div>
      </section>

      <section class="rounded-[12px] border border-black/10 bg-white xl:col-span-2">
        <div class="border-b border-black/10 px-4 py-3">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="text-[14px] font-semibold text-[#0A0A0A]">测试点审核</div>
            <div class="flex items-center gap-2">
              <select v-model="testPointFilter" class="h-8 rounded-[8px] border border-black/10 px-2 text-[12px]">
                <option value="ALL">全部状态</option>
                <option value="DRAFT">待审核</option>
                <option value="ACCEPTED">已接受</option>
                <option value="REJECTED">已拒绝</option>
              </select>
              <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px] disabled:opacity-60" :disabled="syncingTestPoints" @click="syncTestPoints">
                {{ syncingTestPoints ? '同步中...' : '同步测试点' }}
              </button>
            </div>
          </div>
          <div class="mt-2 text-[12px] text-[#717182]">待审核 {{ pendingTestPointCount }} · 已接受 {{ acceptedTestPointCount }} · 总计 {{ testPoints.length }}</div>
        </div>
        <div v-if="filteredTestPoints.length === 0" class="px-4 py-6 text-[12px] text-[#717182]">暂无测试点。</div>
        <div v-else class="overflow-x-auto">
          <table class="w-full min-w-[980px] border-collapse">
            <thead>
              <tr class="bg-[rgba(236,236,240,0.3)]">
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">标题</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">Priority</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">Risk</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">Scenario</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">状态</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in filteredTestPoints" :key="row.id" class="border-t border-black/10 align-top">
                <td class="px-3 py-2 text-[12px] text-[#0A0A0A]">
                  <div class="font-medium">{{ row.title || '-' }}</div>
                  <div class="mt-1 line-clamp-2 text-[#717182]">{{ row.description || '-' }}</div>
                </td>
                <td class="px-3 py-2 text-[12px] text-[#4A5565]">{{ row.priority || '-' }}</td>
                <td class="px-3 py-2 text-[12px] text-[#4A5565]">{{ row.riskLevel || '-' }}</td>
                <td class="px-3 py-2 text-[12px] text-[#4A5565]">{{ row.scenarioType || '-' }}</td>
                <td class="px-3 py-2 text-[12px] text-[#4A5565]">{{ row.status }}</td>
                <td class="px-3 py-2">
                  <div class="flex items-center gap-2">
                    <button
                      class="h-7 rounded-[6px] border border-black/10 px-2 text-[11px] text-[#166534] disabled:opacity-60"
                      :disabled="updatingTestPointId === row.id || row.status === 'ACCEPTED'"
                      @click="reviewTestPoint(row, 'ACCEPTED')"
                    >
                      接受
                    </button>
                    <button
                      class="h-7 rounded-[6px] border border-black/10 px-2 text-[11px] text-[#B91C1C] disabled:opacity-60"
                      :disabled="updatingTestPointId === row.id || row.status === 'REJECTED'"
                      @click="reviewTestPoint(row, 'REJECTED')"
                    >
                      拒绝
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="rounded-[12px] border border-black/10 bg-white xl:col-span-2">
        <div class="border-b border-black/10 px-4 py-3">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="text-[14px] font-semibold text-[#0A0A0A]">用例草稿审核</div>
            <div class="flex items-center gap-2">
              <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px] disabled:opacity-60" :disabled="acceptedTestPointCount === 0 || generatingDrafts" @click="generateDrafts">
                {{ generatingDrafts ? '生成中...' : '从已接受测试点生成草稿' }}
              </button>
              <button
                class="h-8 rounded-[8px] bg-[#155DFC] px-3 text-[12px] text-white disabled:opacity-60"
                :disabled="selectedDraftCount === 0 || approvingDrafts"
                @click="approveDrafts"
              >
                {{ approvingDrafts ? '入库中...' : `批量审核入库（${selectedDraftCount}）` }}
              </button>
            </div>
          </div>
          <div class="mt-2 text-[12px] text-[#717182]">待审核 PENDING {{ pendingCaseDraftCount }} · 已入库 COMMITTED {{ committedCaseDraftCount }} · 总计 {{ caseDrafts.length }}</div>
        </div>
        <div v-if="caseDrafts.length === 0" class="px-4 py-6 text-[12px] text-[#717182]">
          <div>暂无用例草稿。</div>
          <div class="mt-1">请先在“测试点审核”中接受至少 1 条测试点，再点击“从已接受测试点生成草稿”。</div>
        </div>
        <div v-else class="overflow-x-auto">
          <table class="w-full min-w-[1100px] border-collapse">
            <thead>
              <tr class="bg-[rgba(236,236,240,0.3)]">
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">
                  <input type="checkbox" :checked="allSelectableDraftChecked" class="h-4 w-4" @change="toggleSelectAllDrafts(($event.target as HTMLInputElement).checked)" />
                </th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">标题</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">前置条件</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">步骤</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">预期结果</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in caseDrafts" :key="row.id" class="border-t border-black/10 align-top">
                <td class="px-3 py-2">
                  <input
                    type="checkbox"
                    class="h-4 w-4"
                    :disabled="row.status !== 'PENDING'"
                    :checked="isDraftSelected(row.id)"
                    @change="toggleDraftSelection(row.id, ($event.target as HTMLInputElement).checked)"
                  />
                </td>
                <td class="px-3 py-2 text-[12px] text-[#0A0A0A]">
                  <div class="font-medium">{{ row.title || '-' }}</div>
                  <div class="mt-1 text-[#717182]">P: {{ row.priority || '-' }} · 来源测试点: {{ row.testPointId || '-' }}</div>
                </td>
                <td class="px-3 py-2 text-[12px] text-[#4A5565]"><div class="line-clamp-3">{{ row.preconditions || '-' }}</div></td>
                <td class="px-3 py-2 text-[12px] text-[#4A5565]"><div class="line-clamp-3">{{ row.steps || '-' }}</div></td>
                <td class="px-3 py-2 text-[12px] text-[#4A5565]"><div class="line-clamp-3 whitespace-pre-line">{{ row.expectedResults || '-' }}</div></td>
                <td class="px-3 py-2 text-[12px] text-[#4A5565]">{{ row.status }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="rounded-[12px] border border-black/10 bg-white xl:col-span-2">
        <div class="border-b border-black/10 px-4 py-3">
          <div class="text-[14px] font-semibold text-[#0A0A0A]">用例追溯</div>
          <div class="mt-2 text-[12px] text-[#717182]">追溯关系 {{ caseLinkCount }}</div>
        </div>
        <div v-if="caseLinks.length === 0" class="px-4 py-6 text-[12px] text-[#717182]">审核入库后会生成追溯关系</div>
        <div v-else class="overflow-x-auto">
          <table class="w-full min-w-[980px] border-collapse">
            <thead>
              <tr class="bg-[rgba(236,236,240,0.3)]">
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">用例</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">测试点 ID</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">草稿 ID</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">置信度</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">创建时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in caseLinks" :key="row.id" class="border-t border-black/10 align-top">
                <td class="px-3 py-2 text-[12px] text-[#0A0A0A]">
                  <div class="font-medium">{{ row.testcaseTitle || '-' }}</div>
                  <div class="mt-1 text-[#717182]">ID: {{ row.testcaseId || '-' }}</div>
                </td>
                <td class="px-3 py-2 text-[12px] text-[#4A5565]">{{ row.testPointId || '-' }}</td>
                <td class="px-3 py-2 text-[12px] text-[#4A5565]">{{ row.caseDraftId || '-' }}</td>
                <td class="px-3 py-2 text-[12px] text-[#4A5565]">{{ row.confidence == null ? '-' : row.confidence }}</td>
                <td class="px-3 py-2 text-[12px] text-[#4A5565]">{{ formatTime(row.createdAt) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <div v-if="error" class="xl:col-span-2 text-[12px] text-[#B91C1C]">{{ error }}</div>
      <div v-else-if="success" class="xl:col-span-2 text-[12px] text-[#166534]">{{ success }}</div>
    </div>
  </div>
</template>
