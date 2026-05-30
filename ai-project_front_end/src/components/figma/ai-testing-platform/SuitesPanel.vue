<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import headerPlus from '@/assets/figma/ai-testing-platform/header-plus.svg'
import filterSearch from '@/assets/figma/ai-testing-platform/filter-search.svg'
import SuiteCard, { type SuiteCardData } from '@/components/figma/ai-testing-platform/SuiteCard.vue'
import CreateSuiteModal from '@/components/figma/ai-testing-platform/CreateSuiteModal.vue'
import { createSuiteRun } from '@/lib/aiTestingPlatformApi'

type ApiResponse<T> = {
  code?: number
  message?: string
  data?: T
}

type PageData<T> = {
  page: number
  pageSize: number
  total: number
  items: T[]
}

type SuitePublic = {
  id: string
  name: string
  defaultEnvId?: string | null
  config: {
    timeoutSec: number
    concurrency: number
    retryCount: number
  }
  updatedAt: number
}

type EnvironmentPublic = {
  id: string
  name: string
}

const isCreateSuiteOpen = ref(false)
const router = useRouter()
const route = useRoute()
const suites = ref<SuiteCardData[]>([])
const totalSuites = ref(0)
const isLoadingSuites = ref(false)
const environments = ref<EnvironmentPublic[]>([])
const errorMessage = ref('')

const projectId = computed(() => String(route.params.projectId || '').trim())
const hasProjectId = computed(() => Boolean(projectId.value))

const resolveApiBaseUrl = () => {
  const envBase = String(import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!envBase) return ''
  return envBase.endsWith('/') ? envBase.slice(0, -1) : envBase
}

const resolveAuthHeader = () => {
  const accessToken = localStorage.getItem('accessToken')
  if (!accessToken) {
    throw new Error('登录状态已失效，请重新登录')
  }
  return `Bearer ${accessToken}`
}

const toNameMap = <T extends { id: string; name: string }>(items: T[]) => {
  return items.reduce<Record<string, string>>((acc, item) => {
    acc[item.id] = item.name
    return acc
  }, {})
}

const toUserFacingError = (error: unknown, fallback: string) => {
  if (!(error instanceof Error)) return fallback
  const message = String(error.message || '').trim()
  if (!message || message === 'Failed to fetch') return fallback
  return message
}

const formatDateTime = (timestamp?: number | null) => {
  if (!timestamp) return '-'
  const value = new Date(timestamp * 1000)
  if (Number.isNaN(value.getTime())) return '-'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(value)
}

const mapSuiteToCard = (suite: SuitePublic, environmentNameMap: Record<string, string>): SuiteCardData => {
  return {
    id: suite.id,
    title: suite.name,
    owner: '系统',
    status: 'pass',
    caseCount: '-',
    concurrency: `${suite.config.concurrency}`,
    timeout: `${suite.config.timeoutSec}s`,
    retry: `${suite.config.retryCount}次`,
    environment: suite.defaultEnvId ? (environmentNameMap[suite.defaultEnvId] || '-') : '-',
    defaultEnvId: suite.defaultEnvId || null,
    lastRunAt: formatDateTime(suite.updatedAt),
    metaRowHeight: 16
  }
}

const loadEnvironmentNameMap = async (authorization: string) => {
  if (!projectId.value) {
    environments.value = []
    return {}
  }
  const response = await fetch(`${resolveApiBaseUrl()}/api/projects/${encodeURIComponent(projectId.value)}/environments`, {
    method: 'GET',
    headers: {
      Authorization: authorization
    }
  })
  const payload = await response.json() as ApiResponse<EnvironmentPublic[]>
  if (!response.ok || payload.code !== 0 || !payload.data) {
    environments.value = []
    return {}
  }
  environments.value = payload.data
  return toNameMap(payload.data)
}

const loadSuites = async () => {
  if (!projectId.value) {
    suites.value = []
    totalSuites.value = 0
    errorMessage.value = ''
    return
  }
  isLoadingSuites.value = true
  errorMessage.value = ''
  try {
    const authorization = resolveAuthHeader()
    const query = new URLSearchParams({
      projectId: projectId.value,
      page: '1',
      pageSize: '200'
    })
    const response = await fetch(`${resolveApiBaseUrl()}/api/suites?${query.toString()}`, {
      method: 'GET',
      headers: {
        Authorization: authorization
      }
    })
    const payload = await response.json() as ApiResponse<PageData<SuitePublic>>
    if (!response.ok || payload.code !== 0 || !payload.data) {
      throw new Error(payload.message || '获取测试套件失败，请稍后重试')
    }
    const environmentNameMap = await loadEnvironmentNameMap(authorization)
    totalSuites.value = payload.data.total
    suites.value = payload.data.items.map((suite) => mapSuiteToCard(suite, environmentNameMap))
  } catch (error) {
    suites.value = []
    totalSuites.value = 0
    errorMessage.value = toUserFacingError(error, '获取测试套件失败，请检查网络后重试')
  } finally {
    isLoadingSuites.value = false
  }
}

function openCreateSuite() {
  if (!hasProjectId.value) {
    showToast('项目ID缺失，请先选择项目', 'error')
    return
  }
  isCreateSuiteOpen.value = true
}

