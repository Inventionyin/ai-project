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

      <div class="mt-5 grid gap-3 md:grid-cols-3">
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
      </div>

      <div class="mt-3 flex gap-2">
        <button class="rounded bg-[#155DFC] px-3 py-1 text-[12px] text-white" @click="savePolicy">保存策略</button>
        <button class="rounded border border-black/10 px-3 py-1 text-[12px]" @click="revoke">吊销 Token</button>
      </div>

      <div v-if="loading" class="py-8 text-center text-[12px] text-[#717182]">加载中...</div>

      <div v-else class="mt-5 grid gap-3 md:grid-cols-2">
        <div class="rounded border border-black/10 p-4">
          <div class="text-[13px] font-medium">当前状态</div>
          <div class="mt-2 grid gap-1 text-[12px] text-[#474747]">
            <div>状态：{{ statusLabel }}</div>
            <div>Hint：{{ status?.hint || '-' }}</div>
            <div>最近轮换：{{ formatTime(status?.rotatedAt) }}</div>
            <div>最后使用：{{ formatTime(status?.lastUsedAt) }}</div>
            <div>轮换人：{{ status?.rotatedBy || '-' }}</div>
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
import { getCiTokenStatus, revokeCiToken, rotateCiToken, updateCiTokenPolicy, type CiTokenPolicy, type CiTokenStatus } from '@/lib/api/ciTokenGovernance'

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

const policy = computed<CiTokenPolicy>(() => ({
  allowedRunnerTypes: runnerTypesText.value.split(',').map((v) => v.trim()).filter(Boolean),
  allowedTestCaseIds: testcaseIdsText.value.split(',').map((v) => v.trim()).filter(Boolean),
  maxTestCaseCount: maxCountText.value ? Number(maxCountText.value) : null,
}))

const statusLabel = computed(() => (status.value?.enabled ? '已启用' : '已吊销'))

function formatTime(ts: number | null | undefined) {
  return ts ? new Date(ts * 1000).toLocaleString('zh-CN') : '-'
}

function syncFormFromStatus() {
  runnerTypesText.value = status.value?.policy.allowedRunnerTypes.join(', ') || ''
  testcaseIdsText.value = status.value?.policy.allowedTestCaseIds.join(', ') || ''
  maxCountText.value = status.value?.policy.maxTestCaseCount != null ? String(status.value.policy.maxTestCaseCount) : ''
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
    const res = await rotateCiToken(projectId, policy.value)
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
    status.value = await revokeCiToken(projectId)
    token.value = ''
    syncFormFromStatus()
    feedback.value = 'Token 已吊销'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '吊销失败'
  }
}

onMounted(reload)
</script>
