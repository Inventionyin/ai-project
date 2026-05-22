<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  createKnowledgeRetrospective,
  evaluateKnowledgeRecommendations,
  fetchKnowledgeRetrospectiveDetail,
  fetchKnowledgeRetrospectives,
  type KnowledgeRecommendation,
  updateKnowledgeRetrospective,
  updateKnowledgeRecommendationStatus,
  type KnowledgeRetrospective,
  type KnowledgeRetrospectiveSourceType
} from '@/lib/api/knowledge'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || '').trim())
const queryRetrospectiveId = computed(() => {
  const byStandard = String(route.query.retrospectiveId || '').trim()
  if (byStandard) return byStandard
  return String(route.query.retropectiveId || '').trim()
})

const loading = ref(false)
const savingCreate = ref(false)
const savingDetail = ref(false)
const error = ref('')
const success = ref('')

const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const sourceTypeFilter = ref('')
const statusFilter = ref('')
const items = ref<KnowledgeRetrospective[]>([])

const selectedId = ref('')
const detail = ref<KnowledgeRetrospective | null>(null)
const detailLoading = ref(false)
const recommendationLoading = ref(false)
const recommendationError = ref('')
const recommendations = ref<KnowledgeRecommendation[]>([])
const recommendationUpdatingMap = ref<Record<string, boolean>>({})

const createForm = ref({
  title: '',
  sourceType: 'OTHER' as KnowledgeRetrospectiveSourceType | string,
  problemSummary: '',
  rootCause: '',
  decision: '',
  actionItems: ''
})

const detailForm = ref({
  problemSummary: '',
  rootCause: '',
  decision: '',
  actionItems: ''
})

let listLoadSeq = 0
let detailLoadSeq = 0
let recommendationLoadSeq = 0

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const hasPrev = computed(() => page.value > 1)
const hasNext = computed(() => page.value < totalPages.value)

async function loadList() {
  const pid = projectId.value
  if (!pid) return
  const seq = ++listLoadSeq
  loading.value = true
  error.value = ''
  try {
    const res = await fetchKnowledgeRetrospectives(pid, {
      page: page.value,
      pageSize: pageSize.value,
      sourceType: sourceTypeFilter.value || undefined,
      status: statusFilter.value || undefined
    })
    if (seq !== listLoadSeq || pid !== projectId.value) return
    items.value = res.items
    total.value = res.total
    page.value = Math.max(1, Math.min(res.page || 1, Math.max(1, Math.ceil((res.total || 0) / (res.pageSize || pageSize.value)))))
    const preferredId = queryRetrospectiveId.value
    if (preferredId) {
      selectedId.value = preferredId
    } else if (!selectedId.value || !items.value.some((item) => item.id === selectedId.value)) {
      selectedId.value = items.value[0]?.id || ''
    }
  } catch (e) {
    if (seq !== listLoadSeq) return
    error.value = e instanceof Error ? e.message : '加载复盘列表失败'
    items.value = []
    total.value = 0
  } finally {
    if (seq === listLoadSeq) loading.value = false
  }
}

async function loadDetail() {
  const pid = projectId.value
  const rid = selectedId.value
  if (!pid || !rid) {
    detail.value = null
    return
  }
  const seq = ++detailLoadSeq
  detailLoading.value = true
  error.value = ''
  try {
    const data = await fetchKnowledgeRetrospectiveDetail(pid, rid)
    if (seq !== detailLoadSeq || pid !== projectId.value || rid !== selectedId.value) return
    detail.value = data
    detailForm.value = {
      problemSummary: data.problemSummary || '',
      rootCause: data.rootCause || '',
      decision: data.decision || '',
      actionItems: data.actionItems || ''
    }
  } catch (e) {
    if (seq !== detailLoadSeq) return
    error.value = e instanceof Error ? e.message : '加载复盘详情失败'
    detail.value = null
  } finally {
    if (seq === detailLoadSeq) detailLoading.value = false
  }
}

