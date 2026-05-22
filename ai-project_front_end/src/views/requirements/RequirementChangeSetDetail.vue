<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchRequirementChangeSetDetail,
  fetchRequirementRegressionSetByChangeSet,
  generateRequirementRegressionSet,
  type RequirementChangeSetDetail,
  type RequirementRegressionCase,
  type RequirementRegressionSetDetail
} from '@/lib/api/requirementChanges'
import { evaluateKnowledgeRecommendations, type KnowledgeRecommendation } from '@/lib/api/knowledge'
import VersionDiffViewer from '@/components/VersionDiffViewer.vue'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => String(route.params.projectId || '').trim())
const changeSetId = computed(() => String(route.params.changeSetId || '').trim())

const loading = ref(false)
const generating = ref(false)
const error = ref('')
const success = ref('')
const detail = ref<RequirementChangeSetDetail | null>(null)
const regressionSet = ref<RequirementRegressionSetDetail | null>(null)
const knowledgeRecommendations = ref<KnowledgeRecommendation[]>([])
const knowledgeLoading = ref(false)
const knowledgeError = ref('')
let loadSeq = 0

const changeItems = computed(() => detail.value?.items || [])
const regressionCases = computed(() => regressionSet.value?.cases || [])
const highImpactCount = computed(() =>
  changeItems.value.filter((item) => ['HIGH', 'CRITICAL'].includes(String(item.impactLevel || '').toUpperCase())).length
)

async function load() {
  const pid = projectId.value
  const cid = changeSetId.value
  if (!pid || !cid) return
  const seq = ++loadSeq
  loading.value = true
  error.value = ''
  success.value = ''
  regressionSet.value = null
  knowledgeRecommendations.value = []
  knowledgeError.value = ''
  knowledgeLoading.value = true
  try {
    const [data, existingRegressionSet, recommendationResult] = await Promise.all([
      fetchRequirementChangeSetDetail(pid, cid),
      fetchRequirementRegressionSetByChangeSet(pid, cid),
      evaluateKnowledgeRecommendations(pid, 'CHANGE_SET', cid, 5).catch((reason) => {
        knowledgeError.value = reason instanceof Error ? reason.message : '加载推荐经验失败'
        return { targetType: 'CHANGE_SET', targetId: cid, recommendations: [] }
      })
    ])
    if (seq !== loadSeq || pid !== projectId.value || cid !== changeSetId.value) return
    detail.value = data
    regressionSet.value = existingRegressionSet
    knowledgeRecommendations.value = recommendationResult.recommendations || []
  } catch (e) {
    if (seq !== loadSeq) return
    error.value = e instanceof Error ? e.message : '加载变更影响分析失败'
    detail.value = null
  } finally {
    if (seq === loadSeq) knowledgeLoading.value = false
    if (seq === loadSeq) loading.value = false
  }
}

async function createRegressionSet() {
  const pid = projectId.value
  const cid = changeSetId.value
  if (!pid || !cid) return
  generating.value = true
  error.value = ''
  success.value = ''
  try {
    const data = await generateRequirementRegressionSet(pid, cid)
    if (pid !== projectId.value || cid !== changeSetId.value) return
    regressionSet.value = data
    success.value = regressionCases.value.length ? '回归集已刷新' : '回归集已生成'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '生成回归集失败'
  } finally {
    generating.value = false
  }
}

function backToDoc() {
  if (!detail.value) return
  void router.push(`/projects/${encodeURIComponent(projectId.value)}/requirements/docs/${encodeURIComponent(detail.value.docId)}`)
}