function closeCreateSuite() {
  isCreateSuiteOpen.value = false
}

async function handleCreateSuite(data: {
  name: string
  description: string
  defaultEnvironment: string
  timeoutSeconds: number
  concurrency: number
  retryCount: number
}) {
  try {
    if (!projectId.value) {
      throw new Error('项目ID缺失，无法创建套件')
    }
    if (!data.name.trim()) {
      throw new Error('请输入套件名称')
    }
    const authorization = resolveAuthHeader()
    const response = await fetch(`${resolveApiBaseUrl()}/api/suites`, {
      method: 'POST',
      headers: {
        Authorization: authorization,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        projectId: projectId.value,
        name: data.name.trim(),
        defaultEnvId: data.defaultEnvironment || null,
        config: {
          timeoutSec: Number(data.timeoutSeconds),
          concurrency: Number(data.concurrency),
          retryCount: Number(data.retryCount)
        }
      })
    })
    const payload = await response.json() as ApiResponse<SuitePublic>
    if (!response.ok || payload.code !== 0) {
      throw new Error(payload.message || '新建测试套件失败，请稍后重试')
    }
    closeCreateSuite()
    await loadSuites()
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '新建测试套件失败，请稍后重试'
    showToast(errorMessage, 'error')
  }
}

function showToast(message: string, type: 'success' | 'error' = 'success') {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, type } }))
}

function deleteSuite(index: number) {
  suites.value.splice(index, 1)
  showToast('套件已删除')
}

async function runSuite(suite: SuiteCardData) {
  if (!hasProjectId.value) {
    showToast('项目ID缺失，无法运行套件', 'error')
    return
  }
  const pid = projectId.value
  if (!suite.defaultEnvId) {
    showToast('套件未配置默认环境，无法运行', 'error')
    return
  }
  try {
    const run = await createSuiteRun({
      projectId: pid,
      suiteId: suite.id,
      envId: suite.defaultEnvId,
      triggerType: 'MANUAL',
      meta: { source: 'suite_card' }
    })
    const rid = String(run?.id || '').trim()
    if (!rid) throw new Error('运行创建成功但未返回 runId')
    showToast(`运行已触发：${rid}`)
    await router.push(`/projects/${encodeURIComponent(pid)}/runs/${encodeURIComponent(rid)}`)
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '运行触发失败，请稍后重试'
    showToast(errorMessage, 'error')
  }
}

function arrangeSuite(suiteId: string) {
  if (!hasProjectId.value) {
    showToast('项目ID缺失，无法进入套件编排', 'error')
    return
  }
  router.push(`/projects/${encodeURIComponent(projectId.value)}/assets/suites/${encodeURIComponent(suiteId)}`)
}

onMounted(() => {
  void loadSuites()
})
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)] md:pr-[16.67px]">
    <div class="flex flex-col gap-[16px] px-[16px] pt-[16px] md:px-[24px] md:pt-[24px]">
      <div class="flex items-center justify-between gap-[16px]">
        <div class="flex flex-col gap-[2px]">
          <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">测试套件</div>
          <div class="text-[14px] leading-[20px] text-[#717182]">{{ isLoadingSuites ? '加载中...' : `共 ${totalSuites} 个套件` }}</div>
        </div>

        <button
          type="button"
          class="relative h-[32px] w-[100px] rounded-[10px] bg-[#155DFC] disabled:cursor-not-allowed disabled:bg-[#8EA9FF]"
          :disabled="!hasProjectId"
          @click="openCreateSuite"
        >
          <img :src="headerPlus" alt="" class="absolute left-[12px] top-[9px] h-[14px] w-[14px]" />
          <span class="absolute left-[32px] top-[6.33px] text-[14px] font-medium leading-[20px] text-white">
            新建套件
          </span>
        </button>
      </div>

      <div
        v-if="errorMessage"
        class="flex items-center justify-between gap-[12px] rounded-[10px] border border-[#FCA5A5] bg-[#FEF2F2] px-[12px] py-[10px] text-[13px] text-[#991B1B]"
      >
        <span>{{ errorMessage }}</span>
        <button type="button" class="shrink-0 text-[12px] font-medium text-[#B91C1C]" @click="loadSuites">重试</button>
      </div>

      <div class="relative h-[32px] w-full">
        <div class="relative h-full w-full rounded-[10px] bg-[#ECECF0]">
          <img :src="filterSearch" alt="" class="absolute left-[12px] top-[9px] h-[14px] w-[14px]" />
          <div class="absolute left-[32px] top-1/2 -translate-y-1/2 text-[14px] leading-[20px] text-[#0A0A0A]">
            搜索套件标题...
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-[16px] lg:grid-cols-3 lg:justify-items-start">
        <SuiteCard
          v-for="(suite, index) in suites"
          :key="suite.id"
          :suite="suite"
          @delete="deleteSuite(index)"
          @run="runSuite(suite)"
          @arrange="arrangeSuite(suite.id)"
        />
      </div>
    </div>
  </div>

  <CreateSuiteModal
    :is-open="isCreateSuiteOpen"
    :environments="environments"
    @close="closeCreateSuite"
    @create="handleCreateSuite"
  />
</template>
