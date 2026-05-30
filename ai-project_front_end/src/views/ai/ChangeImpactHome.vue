<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { fetchRequirementDocs, type RequirementDoc, type RequirementDocStatus } from '@/lib/api/requirements'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || '').trim())

const loading = ref(false)
const error = ref('')
const docs = ref<RequirementDoc[]>([])

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

async function load() {
  if (!projectId.value) return
  loading.value = true
  error.value = ''
  try {
    const data = await fetchRequirementDocs(projectId.value, { page: 1, pageSize: 8 })
    docs.value = data.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载变更影响入口失败'
    docs.value = []
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
          <h1 class="text-[16px] font-semibold leading-6 text-[#0A0A0A]">变更影响分析</h1>
          <p class="mt-1 text-[12px] leading-4 text-[#717182]">从需求文档详情选择版本对比，生成变更集和回归建议。</p>
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
          <div class="text-[12px] leading-4 text-[#717182]">可对比文档</div>
          <div class="mt-2 text-[22px] font-semibold leading-7 text-[#0A0A0A]">{{ docs.length }}</div>
        </div>
        <div class="rounded-[10px] border border-black/10 bg-white p-4">
          <div class="text-[12px] leading-4 text-[#717182]">推荐动作</div>
          <div class="mt-2 text-[16px] font-semibold leading-6 text-[#0A0A0A]">选择文档版本</div>
        </div>
        <div class="rounded-[10px] border border-black/10 bg-white p-4">
          <div class="text-[12px] leading-4 text-[#717182]">输出结果</div>
          <div class="mt-2 text-[16px] font-semibold leading-6 text-[#0A0A0A]">变更集 / 回归建议</div>
        </div>
      </div>

      <section class="rounded-[10px] border border-black/10 bg-white p-4">
        <div class="mb-3 flex items-center justify-between gap-3">
          <div class="text-[14px] font-semibold leading-5 text-[#0A0A0A]">最近需求文档</div>
          <RouterLink
            :to="`/projects/${encodeURIComponent(projectId)}/knowledge/retrospectives`"
            class="inline-flex h-8 items-center justify-center rounded-[8px] border border-black/10 bg-white px-3 text-[12px] text-[#374151]"
          >
            查看知识沉淀
          </RouterLink>
        </div>

        <div v-if="loading" class="py-8 text-center text-[12px] text-[#717182]">加载中...</div>
        <div v-else-if="docs.length === 0" class="rounded-[8px] bg-[#F8FAFC] px-3 py-6 text-center text-[12px] text-[#717182]">
          暂无需求文档
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="doc in docs"
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
              <div class="mt-1 text-[12px] leading-4 text-[#717182]">进入文档详情后可选择版本生成变更集</div>
            </div>
            <RouterLink
              :to="`/projects/${encodeURIComponent(projectId)}/requirements/docs/${encodeURIComponent(doc.id)}`"
              class="inline-flex h-8 items-center justify-center rounded-[8px] bg-[#155DFC] px-3 text-[12px] font-medium text-white"
            >
              打开文档
            </RouterLink>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
