<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-6">
    <div class="rounded-[8px] border border-black/10 bg-white p-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div class="text-[16px] font-semibold text-[#0A0A0A]">CI Token 治理</div>
          <div class="mt-1 text-[12px] text-[#717182]">集中查看多 Token 状态、轮换窗口、泄露处置与触发策略</div>
        </div>
        <div class="flex flex-wrap gap-2">
          <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px]" @click="reload">刷新</button>
          <button class="h-8 rounded-[8px] bg-[#155DFC] px-3 text-[12px] text-white" @click="rotate">轮换当前 Token</button>
        </div>
      </div>

      <div class="mt-5 grid gap-3 md:grid-cols-4">
        <div class="rounded-[8px] border border-black/10 bg-[#F8FAFC] p-4">
          <div class="text-[12px] text-[#717182]">当前状态</div>
          <div class="mt-2 flex items-center gap-2">
            <span class="rounded-[999px] border px-2 py-1 text-[12px]" :class="stateTagClass(statusState)">{{ stateLabel(statusState) }}</span>
            <span class="text-[12px] text-[#474747]">{{ status?.hint || '未生成' }}</span>
          </div>
        </div>
        <div class="rounded-[8px] border border-black/10 bg-[#F8FAFC] p-4">
          <div class="text-[12px] text-[#717182]">多 Token</div>
          <div class="mt-2 text-[18px] font-semibold text-[#0A0A0A]">{{ aggregate.total }}</div>
          <div class="mt-1 text-[12px] text-[#717182]">活跃 {{ aggregate.active }} / 风险 {{ aggregate.risky }}</div>
        </div>
        <div class="rounded-[8px] border border-black/10 bg-[#F8FAFC] p-4">
          <div class="text-[12px] text-[#717182]">到期提醒</div>
          <div class="mt-2 text-[13px] font-medium" :class="expiryTextClass">{{ expirySummary }}</div>
          <div class="mt-1 text-[12px] text-[#717182]">{{ formatTime(status?.expiresAt) }}</div>
        </div>
        <div class="rounded-[8px] border border-black/10 bg-[#F8FAFC] p-4">
          <div class="text-[12px] text-[#717182]">泄露处置</div>
          <div class="mt-2 text-[13px] font-medium" :class="leakTextClass">{{ leakSummary }}</div>
          <div class="mt-1 text-[12px] text-[#717182]">{{ formatTime(status?.leakReportedAt) }}</div>
        </div>
      </div>

      <div v-if="diagnostics.length" class="mt-4 grid gap-2 md:grid-cols-2">
        <div v-for="item in diagnostics" :key="item.label" class="rounded-[8px] border px-3 py-2 text-[12px]" :class="diagnosticClass(item.level)">
          <span class="font-medium">{{ item.label }}：</span>{{ item.text }}
        </div>
      </div>

      <div class="mt-5 grid gap-3 md:grid-cols-4">
        <label class="grid gap-1 text-[12px]">
          <span class="text-[#717182]">允许 RunnerType</span>
          <input v-model="runnerTypesText" placeholder="DEFAULT,PYTEST_ALLURE" class="h-8 rounded-[8px] border border-black/10 px-2" />
        </label>
        <label class="grid gap-1 text-[12px]">
          <span class="text-[#717182]">允许 TestCaseId</span>
          <input v-model="testcaseIdsText" placeholder="uuid1,uuid2" class="h-8 rounded-[8px] border border-black/10 px-2" />
        </label>
        <label class="grid gap-1 text-[12px]">
          <span class="text-[#717182]">最大用例数</span>
          <input v-model="maxCountText" type="number" min="1" class="h-8 rounded-[8px] border border-black/10 px-2" />
        </label>
        <label class="grid gap-1 text-[12px]">
          <span class="text-[#717182]">过期时间</span>
          <input v-model="expiresAtText" type="datetime-local" class="h-8 rounded-[8px] border border-black/10 px-2" />
        </label>
      </div>

      <div class="mt-3 grid gap-3 md:grid-cols-[1fr_auto_auto_auto]">
        <input v-model="reasonText" placeholder="吊销/泄露原因，可选" class="h-8 rounded-[8px] border border-black/10 px-2 text-[12px]" />
        <button class="h-8 rounded-[8px] bg-[#155DFC] px-3 text-[12px] text-white" @click="savePolicy">保存策略</button>
        <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px]" @click="revoke">吊销 Token</button>
        <button class="h-8 rounded-[8px] border border-red-200 bg-red-50 px-3 text-[12px] text-red-700" @click="reportLeak">上报泄露</button>
      </div>

      <div class="mt-3 grid gap-3 md:grid-cols-[1fr_auto_auto]">
        <input v-model="namedTokenName" placeholder="专用 Token 名称，如 jenkins-main / github-actions" class="h-8 rounded-[8px] border border-black/10 px-2 text-[12px]" />
        <label class="flex h-8 items-center gap-2 rounded-[8px] border border-black/10 px-3 text-[12px] text-[#474747]">
          <input v-model="namedTokenPrimary" type="checkbox" />
          设为主 Token
        </label>
        <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px]" @click="rotateNamed">创建/轮换专用 Token</button>
      </div>

      <div v-if="loading" class="py-8 text-center text-[12px] text-[#717182]">加载中...</div>

      <div v-else class="mt-5 overflow-hidden rounded-[8px] border border-black/10">
        <div class="grid grid-cols-[1.2fr_0.8fr_1fr_1fr_1.1fr_1.2fr] bg-[#F8FAFC] px-3 py-2 text-[12px] font-medium text-[#474747]">
          <div>Token</div>
          <div>状态</div>
          <div>最近轮换</div>
          <div>最后使用</div>
          <div>到期 / 泄露</div>
          <div>安全诊断</div>
        </div>
        <div v-if="tokenRows.length === 0" class="px-3 py-5 text-center text-[12px] text-[#717182]">暂无命名 Token，当前项目 Token 会在轮换后同步为主 Token</div>
        <div
          v-for="row in tokenRows"
          :key="row.id || row.name"
          class="grid grid-cols-[1.2fr_0.8fr_1fr_1fr_1.1fr_1.2fr] border-t border-black/10 px-3 py-3 text-[12px] text-[#474747]"
          :class="row.primary ? 'bg-[#F0F6FF]' : 'bg-white'"
        >
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="truncate font-medium text-[#0A0A0A]">{{ row.name }}</span>
              <span v-if="row.primary" class="rounded-[999px] bg-[#DBEAFE] px-2 py-0.5 text-[11px] text-[#155DFC]">当前 active</span>
            </div>
            <div class="mt-1 text-[#717182]">{{ row.hint || 'redacted' }}</div>
          </div>
          <div><span class="rounded-[999px] border px-2 py-1" :class="stateTagClass(row.state)">{{ stateLabel(row.state) }}</span></div>
          <div>{{ formatTime(row.rotatedAt) }}<div class="mt-1 text-[#717182]">{{ row.rotatedBy || '-' }}</div></div>
          <div>{{ formatTime(row.lastUsedAt) }}</div>
          <div>
            <div>{{ formatTime(row.expiresAt) }}</div>
            <div class="mt-1" :class="rowHintClass(row)">{{ rowHint(row) }}</div>
          </div>
          <div>
            <div>Runner: {{ row.policy.allowedRunnerTypes.join(', ') || '不限' }}</div>
            <div class="mt-1">Case: {{ row.policy.allowedTestCaseIds.length }} / Max: {{ row.policy.maxTestCaseCount ?? '不限' }}</div>
          </div>
        </div>
      </div>

      <div v-if="token" class="mt-4 rounded-[8px] border border-[#16A34A]/30 bg-[#F0FDF4] px-3 py-2 text-[12px] text-[#166534]">
        新 Token 仅本次显示：{{ token }}
      </div>
      <div v-if="feedback" class="mt-3 rounded-[8px] bg-blue-50 px-3 py-2 text-[12px] text-blue-700">{{ feedback }}</div>
      <div v-if="error" class="mt-3 rounded-[8px] bg-red-50 px-3 py-2 text-[12px] text-red-700">{{ error }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  getCiTokenStatus,
  getCiTokens,
  reportCiTokenLeak,
  revokeCiToken,
  rotateCiToken,
  rotateNamedCiToken,
  updateCiTokenPolicy,
  type CiTokenPolicy,
  type CiTokenRecord,
  type CiTokenStatus,
} from '@/lib/api/ciTokenGovernance'

