<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-6">
    <div class="rounded-[14px] border border-black/10 bg-white p-6">
      <div class="flex items-start justify-between gap-4">
        <div>
          <div class="text-[16px] font-semibold text-[#0A0A0A]">CI Token 治理</div>
          <div class="mt-1 text-[12px] text-[#717182]">管理触发策略、查看状态、轮换或吊销项目 CI Token</div>
        </div>
        <div class="flex gap-2">
          <button class="rounded border border-black/10 px-3 py-1 text-[12px]" @click="reload">刷新</button>
          <button class="rounded bg-[#155DFC] px-3 py-1 text-[12px] text-white" @click="rotate">轮换 Token</button>
        </div>
      </div>

      <div class="mt-5 grid gap-3 md:grid-cols-4">
        <label class="grid gap-1 text-[12px]">
          <span class="text-[#717182]">允许 RunnerType</span>
          <input v-model="runnerTypesText" placeholder="DEFAULT,PYTEST_ALLURE" class="rounded border border-black/10 px-2 py-1" />
        </label>
        <label class="grid gap-1 text-[12px]">
          <span class="text-[#717182]">允许 TestCaseId</span>
          <input v-model="testcaseIdsText" placeholder="uuid1,uuid2" class="rounded border border-black/10 px-2 py-1" />
        </label>
        <label class="grid gap-1 text-[12px]">
          <span class="text-[#717182]">最大用例数</span>
          <input v-model="maxCountText" type="number" min="1" class="rounded border border-black/10 px-2 py-1" />
        </label>
        <label class="grid gap-1 text-[12px]">
          <span class="text-[#717182]">过期时间</span>
          <input v-model="expiresAtText" type="datetime-local" class="rounded border border-black/10 px-2 py-1" />
        </label>
      </div>

      <div class="mt-3 grid gap-3 md:grid-cols-[1fr_auto_auto_auto]">
        <input v-model="reasonText" placeholder="吊销/泄露原因，可选" class="rounded border border-black/10 px-2 py-1 text-[12px]" />
        <button class="rounded bg-[#155DFC] px-3 py-1 text-[12px] text-white" @click="savePolicy">保存策略</button>
        <button class="rounded border border-black/10 px-3 py-1 text-[12px]" @click="revoke">吊销 Token</button>
        <button class="rounded border border-red-200 bg-red-50 px-3 py-1 text-[12px] text-red-700" @click="reportLeak">上报泄露</button>
      </div>

      <div v-if="loading" class="py-8 text-center text-[12px] text-[#717182]">加载中...</div>

      <div v-else class="mt-5 grid gap-3 md:grid-cols-2">
        <div class="rounded border border-black/10 p-4">
          <div class="text-[13px] font-medium">当前状态</div>
          <div class="mt-2 grid gap-1 text-[12px] text-[#474747]">
            <div>状态：{{ statusLabel }}</div>
            <div>Hint：{{ status?.hint || '-' }}</div>
            <div>最近轮换：{{ formatTime(status?.rotatedAt) }}</div>
            <div>过期时间：{{ formatTime(status?.expiresAt) }}</div>
            <div>最后使用：{{ formatTime(status?.lastUsedAt) }}</div>
            <div>轮换人：{{ status?.rotatedBy || '-' }}</div>
            <div>吊销时间：{{ formatTime(status?.revokedAt) }}</div>
            <div>吊销原因：{{ status?.revokedReason || '-' }}</div>
            <div>泄露上报：{{ formatTime(status?.leakReportedAt) }}</div>
            <div>泄露原因：{{ status?.leakReportReason || '-' }}</div>
          </div>
          <div v-if="token" class="mt-3 rounded bg-green-50 px-3 py-2 text-[12px] text-green-700">
            新 Token：{{ token }}
          </div>
        </div>
        <div class="rounded border border-black/10 p-4">
          <div class="text-[13px] font-medium">策略摘要</div>
          <div class="mt-2 grid gap-1 text-[12px] text-[#474747]">
            <div>RunnerType：{{ policy.allowedRunnerTypes.join(', ') || '-' }}</div>
            <div>TestCase：{{ policy.allowedTestCaseIds.length || 0 }}</div>
            <div>MaxCount：{{ policy.maxTestCaseCount ?? '-' }}</div>
          </div>
          <div v-if="feedback" class="mt-3 rounded bg-blue-50 px-3 py-2 text-[12px] text-blue-700">{{ feedback }}</div>
          <div v-if="error" class="mt-3 rounded bg-red-50 px-3 py-2 text-[12px] text-red-700">{{ error }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getCiTokenStatus, reportCiTokenLeak, revokeCiToken, rotateCiToken, updateCiTokenPolicy, type CiTokenPolicy, type CiTokenStatus } from '@/lib/api/ciTokenGovernance'