async function loadRecommendations() {
  const pid = projectId.value
  const rid = selectedId.value
  if (!pid || !rid) {
    recommendations.value = []
    recommendationError.value = ''
    return
  }
  const seq = ++recommendationLoadSeq
  recommendationLoading.value = true
  recommendationError.value = ''
  try {
    const res = await evaluateKnowledgeRecommendations(pid, 'RETROSPECTIVE', rid, 10)
    if (seq !== recommendationLoadSeq || pid !== projectId.value || rid !== selectedId.value) return
    recommendations.value = Array.isArray(res?.recommendations) ? res.recommendations : []
  } catch (e) {
    if (seq !== recommendationLoadSeq) return
    recommendationError.value = e instanceof Error ? e.message : '加载推荐建议失败'
    recommendations.value = []
  } finally {
    if (seq === recommendationLoadSeq) recommendationLoading.value = false
  }
}

async function setRecommendationStatus(recommendationId: string, status: 'PENDING' | 'ADOPTED' | 'REJECTED') {
  const pid = projectId.value
  if (!pid || !recommendationId) return
  recommendationUpdatingMap.value[recommendationId] = true
  recommendationError.value = ''
  try {
    const updated = await updateKnowledgeRecommendationStatus(pid, recommendationId, status)
    const index = recommendations.value.findIndex((item) => item.id === recommendationId)
    if (index >= 0) recommendations.value[index] = { ...recommendations.value[index], ...updated }
  } catch (e) {
    recommendationError.value = e instanceof Error ? e.message : '更新推荐状态失败'
  } finally {
    recommendationUpdatingMap.value[recommendationId] = false
  }
}

async function submitCreate() {
  const pid = projectId.value
  if (!pid) return
  const title = createForm.value.title.trim()
  if (!title) {
    error.value = '标题不能为空'
    return
  }
  savingCreate.value = true
  error.value = ''
  success.value = ''
  try {
    const created = await createKnowledgeRetrospective(pid, {
      title,
      sourceType: createForm.value.sourceType || 'OTHER',
      problemSummary: createForm.value.problemSummary.trim(),
      rootCause: createForm.value.rootCause.trim(),
      decision: createForm.value.decision.trim(),
      actionItems: createForm.value.actionItems.trim()
    })
    createForm.value = { title: '', sourceType: 'OTHER', problemSummary: '', rootCause: '', decision: '', actionItems: '' }
    success.value = '复盘已创建'
    page.value = 1
    await loadList()
    selectedId.value = created.id
    await loadDetail()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '创建复盘失败'
  } finally {
    savingCreate.value = false
  }
}

async function submitDetailUpdate() {
  const pid = projectId.value
  const rid = selectedId.value
  if (!pid || !rid) return
  savingDetail.value = true
  error.value = ''
  success.value = ''
  try {
    const updated = await updateKnowledgeRetrospective(pid, rid, {
      problemSummary: detailForm.value.problemSummary.trim(),
      rootCause: detailForm.value.rootCause.trim(),
      decision: detailForm.value.decision.trim(),
      actionItems: detailForm.value.actionItems.trim()
    })
    detail.value = updated
    const index = items.value.findIndex((item) => item.id === updated.id)
    if (index >= 0) items.value[index] = { ...items.value[index], ...updated }
    success.value = '复盘详情已更新'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '更新复盘失败'
  } finally {
    savingDetail.value = false
  }
}