type Diagnostic = { label: string; text: string; level: 'ok' | 'warning' | 'danger' }

const route = useRoute()
const projectId = route.params.projectId as string

const loading = ref(false)
const status = ref<CiTokenStatus | null>(null)
const tokens = ref<CiTokenRecord[]>([])
const token = ref('')
const feedback = ref('')
const error = ref('')

const runnerTypesText = ref('')
const testcaseIdsText = ref('')
const maxCountText = ref('')
const expiresAtText = ref('')
const reasonText = ref('')
const namedTokenName = ref('jenkins-main')
const namedTokenPrimary = ref(false)

const policy = computed<CiTokenPolicy>(() => ({
  allowedRunnerTypes: runnerTypesText.value.split(',').map((v) => v.trim()).filter(Boolean),
  allowedTestCaseIds: testcaseIdsText.value.split(',').map((v) => v.trim()).filter(Boolean),
  maxTestCaseCount: maxCountText.value ? Number(maxCountText.value) : null,
}))

const statusState = computed(() => status.value?.state || (status.value?.enabled ? 'active' : 'disabled'))

const tokenRows = computed<CiTokenRecord[]>(() => {
  if (tokens.value.length > 0) return tokens.value
  if (!status.value) return []
  return [{
    ...status.value,
    id: 'project-current',
    name: 'project-current',
    primary: status.value.enabled || status.value.state === 'active',
  }]
})

