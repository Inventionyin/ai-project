<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  fetchRequirementAnalyses,
  fetchRequirementDocs,
  type RequirementAnalysis,
  type RequirementDoc,
  type RequirementDocStatus
} from '@/lib/api/requirements'

type DocWithAnalysis = RequirementDoc & {
  latestAnalysis?: RequirementAnalysis | null
}

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || '').trim())

const loading = ref(false)
const error = ref('')
const docs = ref<RequirementDoc[]>([])
const analyses = ref<RequirementAnalysis[]>([])

function statusLabel(value: RequirementDocStatus) {
  if (value === 'PUBLISHED') return '已发布'
  if (value === 'REVIEWING') return '评审中'
  if (value === 'ARCHIVED') return '已归档'
  return '草稿'
}

function statusClass(value: RequirementDocStatus) {
  if (value === 'PUBLISHED') return 'bg-[#DCFCE7] text-[#166534]'
  if (value === 'REVIEWING') return 'bg-[#FEF3C7] text-[#92400E]'
  if (value === 'ARCHIVED') return 'bg-[#E5E7EB] text-[#4B5563]'
  return 'bg-[#DBEAFE] text-[#1D4ED8]'
}

function riskLabel(value?: string | null) {
  const normalized = String(value || '').toUpperCase()
  if (normalized === 'CRITICAL') return '关键风险'
  if (normalized === 'HIGH') return '高风险'
  if (normalized === 'LOW') return '低风险'
  return '中风险'
}