function formatTime(ts?: number | null) {
  if (!ts) return '-'
  const value = ts < 100000000000 ? ts * 1000 : ts
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

watch(
  () => queryRetrospectiveId.value,
  (value) => {
    const id = String(value || '').trim()
    if (id && id !== selectedId.value) selectedId.value = id
  },
  { immediate: true }
)

watch(
  () => [projectId.value, page.value, pageSize.value, sourceTypeFilter.value, statusFilter.value],
  () => {
    void loadList()
  },
  { immediate: true }
)

watch(
  () => selectedId.value,
  () => {
    void loadDetail()
    void loadRecommendations()
  }
)
</script>

<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-4 md:p-6">
    <div class="grid grid-cols-1 gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
      <section class="rounded-[12px] border border-black/10 bg-white p-4">
        <h2 class="text-[14px] font-semibold text-[#0A0A0A]">新建复盘</h2>
        <div class="mt-3 space-y-3">
          <label class="block text-[12px] text-[#717182]">
            标题
            <input v-model="createForm.title" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px]" />
          </label>
          <label class="block text-[12px] text-[#717182]">
            来源类型
            <select v-model="createForm.sourceType" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-2 text-[13px]">
              <option value="PRD">PRD</option>
              <option value="SPEC">SPEC</option>
              <option value="PROTOTYPE">PROTOTYPE</option>
              <option value="DEFECT">DEFECT</option>
              <option value="OTHER">OTHER</option>
            </select>
          </label>
          <label class="block text-[12px] text-[#717182]">
            问题摘要
            <textarea v-model="createForm.problemSummary" class="mt-1 min-h-[72px] w-full rounded-[8px] border border-black/10 px-3 py-2 text-[13px]" />
          </label>
          <label class="block text-[12px] text-[#717182]">
            根因分析
            <textarea v-model="createForm.rootCause" class="mt-1 min-h-[72px] w-full rounded-[8px] border border-black/10 px-3 py-2 text-[13px]" />
          </label>
          <label class="block text-[12px] text-[#717182]">
            决策
            <textarea v-model="createForm.decision" class="mt-1 min-h-[72px] w-full rounded-[8px] border border-black/10 px-3 py-2 text-[13px]" />
          </label>
          <label class="block text-[12px] text-[#717182]">
            行动项
            <textarea v-model="createForm.actionItems" class="mt-1 min-h-[72px] w-full rounded-[8px] border border-black/10 px-3 py-2 text-[13px]" />
          </label>
        </div>
        <button class="mt-4 h-9 rounded-[8px] bg-[#155DFC] px-4 text-[13px] text-white disabled:opacity-60" :disabled="savingCreate" @click="submitCreate">
          {{ savingCreate ? '创建中...' : '创建复盘' }}
        </button>
      </section>

      <section class="rounded-[12px] border border-black/10 bg-white">
        <div class="border-b border-black/10 px-4 py-3">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="text-[14px] font-semibold text-[#0A0A0A]">复盘中心</div>
            <div class="flex items-center gap-2">
              <select v-model="sourceTypeFilter" class="h-8 rounded-[8px] border border-black/10 px-2 text-[12px]">
                <option value="">全部来源</option>
                <option value="PRD">PRD</option>
                <option value="SPEC">SPEC</option>
                <option value="PROTOTYPE">PROTOTYPE</option>
                <option value="DEFECT">DEFECT</option>
                <option value="OTHER">OTHER</option>
              </select>
              <select v-model="statusFilter" class="h-8 rounded-[8px] border border-black/10 px-2 text-[12px]">
                <option value="">全部状态</option>
                <option value="DRAFT">DRAFT</option>
                <option value="REVIEWING">REVIEWING</option>
                <option value="PUBLISHED">PUBLISHED</option>
                <option value="ARCHIVED">ARCHIVED</option>
              </select>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-0 lg:grid-cols-[320px_minmax(0,1fr)]">
          <div class="border-r border-black/10">
            <div v-if="loading" class="px-3 py-4 text-[12px] text-[#717182]">加载中...</div>
            <div v-else-if="items.length === 0" class="px-3 py-4 text-[12px] text-[#717182]">暂无数据</div>
            <button
              v-for="item in items"
              :key="item.id"
              class="block w-full border-b border-black/10 px-3 py-3 text-left"
              :class="selectedId === item.id ? 'bg-[#EFF6FF]' : 'bg-white hover:bg-[#FAFAFA]'"
              @click="selectedId = item.id"
            >
              <div class="text-[13px] font-medium text-[#0A0A0A]">{{ item.title || '-' }}</div>
              <div class="mt-1 text-[11px] text-[#717182]">{{ item.sourceType }} · {{ item.status }}</div>
              <div class="mt-1 text-[11px] text-[#717182]">{{ formatTime(item.updatedAt || item.createdAt) }}</div>
            </button>
            <div class="flex items-center justify-between px-3 py-2 text-[11px] text-[#717182]">
              <button class="h-7 rounded-[6px] border border-black/10 px-2 disabled:opacity-50" :disabled="!hasPrev" @click="page -= 1">上一页</button>
              <span>{{ page }} / {{ totalPages }}</span>
              <button class="h-7 rounded-[6px] border border-black/10 px-2 disabled:opacity-50" :disabled="!hasNext" @click="page += 1">下一页</button>
            </div>
          </div>

          <div class="p-4">
            <div v-if="detailLoading" class="text-[12px] text-[#717182]">详情加载中...</div>
            <div v-else-if="!detail" class="text-[12px] text-[#717182]">请选择左侧复盘记录。</div>
            <div v-else>
              <div class="mb-3 text-[14px] font-semibold text-[#0A0A0A]">{{ detail.title }}</div>
              <div class="mb-4 text-[12px] text-[#717182]">{{ detail.sourceType }} · {{ detail.status }}</div>
              <div class="space-y-3">
                <label class="block text-[12px] text-[#717182]">
                  问题摘要
                  <textarea v-model="detailForm.problemSummary" class="mt-1 min-h-[92px] w-full rounded-[8px] border border-black/10 px-3 py-2 text-[13px]" />
                </label>
                <label class="block text-[12px] text-[#717182]">
                  根因分析
                  <textarea v-model="detailForm.rootCause" class="mt-1 min-h-[92px] w-full rounded-[8px] border border-black/10 px-3 py-2 text-[13px]" />
                </label>
                <label class="block text-[12px] text-[#717182]">
                  决策
                  <textarea v-model="detailForm.decision" class="mt-1 min-h-[92px] w-full rounded-[8px] border border-black/10 px-3 py-2 text-[13px]" />
                </label>
                <label class="block text-[12px] text-[#717182]">
                  行动项
                  <textarea v-model="detailForm.actionItems" class="mt-1 min-h-[92px] w-full rounded-[8px] border border-black/10 px-3 py-2 text-[13px]" />
                </label>
              </div>
              <button class="mt-4 h-9 rounded-[8px] bg-[#155DFC] px-4 text-[13px] text-white disabled:opacity-60" :disabled="savingDetail" @click="submitDetailUpdate">
                {{ savingDetail ? '保存中...' : '保存详情' }}
              </button>

              <div class="mt-6 rounded-[8px] border border-black/10 bg-[#FAFAFA] p-3">
                <div class="text-[13px] font-semibold text-[#0A0A0A]">推荐建议</div>
                <div v-if="recommendationLoading" class="mt-2 text-[12px] text-[#717182]">推荐加载中...</div>
                <div v-else-if="recommendationError" class="mt-2 text-[12px] text-[#B91C1C]">{{ recommendationError }}</div>
                <div v-else-if="recommendations.length === 0" class="mt-2 text-[12px] text-[#717182]">暂无推荐建议</div>
                <div v-else class="mt-2 space-y-2">
                  <div v-for="rec in recommendations" :key="rec.id" class="rounded-[8px] border border-black/10 bg-white p-3">
                    <div class="text-[13px] text-[#0A0A0A]">{{ rec.content || '-' }}</div>
                    <div class="mt-1 text-[11px] text-[#717182]">类型：{{ rec.type || '-' }} · 分数：{{ rec.score ?? '-' }} · 状态：{{ rec.status || '-' }}</div>
                    <div class="mt-2 flex flex-wrap gap-2">
                      <button
                        class="h-7 rounded-[6px] border border-black/10 px-2 text-[11px] disabled:opacity-50"
                        :disabled="recommendationUpdatingMap[rec.id]"
                        @click="setRecommendationStatus(rec.id, 'ADOPTED')"
                      >
                        采纳
                      </button>
                      <button
                        class="h-7 rounded-[6px] border border-black/10 px-2 text-[11px] disabled:opacity-50"
                        :disabled="recommendationUpdatingMap[rec.id]"
                        @click="setRecommendationStatus(rec.id, 'REJECTED')"
                      >
                        拒绝
                      </button>
                      <button
                        class="h-7 rounded-[6px] border border-black/10 px-2 text-[11px] disabled:opacity-50"
                        :disabled="recommendationUpdatingMap[rec.id]"
                        @click="setRecommendationStatus(rec.id, 'PENDING')"
                      >
                        待处理
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="error" class="border-t border-black/10 px-4 py-2 text-[12px] text-[#B91C1C]">{{ error }}</div>
        <div v-else-if="success" class="border-t border-black/10 px-4 py-2 text-[12px] text-[#166534]">{{ success }}</div>
      </section>
    </div>
  </div>
</template>