function goToRetrospectives() {
  void router.push(`/projects/${encodeURIComponent(projectId.value)}/knowledge/retrospectives`)
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

function impactClass(level: string) {
  const value = String(level || '').toUpperCase()
  if (value === 'CRITICAL') return 'border-[#EF4444]/30 bg-[#FEF2F2] text-[#B91C1C]'
  if (value === 'HIGH') return 'border-[#F97316]/30 bg-[#FFF7ED] text-[#C2410C]'
  if (value === 'MEDIUM') return 'border-[#EAB308]/30 bg-[#FEFCE8] text-[#854D0E]'
  return 'border-[#22C55E]/30 bg-[#F0FDF4] text-[#166534]'
}

function casePriorityClass(row: RequirementRegressionCase) {
  const value = String(row.priority || '').toUpperCase()
  if (['P0', 'CRITICAL', 'HIGH'].includes(value)) return 'text-[#B91C1C]'
  if (['P1', 'MEDIUM'].includes(value)) return 'text-[#C2410C]'
  return 'text-[#166534]'
}

watch(
  () => [projectId.value, changeSetId.value],
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
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-[14px] font-semibold text-[#0A0A0A]">变更影响分析</h2>
          <div class="flex items-center gap-2">
            <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px]" @click="goToRetrospectives">复盘中心</button>
            <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px]" @click="backToDoc">返回文档</button>
          </div>
        </div>

        <div class="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div class="rounded-[8px] border border-black/10 bg-[#FAFAFA] p-3">
            <div class="text-[12px] text-[#717182]">变更点</div>
            <div class="mt-1 text-[22px] font-semibold text-[#0A0A0A]">{{ changeItems.length }}</div>
          </div>
          <div class="rounded-[8px] border border-black/10 bg-[#FAFAFA] p-3">
            <div class="text-[12px] text-[#717182]">高影响</div>
            <div class="mt-1 text-[22px] font-semibold text-[#B91C1C]">{{ highImpactCount }}</div>
          </div>
        </div>

        <dl class="mt-4 space-y-3 text-[12px]">
          <div>
            <dt class="text-[#717182]">状态</dt>
            <dd class="mt-1 text-[#0A0A0A]">{{ detail.status }}</dd>
          </div>
          <div>
            <dt class="text-[#717182]">基线版本</dt>
            <dd class="mt-1 break-all text-[#0A0A0A]">{{ detail.baselineVersionId }}</dd>
          </div>
          <div>
            <dt class="text-[#717182]">目标版本</dt>
            <dd class="mt-1 break-all text-[#0A0A0A]">{{ detail.targetVersionId }}</dd>
          </div>
          <div>
            <dt class="text-[#717182]">创建时间</dt>
            <dd class="mt-1 text-[#0A0A0A]">{{ formatTime(detail.createdAt) }}</dd>
          </div>
        </dl>

        <div class="mt-4 rounded-[8px] bg-[#F8FAFC] p-3 text-[12px] leading-5 text-[#4A5565]">
          {{ detail.summary || '暂无摘要' }}
        </div>

        <button class="mt-4 h-9 rounded-[8px] bg-[#155DFC] px-4 text-[13px] text-white disabled:opacity-60" :disabled="generating" @click="createRegressionSet">
          {{ generating ? '生成中...' : regressionSet ? '刷新回归集' : '生成回归集' }}
        </button>

        <div class="mt-4 border-t border-black/10 pt-4">
          <div class="text-[13px] font-medium text-[#0A0A0A]">推荐经验</div>
          <div v-if="knowledgeLoading" class="mt-2 text-[12px] text-[#717182]">加载中...</div>
          <div v-else-if="knowledgeError" class="mt-2 text-[12px] text-[#B91C1C]">{{ knowledgeError }}</div>
          <div v-else-if="knowledgeRecommendations.length === 0" class="mt-2 text-[12px] text-[#717182]">暂无推荐经验。</div>
          <div v-else class="mt-2 space-y-2">
            <article v-for="item in knowledgeRecommendations" :key="item.id" class="rounded-[8px] border border-black/10 bg-[#FAFAFA] p-2">
              <div class="flex flex-wrap items-center gap-2 text-[11px]">
                <span class="rounded-[6px] bg-[#EFF6FF] px-2 py-0.5 text-[#155DFC]">score: {{ item.score ?? '-' }}</span>
                <span class="rounded-[6px] bg-[#F4F4F5] px-2 py-0.5 text-[#4A5565]">{{ item.status || '-' }}</span>
                <span class="rounded-[6px] bg-[#F4F4F5] px-2 py-0.5 text-[#4A5565]">{{ item.type || '-' }}</span>
              </div>
              <p class="mt-1 text-[12px] leading-5 text-[#0A0A0A]">{{ item.content || '-' }}</p>
            </article>
          </div>
        </div>
      </section>

      <section class="rounded-[12px] border border-black/10 bg-white">
        <div class="border-b border-black/10 px-4 py-3">
          <div class="text-[14px] font-semibold text-[#0A0A0A]">影响项</div>
          <div class="mt-1 text-[12px] text-[#717182]">按后端识别出的变更类型和影响级别展示，可作为回归测试入口。</div>
        </div>

        <div class="px-4 py-3 border-b border-black/10">
          <VersionDiffViewer :items="changeItems" />
        </div>
        <div v-if="changeItems.length === 0" class="px-4 py-6 text-[12px] text-[#717182]">暂无变更项。</div>
        <div v-else class="divide-y divide-black/10">
          <article v-for="item in changeItems" :key="item.id" class="px-4 py-3">
            <div class="flex flex-wrap items-center gap-2">
              <span class="rounded-[6px] border px-2 py-1 text-[11px]" :class="impactClass(item.impactLevel)">{{ item.impactLevel }}</span>
              <span class="rounded-[6px] bg-[#F4F4F5] px-2 py-1 text-[11px] text-[#4A5565]">{{ item.changeType }}</span>
              <span v-if="item.sourcePath" class="rounded-[6px] bg-[#EFF6FF] px-2 py-1 text-[11px] text-[#155DFC]">{{ item.sourcePath }}</span>
            </div>
            <h3 class="mt-2 text-[13px] font-medium text-[#0A0A0A]">{{ item.title || '-' }}</h3>
            <p class="mt-1 text-[12px] leading-5 text-[#4A5565]">{{ item.description || '暂无描述' }}</p>
          </article>
        </div>
      </section>

      <section class="rounded-[12px] border border-black/10 bg-white xl:col-span-2">
        <div class="border-b border-black/10 px-4 py-3">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div class="text-[14px] font-semibold text-[#0A0A0A]">回归集</div>
              <div class="mt-1 text-[12px] text-[#717182]">
                {{ regressionSet ? `${regressionCases.length} 条候选用例 · ${regressionSet.status}` : '点击“生成回归集”后展示候选用例。' }}
              </div>
            </div>
            <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px] disabled:opacity-60" :disabled="generating" @click="createRegressionSet">
              {{ generating ? '处理中...' : '生成/刷新' }}
            </button>
          </div>
        </div>
        <div v-if="!regressionSet" class="px-4 py-6 text-[12px] text-[#717182]">尚未生成回归集。</div>
        <div v-else-if="regressionCases.length === 0" class="px-4 py-6 text-[12px] text-[#717182]">暂无命中的回归用例。</div>
        <div v-else class="overflow-x-auto">
          <table class="w-full min-w-[980px] border-collapse">
            <thead>
              <tr class="bg-[rgba(236,236,240,0.3)]">
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">用例</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">优先级</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">命中原因</th>
                <th class="px-3 py-2 text-left text-[12px] font-medium text-[#717182]">来源路径</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in regressionCases" :key="row.id" class="border-t border-black/10 align-top">
                <td class="px-3 py-2 text-[12px] text-[#0A0A0A]">
                  <div class="font-medium">{{ row.testcaseTitle || '-' }}</div>
                  <div class="mt-1 break-all text-[#717182]">ID: {{ row.testcaseId }}</div>
                </td>
                <td class="px-3 py-2 text-[12px] font-medium" :class="casePriorityClass(row)">{{ row.priority || '-' }}</td>
                <td class="px-3 py-2 text-[12px] text-[#4A5565]">{{ row.reason || '-' }}</td>
                <td class="px-3 py-2 text-[12px] text-[#4A5565]">{{ row.sourcePaths.length ? row.sourcePaths.join(' / ') : '-' }}</td>
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