const aggregate = computed(() => {
  const rows = tokenRows.value
  const active = rows.filter((row) => row.state === 'active').length
  const risky = rows.filter((row) => ['expired', 'revoked', 'leaked'].includes(row.state) || ['warning', 'critical', 'expired'].includes(expiryReminderState(row))).length
  return { total: rows.length, active, risky }
})

const expirySummary = computed(() => {
  const state = status.value ? expiryReminderState(status.value) : 'none'
  if (state === 'critical') return '即将过期'
  if (state === 'warning') return '需要排期轮换'
  if (state === 'expired' || statusState.value === 'expired') return '已过期'
  if (status.value?.expiresAt) return '有效期正常'
  return '未设置过期'
})

const leakSummary = computed(() => {
  if (statusState.value === 'leaked') return '已上报泄露'
  if (status.value && leakAttentionState(status.value) === 'fresh') return '待完成轮换'
  if (status.value && leakAttentionState(status.value) === 'stale') return '泄露处置超时'
  return '未见泄露'
})

const expiryTextClass = computed(() => {
  const state = status.value ? expiryReminderState(status.value) : 'none'
  return state === 'critical' || state === 'expired' || statusState.value === 'expired' ? 'text-[#B91C1C]' : state === 'warning' ? 'text-[#B45309]' : 'text-[#15803D]'
})
const leakTextClass = computed(() => statusState.value === 'leaked' || (status.value && leakAttentionState(status.value) === 'stale') ? 'text-[#B91C1C]' : 'text-[#15803D]')

const diagnostics = computed<Diagnostic[]>(() => {
  const rows: Diagnostic[] = []
  if (!status.value) return rows
  rows.push({ label: '密钥值', text: '仅保存 hash 与 hint，列表不会回显明文 Token', level: 'ok' })
  const expiryState = expiryReminderState(status.value)
  if (expiryState === 'critical' || expiryState === 'warning') {
    rows.push({ label: '到期提醒', text: `${expirySummary.value}，建议先轮换再吊销旧凭据`, level: expiryState === 'critical' ? 'danger' : 'warning' })
  }
  if (status.value.state === 'leaked') {
    rows.push({ label: '泄露响应', text: `泄露原因已记录：${status.value.leakReportReason || '未填写'}`, level: 'danger' })
  }
  if (status.value.state === 'revoked') {
    rows.push({ label: '吊销记录', text: `吊销原因：${status.value.revokedReason || '未填写'}`, level: 'warning' })
  }
  return rows
})

