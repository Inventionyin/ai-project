<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { assignDefect, getDefectDetail, transitionDefect, type DefectDetailData, type DefectStatus } from '@/lib/api/defects'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => String(route.params.projectId || '').trim())
const defectId = computed(() => String(route.params.defectId || '').trim())

const loading = ref(false)
const assigning = ref(false)
const transitioning = ref(false)
const error = ref('')
const actionError = ref('')
const success = ref('')

const detail = ref<DefectDetailData | null>(null)
const assigneeId = ref('')
const toStatus = ref<DefectStatus | ''>('')
const transitionComment = ref('')

const transitionOptions: DefectStatus[] = ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED']

const timeline = computed(() => detail.value?.timeline || detail.value?.events || [])

function formatTime(ts?: number | null) {
  if (!ts) return '-'
  const value = ts < 100000000000 ? ts * 1000 : ts
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(
    date.getHours()
  ).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}

function statusClass(value?: string) {
  if (value === 'OPEN' || value === 'REOPENED') return 'bg-[#FEE2E2] text-[#B91C1C]'
  if (value === 'IN_PROGRESS') return 'bg-[#DBEAFE] text-[#1D4ED8]'
  if (value === 'RESOLVED') return 'bg-[#FEF3C7] text-[#92400E]'
  if (value === 'CLOSED') return 'bg-[#DCFCE7] text-[#166534]'
  return 'bg-[#E5E7EB] text-[#4B5563]'
}

async function loadDetail() {
  const pid = projectId.value
  const did = defectId.value
  if (!pid || !did) return
  loading.value = true
  error.value = ''
  actionError.value = ''
  success.value = ''
  try {
    const data = await getDefectDetail(pid, did)
    detail.value = data
    assigneeId.value = String(data.assigneeId || '').trim()
    toStatus.value = ''
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载缺陷详情失败'
    detail.value = null
  } finally {
    loading.value = false
  }
}

async function submitAssign() {
  const pid = projectId.value
  const did = defectId.value
  const aid = assigneeId.value.trim()
  if (!pid || !did) return
  if (!aid) {
    actionError.value = '请填写 assigneeId'
    return
  }
  assigning.value = true
  actionError.value = ''
  success.value = ''
  try {
    const updated = await assignDefect(pid, did, aid)
    detail.value = updated
    success.value = '指派成功'
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : '指派失败'
  } finally {
    assigning.value = false
  }
}

async function submitTransition() {
  const pid = projectId.value
  const did = defectId.value
  if (!pid || !did) return
  if (!toStatus.value) {
    actionError.value = '请选择目标状态'
    return
  }
  transitioning.value = true
  actionError.value = ''
  success.value = ''
  try {
    const updated = await transitionDefect(pid, did, toStatus.value, transitionComment.value.trim())
    detail.value = updated
    toStatus.value = ''
    transitionComment.value = ''
    success.value = '状态流转成功'
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : '状态流转失败'
  } finally {
    transitioning.value = false
  }
}

function backToList() {
  void router.push(`/projects/${encodeURIComponent(projectId.value)}/defects`)
}

watch(
  () => [projectId.value, defectId.value],
  () => {
    void loadDetail()
  },
  { immediate: true }
)
</script>

