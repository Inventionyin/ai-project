<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import suiteDetailBack from '@/assets/figma/ai-testing-platform/suite-detail-back.svg'
import suiteDetailRun from '@/assets/figma/ai-testing-platform/suite-detail-run.svg'
import suiteDetailSave from '@/assets/figma/ai-testing-platform/suite-detail-save.svg'
import SuiteCasePool from '@/components/figma/ai-testing-platform/SuiteCasePool.vue'
import SuiteCaseTable from '@/components/figma/ai-testing-platform/SuiteCaseTable.vue'
import { createSuiteRun, fetchProjectTestcasesLite, fetchSuiteDetail, fetchSuiteItems, upsertSuiteItems, type ProjectTestcaseLite, type SuiteItem } from '@/lib/aiTestingPlatformApi'

const router = useRouter()
const route = useRoute()

const projectId = computed(() => (typeof route.params.projectId === 'string' && route.params.projectId.length > 0 ? route.params.projectId : '1'))
const suiteId = computed(() => (typeof route.params.id === 'string' ? route.params.id.trim() : ''))
const suiteName = ref('套件编排')
const suiteDefaultEnvId = ref('')
const isLoadingSuiteItems = ref(false)
const isSaving = ref(false)
const isRunning = ref(false)

function showToast(message: string, type: 'success' | 'error' = 'success') {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, type } }))
}

function goBack() {
  router.push(`/projects/${encodeURIComponent(projectId.value)}/assets/suites`)
}

type PoolCase = { testcaseId: string; title: string; typeLabel: string; priority: string }
type SuiteCaseRow = { testcaseId: string; title: string; typeLabel: string; priority: string; params: Record<string, unknown> }

const poolCases = ref<PoolCase[]>([])
const suiteRows = ref<SuiteCaseRow[]>([])

const selectedPoolIndex = ref<number | null>(null)

const normalizeText = (value: unknown, fallback = '-') => {
  const text = String(value ?? '').trim()
  return text || fallback
}

const mapProjectTestcaseToPoolCase = (item: ProjectTestcaseLite): PoolCase | null => {
  const testcaseId = String(item?.id || '').trim()
  if (!testcaseId) return null
  return {
    testcaseId,
    title: normalizeText(item?.title ?? item?.name, testcaseId),
    typeLabel: normalizeText(item?.type, 'API'),
    priority: normalizeText(item?.priority, 'P2')
  }
}

const mapItemToRow = (item: SuiteItem): SuiteCaseRow | null => {
  const testcaseId = String(item.testcaseId || '').trim()
  if (!testcaseId) return null
  return {
    testcaseId,
    title: normalizeText(item.testcaseTitle, testcaseId),
    typeLabel: normalizeText(item.testcaseType, 'API'),
    priority: normalizeText(item.testcasePriority, 'P2'),
    params: item.params && typeof item.params === 'object' ? item.params : {}
  }
}

const loadProjectTestcases = async () => {
  const pid = String(projectId.value || '').trim()
  if (!pid) return []
  const pageSize = 200
  const first = await fetchProjectTestcasesLite(pid, 1, pageSize)
  const items = Array.isArray(first.items) ? [...first.items] : []
  const total = Number(first.total || 0)
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  if (totalPages > 1) {
    const pages = await Promise.all(
      Array.from({ length: totalPages - 1 }, (_, idx) => fetchProjectTestcasesLite(pid, idx + 2, pageSize))
    )
    for (const page of pages) {
      if (Array.isArray(page.items)) items.push(...page.items)
    }
  }
  return items
}

const recomputePoolCases = (allCases: ProjectTestcaseLite[], rows: SuiteCaseRow[]) => {
  const used = new Set(rows.map((item) => item.testcaseId))
  const seen = new Set<string>()
  poolCases.value = allCases
    .map(mapProjectTestcaseToPoolCase)
    .filter((item): item is PoolCase => Boolean(item))
    .filter((item) => {
      if (seen.has(item.testcaseId)) return false
      seen.add(item.testcaseId)
      return true
    })
    .filter((item) => !used.has(item.testcaseId))
}