function stateLabel(state: string | undefined) {
  const map: Record<string, string> = {
    active: '已启用',
    disabled: '未启用',
    expired: '已过期',
    revoked: '已吊销',
    leaked: '已泄露',
  }
  return map[state || ''] || state || '-'
}

function stateTagClass(state: string | undefined) {
  if (state === 'active') return 'border-[#16A34A]/30 bg-[#F0FDF4] text-[#166534]'
  if (state === 'leaked' || state === 'expired') return 'border-[#EF4444]/30 bg-[#FEF2F2] text-[#B91C1C]'
  if (state === 'revoked') return 'border-[#F59E0B]/30 bg-[#FFFBEB] text-[#92400E]'
  return 'border-black/10 bg-white text-[#717182]'
}

function diagnosticClass(level: Diagnostic['level']) {
  if (level === 'danger') return 'border-[#EF4444]/30 bg-[#FEF2F2] text-[#B91C1C]'
  if (level === 'warning') return 'border-[#F59E0B]/30 bg-[#FFFBEB] text-[#92400E]'
  return 'border-[#16A34A]/30 bg-[#F0FDF4] text-[#166534]'
}

function rowHint(row: CiTokenStatus) {
  if (row.state === 'leaked') return `泄露：${row.leakReportReason || '原因未填写'}`
  if (row.state === 'revoked') return `吊销：${row.revokedReason || '原因未填写'}`
  if (row.state === 'expired') return '已过期，需轮换'
  const state = expiryReminderState(row)
  if (state === 'critical') return '临近过期'
  if (state === 'warning') return '轮换提醒'
  return '生命周期正常'
}

function rowHintClass(row: CiTokenStatus) {
  const state = expiryReminderState(row)
  if (row.state === 'leaked' || row.state === 'expired' || state === 'critical') return 'text-[#B91C1C]'
  if (row.state === 'revoked' || state === 'warning') return 'text-[#B45309]'
  return 'text-[#15803D]'
}

function expiryReminderState(row: CiTokenStatus) {
  if (!row.expiresAt) return 'none'
  const now = Date.now()
  const expiresMs = row.expiresAt * 1000
  const dayMs = 24 * 60 * 60 * 1000
  if (expiresMs <= now || row.state === 'expired') return 'expired'
  if (expiresMs <= now + 3 * dayMs) return 'critical'
  if (expiresMs <= now + 14 * dayMs) return 'warning'
  return 'ok'
}

function leakAttentionState(row: CiTokenStatus) {
  if (!row.leakReportedAt) return 'none'
  const ageHours = (Date.now() - row.leakReportedAt * 1000) / (60 * 60 * 1000)
  return ageHours <= 24 ? 'fresh' : 'stale'
}

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
    const [statusData, listData] = await Promise.all([getCiTokenStatus(projectId), getCiTokens(projectId).catch(() => ({ projectId, tokens: [] }))])
    status.value = statusData
    tokens.value = listData.tokens
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
    await reload()
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
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '轮换失败'
  }
}

async function rotateNamed() {
  feedback.value = ''
  error.value = ''
  try {
    const name = namedTokenName.value.trim()
    if (!name) throw new Error('请填写专用 Token 名称')
    const res = await rotateNamedCiToken(projectId, name, namedTokenPrimary.value, policy.value, parseInputTime(expiresAtText.value))
    token.value = res.token
    feedback.value = `专用 Token ${res.name} 已轮换，仅本次显示明文`
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '专用 Token 轮换失败'
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
    await reload()
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
    await reload()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '上报失败'
  }
}

onMounted(reload)
</script>