function formatTime(ts?: number | null) {
  if (!ts) return '-'
  const value = ts < 100000000000 ? ts * 1000 : ts
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

const analysisMap = computed(() => {
  const sorted = [...analyses.value].sort((a, b) => Number(b.updatedAt || b.createdAt || 0) - Number(a.updatedAt || a.createdAt || 0))
  const map = new Map<string, RequirementAnalysis>()
  for (const item of sorted) {
    if (!map.has(item.docId)) {
      map.set(item.docId, item)
    }
  }
  return map
})

const docRows = computed<DocWithAnalysis[]>(() =>
  docs.value.map((item) => ({
    ...item,
    latestAnalysis: analysisMap.value.get(item.id) || null
  }))
)

const latestAnalyses = computed(() =>
  [...analyses.value].sort((a, b) => Number(b.updatedAt || b.createdAt || 0) - Number(a.updatedAt || a.createdAt || 0)).slice(0, 6)
)

async function load() {
  if (!projectId.value) return
  loading.value = true
  error.value = ''
  try {
    const [docResult, analysisResult] = await Promise.all([
      fetchRequirementDocs(projectId.value, { page: 1, pageSize: 8 }),
      fetchRequirementAnalyses(projectId.value)
    ])
    docs.value = docResult.items
    analyses.value = analysisResult
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载需求解析入口失败'
    docs.value = []
    analyses.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-4 md:p-6">
    <div class="flex flex-col gap-4">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 class="text-[16px] font-semibold leading-6 text-[#0A0A0A]">需求解析</h1>
          <p class="mt-1 text-[12px] leading-4 text-[#717182]">从需求文档进入解析结果、测试点和候选用例治理。</p>
        </div>
        <div class="flex gap-2">
          <button class="h-9 rounded-[8px] border border-black/10 bg-white px-4 text-[13px] text-[#0A0A0A]" @click="load">
            {{ loading ? '刷新中...' : '刷新' }}
          </button>
          <RouterLink
            :to="`/projects/${encodeURIComponent(projectId)}/requirements/docs`"
            class="inline-flex h-9 items-center justify-center rounded-[8px] bg-[#155DFC] px-4 text-[13px] font-medium text-white"
          >
            进入需求文档
          </RouterLink>
        </div>
      </div>

      <div v-if="error" class="rounded-[8px] border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
        {{ error }}
      </div>

      <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
        <div class="rounded-[10px] border border-black/10 bg-white p-4">
          <div class="text-[12px] leading-4 text-[#717182]">需求文档</div>
          <div class="mt-2 text-[22px] font-semibold leading-7 text-[#0A0A0A]">{{ docs.length }}</div>
        </div>
        <div class="rounded-[10px] border border-black/10 bg-white p-4">
          <div class="text-[12px] leading-4 text-[#717182]">已生成解析</div>
          <div class="mt-2 text-[22px] font-semibold leading-7 text-[#0A0A0A]">{{ analyses.length }}</div>
        </div>
        <div class="rounded-[10px] border border-black/10 bg-white p-4">
          <div class="text-[12px] leading-4 text-[#717182]">最近解析时间</div>
          <div class="mt-2 text-[16px] font-semibold leading-6 text-[#0A0A0A]">
            {{ formatTime(latestAnalyses[0]?.updatedAt || latestAnalyses[0]?.createdAt) }}
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <section class="rounded-[10px] border border-black/10 bg-white p-4">
          <div class="mb-3 flex items-center justify-between gap-3">
            <div class="text-[14px] font-semibold leading-5 text-[#0A0A0A]">文档入口</div>
            <div class="text-[12px] leading-4 text-[#717182]">优先从真实需求文档进入</div>
          </div>

          <div v-if="loading" class="py-8 text-center text-[12px] text-[#717182]">加载中...</div>
          <div v-else-if="docRows.length === 0" class="rounded-[8px] bg-[#F8FAFC] px-3 py-6 text-center text-[12px] text-[#717182]">
            暂无需求文档
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="doc in docRows"
              :key="doc.id"
              class="flex flex-col gap-3 rounded-[8px] border border-black/10 p-3 md:flex-row md:items-center md:justify-between"
            >
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <div class="truncate text-[13px] font-semibold leading-5 text-[#0A0A0A]">{{ doc.title }}</div>
                  <span class="rounded-full px-2 py-0.5 text-[11px] font-medium" :class="statusClass(doc.status)">
                    {{ statusLabel(doc.status) }}
                  </span>
                </div>
                <div class="mt-1 text-[12px] leading-4 text-[#717182]">
                  最近解析：
                  <template v-if="doc.latestAnalysis">
                    {{ riskLabel(doc.latestAnalysis.riskLevel) }} · 覆盖 {{ Number(doc.latestAnalysis.coverageScore || 0).toFixed(0) }}
                  </template>
                  <template v-else>未生成</template>
                </div>
              </div>
              <div class="flex flex-wrap gap-2">
                <RouterLink
                  :to="`/projects/${encodeURIComponent(projectId)}/requirements/docs/${encodeURIComponent(doc.id)}`"
                  class="inline-flex h-8 items-center justify-center rounded-[8px] border border-black/10 bg-white px-3 text-[12px] text-[#374151]"
                >
                  打开文档
                </RouterLink>
                <RouterLink
                  v-if="doc.latestAnalysis"
                  :to="`/projects/${encodeURIComponent(projectId)}/requirements/analyses/${encodeURIComponent(doc.latestAnalysis.id)}`"
                  class="inline-flex h-8 items-center justify-center rounded-[8px] bg-[#155DFC] px-3 text-[12px] font-medium text-white"
                >
                  查看解析
                </RouterLink>
              </div>
            </div>
          </div>
        </section>

        <section class="rounded-[10px] border border-black/10 bg-white p-4">
          <div class="mb-3 text-[14px] font-semibold leading-5 text-[#0A0A0A]">最近解析</div>
          <div v-if="loading" class="py-8 text-center text-[12px] text-[#717182]">加载中...</div>
          <div v-else-if="latestAnalyses.length === 0" class="rounded-[8px] bg-[#F8FAFC] px-3 py-6 text-center text-[12px] text-[#717182]">
            暂无解析记录
          </div>
          <div v-else class="space-y-2">
            <RouterLink
              v-for="analysis in latestAnalyses"
              :key="analysis.id"
              :to="`/projects/${encodeURIComponent(projectId)}/requirements/analyses/${encodeURIComponent(analysis.id)}`"
              class="block rounded-[8px] border border-black/10 p-3 hover:border-[#155DFC]/40 hover:bg-[#F8FBFF]"
            >
              <div class="flex items-center justify-between gap-3">
                <div class="text-[13px] font-semibold leading-5 text-[#0A0A0A]">{{ riskLabel(analysis.riskLevel) }}</div>
                <div class="text-[11px] leading-4 text-[#717182]">{{ formatTime(analysis.updatedAt || analysis.createdAt) }}</div>
              </div>
              <div class="mt-1 text-[12px] leading-5 text-[#374151]">{{ analysis.summary || '已生成解析结果，可继续同步测试点和候选用例。' }}</div>
            </RouterLink>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