const loadSuiteItems = async () => {
  if (!suiteId.value) return
  isLoadingSuiteItems.value = true
  try {
    const [suiteItemsData, suiteData, testcaseData] = await Promise.all([
      fetchSuiteItems(suiteId.value),
      fetchSuiteDetail(suiteId.value),
      loadProjectTestcases()
    ])

    const rows = suiteItemsData.map((item) => mapItemToRow(item)).filter((item): item is SuiteCaseRow => Boolean(item))
    suiteRows.value = rows
    suiteName.value = suiteData?.name || '未知套件'
    suiteDefaultEnvId.value = String(suiteData?.defaultEnvId || '').trim()
    recomputePoolCases(testcaseData, rows)
  } catch (error) {
    suiteRows.value = []
    poolCases.value = []
    suiteName.value = '未知套件'
    suiteDefaultEnvId.value = ''
    const errorMessage = error instanceof Error ? error.message : '获取套件编排数据失败，请稍后重试'
    showToast(errorMessage, 'error')
  } finally {
    isLoadingSuiteItems.value = false
  }
}

const canRun = computed(() => !isLoadingSuiteItems.value && !isRunning.value && !isSaving.value && !!suiteId.value && !!suiteDefaultEnvId.value)
const canSave = computed(() => !isLoadingSuiteItems.value && !isRunning.value && !isSaving.value && !!suiteId.value && suiteRows.value.length > 0)

async function saveSuite() {
  if (!canSave.value) return
  isSaving.value = true
  try {
    const items: SuiteItem[] = suiteRows.value.map((row, index) => ({
      testcaseId: row.testcaseId,
      orderNo: index + 1,
      params: row.params || {}
    }))
    await upsertSuiteItems(suiteId.value, items)
    showToast('套件已保存')
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '保存失败，请稍后重试'
    showToast(errorMessage, 'error')
  } finally {
    isSaving.value = false
  }
}

async function runSuite() {
  if (!suiteId.value) return
  const envId = String(suiteDefaultEnvId.value || '').trim()
  if (!envId) {
    showToast('套件未配置默认环境，无法运行', 'error')
    return
  }
  isRunning.value = true
  try {
    const run = await createSuiteRun({
      projectId: projectId.value,
      suiteId: suiteId.value,
      envId,
      triggerType: 'MANUAL',
      meta: { source: 'suite-detail-panel' }
    })
    const rid = String(run?.id || '').trim()
    if (!rid) throw new Error('运行创建成功但未返回 runId')
    showToast(`运行已触发：${rid}`)
    await router.push(`/projects/${encodeURIComponent(projectId.value)}/runs/${encodeURIComponent(rid)}`)
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '运行触发失败，请稍后重试'
    showToast(errorMessage, 'error')
  } finally {
    isRunning.value = false
  }
}

function selectPoolCase(index: number) {
  selectedPoolIndex.value = index
}

function addPoolCase(index: number) {
  if (index < 0 || index >= poolCases.value.length) return
  const item = poolCases.value.splice(index, 1)[0]
  suiteRows.value.push({ ...item, params: {} })
  selectedPoolIndex.value = null
  showToast('已添加到套件')
}

function removeSuiteRow(index: number) {
  if (index < 0 || index >= suiteRows.value.length) return
  const item = suiteRows.value.splice(index, 1)[0]
  if (poolCases.value.some((row) => row.testcaseId === item.testcaseId)) {
    showToast('已移回用例池')
    return
  }
  poolCases.value.unshift({
    testcaseId: item.testcaseId,
    title: item.title,
    typeLabel: item.typeLabel,
    priority: item.priority
  })
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
  () => [route.params.projectId, route.params.id],
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
          class="relative h-[32px] w-[72.33px] rounded-[10px] border-[0.6667px] border-black/10 bg-transparent disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="!canRun"
          @click="runSuite"
        >
          <img :src="suiteDetailRun" alt="" class="absolute left-[12.67px] top-[9.5px] h-[13px] w-[13px]" />
          <span class="absolute left-[29.67px] top-[6.33px] text-[14px] font-medium leading-[20px] text-[#717182]">
            {{ isRunning ? '运行中' : '运行' }}
          </span>
        </button>

        <button
          type="button"
          class="relative h-[32px] w-[71px] rounded-[10px] bg-[#155DFC] disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="!canSave"
          @click="saveSuite"
        >
          <img :src="suiteDetailSave" alt="" class="absolute left-[12px] top-[9.5px] h-[13px] w-[13px]" />
          <span class="absolute left-[31px] top-[6.33px] text-[14px] font-medium leading-[20px] text-white">
            {{ isSaving ? '保存中' : '保存' }}
          </span>
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
