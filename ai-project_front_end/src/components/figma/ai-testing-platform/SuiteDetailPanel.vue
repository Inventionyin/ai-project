<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import suiteDetailBack from '@/assets/figma/ai-testing-platform/suite-detail-back.svg'
import suiteDetailRun from '@/assets/figma/ai-testing-platform/suite-detail-run.svg'
import suiteDetailSave from '@/assets/figma/ai-testing-platform/suite-detail-save.svg'
import SuiteCasePool from '@/components/figma/ai-testing-platform/SuiteCasePool.vue'
import SuiteCaseTable from '@/components/figma/ai-testing-platform/SuiteCaseTable.vue'

const router = useRouter()
const route = useRoute()

type ApiResponse<T> = {
  code?: number
  message?: string
  data?: T
}

type SuitePublic = {
  id: string
  name: string
}

type SuiteItemPublic = {
  testcaseTitle: string
  testcaseType: string
  testcasePriority: string
}

const projectId = computed(() => (typeof route.params.projectId === 'string' && route.params.projectId.length > 0 ? route.params.projectId : '1'))
const suiteId = computed(() => (typeof route.params.id === 'string' ? route.params.id.trim() : ''))
const suiteName = ref('套件编排')
const isLoadingSuiteItems = ref(false)

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

function showToast(message: string) {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, type: 'success' } }))
}

function goBack() {
  router.push(`/projects/${projectId.value}/assets/suites`)
}

function runSuite() {
  showToast('运行已触发')
}

function saveSuite() {
  showToast('套件已保存')
}

type PoolCase = { title: string; typeLabel: string; priority: string }
type SuiteCaseRow = { title: string; typeLabel: string; priority: string }

const poolCases = ref<PoolCase[]>([
  { title: '取消订单-超时自动取消', typeLabel: 'API', priority: 'P1' },
  { title: '用户登录-手机号验证码', typeLabel: 'API', priority: 'P0' },
  { title: '商品库存扣减-并发场景', typeLabel: 'API', priority: 'P0' },
  { title: '支付宝退款-全额退款', typeLabel: 'API', priority: 'P1' }
])

const suiteRows = ref<SuiteCaseRow[]>([])

const selectedPoolIndex = ref<number | null>(null)

const mapItemToRow = (item: SuiteItemPublic): SuiteCaseRow => {
  return {
    title: item.testcaseTitle,
    typeLabel: item.testcaseType,
    priority: item.testcasePriority
  }
}

const loadSuiteItems = async () => {
  if (!suiteId.value) return
  isLoadingSuiteItems.value = true
  try {
    const authorization = resolveAuthHeader()
    const [itemsResponse, suiteResponse] = await Promise.all([
      fetch(`${resolveApiBaseUrl()}/api/suites/${suiteId.value}/items`, {
        method: 'GET',
        headers: {
          Authorization: authorization
        }
      }),
      fetch(`${resolveApiBaseUrl()}/api/suites/${suiteId.value}`, {
        method: 'GET',
        headers: {
          Authorization: authorization
        }
      })
    ])
    const itemsPayload = await itemsResponse.json() as ApiResponse<SuiteItemPublic[]>
    if (!itemsResponse.ok || itemsPayload.code !== 0 || !itemsPayload.data) {
      throw new Error(itemsPayload.message || '获取套件编排项失败，请稍后重试')
    }
    suiteRows.value = itemsPayload.data.map(mapItemToRow)

    const suitePayload = await suiteResponse.json() as ApiResponse<SuitePublic>
    if (suiteResponse.ok && suitePayload.code === 0 && suitePayload.data?.name) {
      suiteName.value = suitePayload.data.name
    } else {
      suiteName.value = '未知套件'
    }
  } catch (error) {
    suiteRows.value = []
    suiteName.value = '未知套件'
    const errorMessage = error instanceof Error ? error.message : '获取套件编排项失败，请稍后重试'
    window.alert(errorMessage)
  } finally {
    isLoadingSuiteItems.value = false
  }
}

function selectPoolCase(index: number) {
  selectedPoolIndex.value = index
}

function addPoolCase(index: number) {
  if (index < 0 || index >= poolCases.value.length) return
  const item = poolCases.value.splice(index, 1)[0]
  suiteRows.value.push({ ...item })
  selectedPoolIndex.value = null
  showToast('已添加到套件')
}

function removeSuiteRow(index: number) {
  if (index < 0 || index >= suiteRows.value.length) return
  const item = suiteRows.value.splice(index, 1)[0]
  poolCases.value.unshift({ ...item })
  showToast('已移回用例池')
}

function moveSuiteRow(payload: { from: number; to: number }) {
  const { from, to } = payload
  if (from === to) return
  if (from < 0 || from >= suiteRows.value.length) return
  if (to < 0 || to >= suiteRows.value.length) return
  const [row] = suiteRows.value.splice(from, 1)
  suiteRows.value.splice(to, 0, row)
}

onMounted(() => {
  void loadSuiteItems()
})

watch(
  () => route.params.id,
  () => {
    void loadSuiteItems()
  }
)
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)] md:pr-[16.67px]">
    <div class="flex h-[62.67px] w-full items-center justify-between border-b-[0.6667px] border-black/10 bg-white px-[16px] md:px-[24px]">
      <div class="flex items-center gap-[12px]">
        <button type="button" class="h-[18px] w-[18px]" aria-label="Back" @click="goBack">
          <img :src="suiteDetailBack" alt="" class="h-[18px] w-[18px]" />
        </button>

        <div class="flex flex-col gap-[2px]">
          <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">套件编排：{{ suiteName }}</div>
          <div class="text-[12px] leading-[16px] text-[#717182]">{{ isLoadingSuiteItems ? '加载中...' : `${suiteRows.length} 个用例` }}</div>
        </div>
      </div>

      <div class="flex items-center gap-[8px]">
        <button
          type="button"
          class="relative h-[32px] w-[72.33px] rounded-[10px] border-[0.6667px] border-black/10 bg-transparent"
          @click="runSuite"
        >
          <img :src="suiteDetailRun" alt="" class="absolute left-[12.67px] top-[9.5px] h-[13px] w-[13px]" />
          <span class="absolute left-[29.67px] top-[6.33px] text-[14px] font-medium leading-[20px] text-[#717182]"> 运行</span>
        </button>

        <button type="button" class="relative h-[32px] w-[71px] rounded-[10px] bg-[#155DFC]" @click="saveSuite">
          <img :src="suiteDetailSave" alt="" class="absolute left-[12px] top-[9.5px] h-[13px] w-[13px]" />
          <span class="absolute left-[31px] top-[6.33px] text-[14px] font-medium leading-[20px] text-white">保存</span>
        </button>
      </div>
    </div>

    <div class="flex w-full flex-col md:flex-row md:h-[426.67px]">
      <SuiteCasePool
        class="md:h-[426.67px]"
        :cases="poolCases"
        :selected-index="selectedPoolIndex"
        @select="selectPoolCase"
        @add="addPoolCase"
      />
      <SuiteCaseTable class="md:h-[426.67px]" :rows="suiteRows" @remove="removeSuiteRow" @move="moveSuiteRow" />
    </div>
  </div>
</template>