const route = useRoute()
const projectId = route.params.projectId as string

const loading = ref(false)
const status = ref<CiTokenStatus | null>(null)
const token = ref('')
const feedback = ref('')
const error = ref('')

const runnerTypesText = ref('')
const testcaseIdsText = ref('')
const maxCountText = ref('')
const expiresAtText = ref('')
const reasonText = ref('')

const policy = computed<CiTokenPolicy>(() => ({
  allowedRunnerTypes: runnerTypesText.value.split(',').map((v) => v.trim()).filter(Boolean),
  allowedTestCaseIds: testcaseIdsText.value.split(',').map((v) => v.trim()).filter(Boolean),
  maxTestCaseCount: maxCountText.value ? Number(maxCountText.value) : null,
}))

const statusLabel = computed(() => {
  const state = status.value?.state || (status.value?.enabled ? 'active' : 'disabled')
  const map: Record<string, string> = {
    active: '已启用',
    disabled: '未启用',
    expired: '已过期',
    revoked: '已吊销',
    leaked: '已泄露',
  }
  return map[state] || state
})

function formatTime(ts: number | null | undefined) {
  return ts ? new Date(ts * 1000).toLocaleString('zh-CN') : '-'
}

function formatInputTime(ts: number | null | undefined) {
  if (!ts) return ''
  const date = new Date(ts * 1000)
  const offsetMs = date.getTimezoneOffset() * 60 * 1000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
}

function parseInputTime(value: string) {
  const normalized = value.trim()
  if (!normalized) return null
  const ms = new Date(normalized).getTime()
  return Number.isFinite(ms) ? Math.floor(ms / 1000) : null
}

function syncFormFromStatus() {
  runnerTypesText.value = status.value?.policy.allowedRunnerTypes.join(', ') || ''
  testcaseIdsText.value = status.value?.policy.allowedTestCaseIds.join(', ') || ''
  maxCountText.value = status.value?.policy.maxTestCaseCount != null ? String(status.value.policy.maxTestCaseCount) : ''
  expiresAtText.value = formatInputTime(status.value?.expiresAt)
}

async function reload() {
  loading.value = true
  error.value = ''
  try {
    status.value = await getCiTokenStatus(projectId)
    syncFormFromStatus()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function savePolicy() {
  feedback.value = ''
  error.value = ''
  try {
    status.value = await updateCiTokenPolicy(projectId, policy.value)
    syncFormFromStatus()
    feedback.value = '策略已保存'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  }
}

async function rotate() {
  feedback.value = ''
  error.value = ''
  try {
    const res = await rotateCiToken(projectId, policy.value, parseInputTime(expiresAtText.value))
    status.value = res
    token.value = res.token
    syncFormFromStatus()
    feedback.value = 'Token 已轮换'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '轮换失败'
  }
}

async function revoke() {
  feedback.value = ''
  error.value = ''
  try {
    status.value = await revokeCiToken(projectId, reasonText.value)
    token.value = ''
    syncFormFromStatus()
    feedback.value = 'Token 已吊销'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '吊销失败'
  }
}

async function reportLeak() {
  feedback.value = ''
  error.value = ''
  try {
    status.value = await reportCiTokenLeak(projectId, reasonText.value)
    token.value = ''
    syncFormFromStatus()
    feedback.value = '泄露已上报'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '上报失败'
  }
}

onMounted(reload)
</script>