<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-4 md:p-6">
    <div v-if="loading" class="rounded-[12px] border border-black/10 bg-white px-4 py-5 text-[13px] text-[#717182]">加载中...</div>
    <div v-else-if="error" class="rounded-[12px] border border-black/10 bg-white px-4 py-5 text-[13px] text-[#B91C1C]">{{ error }}</div>
    <div v-else-if="detail" class="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section class="rounded-[12px] border border-black/10 bg-white">
        <div class="flex items-center justify-between border-b border-black/10 px-4 py-3">
          <div>
            <div class="text-[14px] font-semibold text-[#0A0A0A]">缺陷详情</div>
            <div class="mt-1 font-mono text-[12px] text-[#155DFC]">{{ detail.id }}</div>
          </div>
          <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px]" @click="backToList">返回列表</button>
        </div>

        <div class="space-y-4 p-4">
          <div>
            <div class="text-[12px] text-[#717182]">标题</div>
            <div class="mt-1 text-[14px] font-medium text-[#0A0A0A]">{{ detail.title }}</div>
          </div>

          <div>
            <div class="text-[12px] text-[#717182]">描述</div>
            <pre class="mt-1 whitespace-pre-wrap break-all rounded-[8px] border border-black/10 bg-[#FAFAFA] p-3 text-[12px] text-[#0A0A0A]">{{ detail.description || '-' }}</pre>
          </div>

          <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <div class="text-[12px] text-[#717182]">状态</div>
              <div class="mt-1">
                <span class="rounded-full px-2 py-[2px] text-[11px] font-medium" :class="statusClass(detail.status)">{{ detail.status || '-' }}</span>
              </div>
            </div>
            <div>
              <div class="text-[12px] text-[#717182]">指派人</div>
              <div class="mt-1 text-[13px] text-[#0A0A0A]">{{ detail.assigneeName || detail.assigneeId || '-' }}</div>
            </div>
            <div class="text-[12px] text-[#4A5565]">runId：{{ detail.runId || '-' }}</div>
            <div class="text-[12px] text-[#4A5565]">caseRunId：{{ detail.caseRunId || '-' }}</div>
            <div class="text-[12px] text-[#4A5565]">testcaseId：{{ detail.testcaseId || '-' }}</div>
            <div class="text-[12px] text-[#717182]">更新时间：{{ formatTime(detail.updatedAt ?? detail.createdAt) }}</div>
          </div>
        </div>

        <div class="border-t border-black/10 px-4 py-3">
          <div class="mb-2 text-[13px] font-medium text-[#0A0A0A]">时间线</div>
          <div v-if="timeline.length === 0" class="rounded-[8px] border border-dashed border-black/10 px-3 py-4 text-[12px] text-[#717182]">暂无事件</div>
          <div v-else class="space-y-2">
            <div v-for="(event, index) in timeline" :key="event.id || `${event.type || 'event'}-${index}`" class="rounded-[8px] border border-black/10 bg-[#FAFAFA] px-3 py-2">
              <div class="text-[12px] text-[#0A0A0A]">{{ event.type || 'EVENT' }} · {{ event.operatorName || event.operatorId || '-' }}</div>
              <div class="mt-1 text-[12px] text-[#4A5565]">{{ event.content || '-' }}</div>
              <div class="mt-1 text-[11px] text-[#717182]">{{ formatTime(event.createdAt) }}</div>
            </div>
          </div>
        </div>
      </section>

      <section class="rounded-[12px] border border-black/10 bg-white p-4">
        <div class="text-[13px] font-medium text-[#0A0A0A]">状态流转与指派</div>

        <div class="mt-3 space-y-4">
          <div>
            <div class="text-[12px] text-[#717182]">指派人 ID</div>
            <div class="mt-1 flex gap-2">
              <input v-model="assigneeId" class="h-9 flex-1 rounded-[8px] border border-black/10 px-3 text-[13px]" placeholder="输入 assigneeId" />
              <button class="h-9 rounded-[8px] bg-[#155DFC] px-3 text-[12px] text-white disabled:opacity-60" :disabled="assigning" @click="submitAssign">
                {{ assigning ? '提交中...' : '指派' }}
              </button>
            </div>
          </div>

          <div>
            <div class="text-[12px] text-[#717182]">状态流转</div>
            <div class="mt-1 flex gap-2">
              <select v-model="toStatus" class="h-9 flex-1 rounded-[8px] border border-black/10 px-2 text-[13px]">
                <option value="">选择目标状态</option>
                <option v-for="item in transitionOptions" :key="item" :value="item">{{ item }}</option>
              </select>
              <button class="h-9 rounded-[8px] bg-[#155DFC] px-3 text-[12px] text-white disabled:opacity-60" :disabled="transitioning" @click="submitTransition">
                {{ transitioning ? '提交中...' : '流转' }}
              </button>
            </div>
            <textarea
              v-model="transitionComment"
              class="mt-2 min-h-[80px] w-full rounded-[8px] border border-black/10 px-3 py-2 text-[13px]"
              placeholder="流转备注（可选）"
            />
          </div>
        </div>

        <div v-if="actionError" class="mt-3 text-[12px] text-[#B91C1C]">{{ actionError }}</div>
        <div v-else-if="success" class="mt-3 text-[12px] text-[#166534]">{{ success }}</div>
      </section>
    </div>
  </div>
</template>
