<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-4 md:p-6">
    <div class="flex flex-col gap-4">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 class="text-[16px] font-semibold leading-6 text-[#0A0A0A]">{{ config.title }}</h1>
          <p class="mt-1 text-[12px] leading-4 text-[#717182]">{{ config.description }}</p>
        </div>
        <button class="h-9 rounded-[8px] border border-black/10 bg-white px-4 text-[13px] text-[#0A0A0A]" @click="load">
          {{ loading ? '刷新中...' : '刷新' }}
        </button>
      </div>

      <div v-if="errorMessage" class="rounded-[8px] border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
        {{ errorMessage }}
      </div>

      <div class="grid grid-cols-1 gap-3 md:grid-cols-4">
        <div v-for="metric in config.metrics(summary)" :key="metric.label" class="rounded-[8px] border border-black/10 bg-white p-4">
          <div class="text-[12px] leading-4 text-[#717182]">{{ metric.label }}</div>
          <div class="mt-2 text-[22px] font-semibold leading-7 text-[#0A0A0A]">{{ metric.value }}</div>
          <div class="mt-1 text-[12px] leading-4" :class="metric.tone || 'text-[#717182]'">{{ metric.note }}</div>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <section class="rounded-[10px] border border-black/10 bg-white p-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div class="text-[14px] font-semibold leading-5 text-[#0A0A0A]">{{ config.workflowTitle }}</div>
              <div class="mt-1 text-[12px] leading-4 text-[#717182]">先选择要处理的类型，再进入对应工作台。</div>
            </div>
            <label class="flex items-center gap-2 text-[12px] leading-4 text-[#717182]">
              {{ config.selectLabel }}
              <select
                v-model="selectedActionTitle"
                :aria-label="config.selectLabel"
                class="h-9 min-w-[180px] rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none focus:border-[#155DFC]"
              >
                <option v-for="action in config.actions(projectId)" :key="action.title" :value="action.title">
                  {{ action.title }}
                </option>
              </select>
            </label>
          </div>

          <div class="mt-4 rounded-[8px] border border-[#155DFC]/30 bg-[#F8FBFF] p-4">
            <div class="text-[13px] font-semibold leading-5 text-[#0A0A0A]">{{ selectedAction.title }}</div>
            <div class="mt-1 text-[12px] leading-5 text-[#374151]">{{ selectedAction.description }}</div>
            <RouterLink
              :to="selectedAction.to"
              class="mt-4 inline-flex h-9 items-center justify-center rounded-[8px] bg-[#155DFC] px-4 text-[13px] font-medium text-white"
            >
              {{ selectedAction.action }}
            </RouterLink>
          </div>

          <div v-if="section === 'assets'" class="mt-4 rounded-[8px] border border-black/10 bg-white p-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div class="text-[13px] font-semibold leading-5 text-[#0A0A0A]">统一资产操作</div>
                <div class="mt-1 text-[12px] leading-4 text-[#717182]">用下拉选择动作，避免把导入、导出、上传、编辑、删除都堆在首屏。</div>
              </div>
              <label class="flex items-center gap-2 text-[12px] leading-4 text-[#717182]">
                选择资产操作
                <select
                  v-model="selectedAssetOperationTitle"
                  aria-label="选择资产操作"
                  class="h-9 min-w-[150px] rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none focus:border-[#155DFC]"
                >
                  <option v-for="operation in assetOperations" :key="operation.title" :value="operation.title">
                    {{ operation.title }}
                  </option>
                </select>
              </label>
            </div>
            <div class="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-[8px] bg-[#F8FAFC] px-3 py-2">
              <div class="text-[12px] leading-5 text-[#374151]">{{ selectedAssetOperation.description }}</div>
              <RouterLink
                :to="selectedAssetOperation.to"
                class="inline-flex h-8 items-center justify-center rounded-[8px] border border-black/10 bg-white px-3 text-[12px] font-medium text-[#155DFC]"
              >
                {{ selectedAssetOperation.action }}
              </RouterLink>
            </div>
          </div>

          <div class="mt-4 flex flex-wrap gap-2">
            <RouterLink
              v-for="action in secondaryActions"
              :key="action.title"
              :to="action.to"
              class="rounded-[8px] border border-black/10 bg-white px-3 py-2 text-[12px] text-[#374151] hover:border-[#155DFC] hover:text-[#155DFC]"
            >
              {{ action.title }}
            </RouterLink>
          </div>
        </section>

        <section class="rounded-[10px] border border-black/10 bg-white p-4">
          <div class="mb-3 text-[14px] font-semibold leading-5 text-[#0A0A0A]">当前判断</div>
          <div class="space-y-2">
            <div v-for="item in config.insights(summary)" :key="item" class="rounded-[8px] bg-[#F8FAFC] px-3 py-2 text-[12px] leading-5 text-[#374151]">
              {{ item }}
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { fetchWorkspaceSummary, type WorkspaceSummary } from '@/lib/api/workspace'

type Metric = {
  label: string
  value: string | number
  note: string
  tone?: string
}

type Action = {
  title: string
  description: string
  action: string
  to: string
}

type AssetOperation = {
  title: string
  description: string
  action: string
  to: string
}

type SectionConfig = {
  title: string
  description: string
  workflowTitle: string
  selectLabel: string
  metrics: (summary: WorkspaceSummary | null) => Metric[]
  actions: (projectId: string) => Action[]
  insights: (summary: WorkspaceSummary | null) => string[]
}

const props = defineProps<{
  section: 'assets' | 'ai' | 'automation' | 'settings'
}>()

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || '').trim())
const loading = ref(false)
const errorMessage = ref('')
const summary = ref<WorkspaceSummary | null>(null)
const selectedActionTitle = ref('')
const selectedAssetOperationTitle = ref('导入')

const zeroSummary: WorkspaceSummary = {
  assets: {
    requirementDocs: 0,
    testcases: 0,
    formalCases: 0,
    testPoints: 0,
    apiCollections: 0,
    apiRequests: 0,
    suites: 0
  },
  automation: {
    runs: 0,
    executedCaseRuns: 0,
    passRate: 0,
    latestRunAt: null
  },
  risks: {
    defects: 0,
    p0Open: 0,
    riskHints: 0
  },
  capabilities: {
    role: 'viewer',
    assets: true,
    ai: false,
    automation: false,
    settings: false,
    ops: false
  }
}

const buildAssetOperations = (pid: string): AssetOperation[] => [
  { title: '导入', description: '按模板导入需求、用例或接口集合，先校验预览再提交。', action: '前往用例管理', to: `/projects/${pid}/assets/testcases` },
  { title: '导出', description: '导出当前筛选结果，用于评审、备份或给上面的人验收。', action: '前往用例管理', to: `/projects/${pid}/assets/testcases` },
  { title: '上传', description: '上传需求文档、用例表格、Swagger/OpenAPI 或补充附件。', action: '前往需求管理', to: `/projects/${pid}/requirements/docs` },
  { title: '编辑', description: '编辑标题、优先级、状态、负责人、模块和说明。', action: '前往用例管理', to: `/projects/${pid}/assets/testcases` },
  { title: '删除', description: '删除前需要确认影响范围，避免误删正式资产。', action: '前往用例管理', to: `/projects/${pid}/assets/testcases` },
  { title: '批量编辑', description: '批量编辑字段、标签、模块和关联关系。', action: '前往用例管理', to: `/projects/${pid}/assets/testcases` }
]

function formatTime(value: number | null) {
  if (!value) return '-'
  return new Date(value * 1000).toLocaleString('zh-CN', { hour12: false })
}

const configs: Record<typeof props.section, SectionConfig> = {
  assets: {
    title: '资产中心',
    description: '统一管理需求、测试用例、接口和回归套件，避免资产入口分散。',
    workflowTitle: '资产工作流',
    selectLabel: '选择资产类型',
    metrics: (source) => {
      const s = source || zeroSummary
      return [
        { label: '需求文档', value: s.assets.requirementDocs, note: '需求管理入口' },
        { label: '测试用例', value: s.assets.testcases, note: `正式用例 ${s.assets.formalCases}` },
        { label: '接口资产', value: s.assets.apiRequests, note: `集合 ${s.assets.apiCollections}` },
        { label: '测试套件', value: s.assets.suites, note: '回归测试集合' }
      ]
    },
    actions: (pid) => [
      { title: '需求管理', description: '导入、解析、版本比对和变更影响分析的源头。', action: '进入需求', to: `/projects/${pid}/requirements/docs` },
      { title: '用例管理', description: '导入、导出、编辑、删除和批量执行测试用例。', action: '进入用例', to: `/projects/${pid}/assets/testcases` },
      { title: '接口管理', description: '维护接口集合、请求、断言和接口自动化资产。', action: '进入接口', to: `/projects/${pid}/assets/apis` },
      { title: '测试套件', description: '把回归用例组合成可重复执行的套件。', action: '进入套件', to: `/projects/${pid}/assets/suites` }
    ],
    insights: (source) => {
      const s = source || zeroSummary
      return [
        `当前资产总量 ${s.assets.testcases} 条，其中正式用例 ${s.assets.formalCases} 条。`,
        `测试点 ${s.assets.testPoints} 条，适合先治理后进入正式验收执行。`,
        `接口请求 ${s.assets.apiRequests} 条，可继续沉淀为接口自动化套件。`
      ]
    }
  },
  ai: {
    title: 'AI能力',
    description: '围绕需求解析、用例生成、用例治理和变更影响分析组织 AI 工作流。',
    workflowTitle: 'AI 辅助流程',
    selectLabel: '选择AI任务',
    metrics: (source) => {
      const s = source || zeroSummary
      return [
        { label: '需求文档', value: s.assets.requirementDocs, note: 'AI 解析输入' },
        { label: '测试点', value: s.assets.testPoints, note: '候选覆盖项' },
        { label: '待治理资产', value: Math.max(0, s.assets.testcases - s.assets.formalCases), note: '需确认转正式' },
        { label: 'P0 风险', value: s.risks.p0Open, note: '生成/治理优先级', tone: s.risks.p0Open > 0 ? 'text-red-700' : 'text-emerald-700' }
      ]
    },
    actions: (pid) => [
      { title: '自动生成测试用例', description: '先检查文档，再生成候选用例，人工确认后入库。', action: '开始生成', to: `/projects/${pid}/ai/generate-cases` },
      { title: '需求解析', description: '提取功能点、业务规则、风险点和测试点。', action: '进入解析', to: `/projects/${pid}/ai/requirements` },
      { title: '用例治理', description: '识别重复、低价值、待转正式和 P0 覆盖不足。', action: '进入治理', to: `/projects/${pid}/ai/case-governance` },
      { title: '变更影响分析', description: '对比需求版本，生成回归建议和影响范围。', action: '查看变更', to: `/projects/${pid}/ai/change-impact` }
    ],
    insights: (source) => {
      const s = source || zeroSummary
      return [
        `AI 不直接改正式资产，先生成建议和草稿，再由人工确认应用。`,
        `当前平台补号/测试点类资产较多，建议先做用例库治理再大规模执行。`,
        `P0 未关闭 ${s.risks.p0Open} 个，AI 生成和治理应优先围绕高风险链路。`
      ]
    }
  },
  automation: {
    title: '自动化执行',
    description: '统一入口管理 UI、接口、性能自动化执行和报告回执。',
    workflowTitle: '执行工作流',
    selectLabel: '选择执行类型',
    metrics: (source) => {
      const s = source || zeroSummary
      return [
        { label: '运行次数', value: s.automation.runs, note: '全部执行记录' },
        { label: '已执行用例', value: s.automation.executedCaseRuns, note: '真实执行回执' },
        { label: '通过率', value: `${s.automation.passRate.toFixed(1)}%`, note: '完成运行统计' },
        { label: '最近执行', value: formatTime(s.automation.latestRunAt), note: '最新回执时间' }
      ]
    },
    actions: (pid) => [
      { title: 'UI自动化', description: '维护浏览器自动化路径、截图、视频和失败定位证据。', action: '查看 UI 报告', to: `/projects/${pid}/automation/ui` },
      { title: '接口自动化', description: '基于接口资产一键调试、执行和沉淀断言。', action: '进入接口执行', to: `/projects/${pid}/automation/api` },
      { title: '性能自动化', description: '维护性能基线、压测报告和趋势对比。', action: '查看性能报告', to: `/projects/${pid}/automation/performance` },
      { title: '运行记录', description: '查看历史运行、失败用例、外部系统回执和 Allure 报告。', action: '进入记录', to: `/projects/${pid}/runs` }
    ],
    insights: (source) => {
      const s = source || zeroSummary
      return [
        `真实执行记录 ${s.automation.executedCaseRuns} 条，验收状态会优先看执行回执。`,
        `接口自动化入口复用接口管理资产，减少 Postman 式调试和自动化之间的割裂。`,
        `性能自动化需要在真实服务器跑基线，趋势稳定后再作为上线门禁。`
      ]
    }
  },
  settings: {
    title: '设置',
    description: '集中管理权限、环境、集成、Token、插件、安全审计和运维健康。',
    workflowTitle: '配置入口',
    selectLabel: '选择配置项',
    metrics: (source) => {
      const s = source || zeroSummary
      return [
        { label: '当前角色', value: s.capabilities.role, note: s.capabilities.settings ? '可管理配置' : '仅查看权限' },
        { label: '外部风险', value: s.risks.riskHints, note: '诊断/告警项' },
        { label: 'P0 未关闭', value: s.risks.p0Open, note: '放行硬门槛', tone: s.risks.p0Open > 0 ? 'text-red-700' : 'text-emerald-700' },
        { label: '缺陷总量', value: s.risks.defects, note: '验收阻塞来源' }
      ]
    },
    actions: (pid) => [
      { title: '权限', description: '区分管理员、编辑者和普通查看者。', action: '进入权限', to: '/settings/rbac' },
      { title: '集成配置', description: '维护 Jira、禅道、Jenkins、钉钉等外部系统。', action: '进入集成', to: `/projects/${pid}/settings/integrations` },
      { title: '环境管理', description: '维护测试环境、变量和默认执行地址。', action: '进入环境', to: `/projects/${pid}/settings/environments` },
      { title: 'API Token / CI Token', description: '管理多 Token、轮换、到期提醒和泄露处置。', action: '进入 Token', to: `/projects/${pid}/settings/ci-token-governance` },
      { title: '运维健康', description: '查看健康聚合、Prometheus/Grafana/SLO 和诊断项。', action: '进入运维', to: `/projects/${pid}/settings/ops-health` }
    ],
    insights: (source) => {
      const s = source || zeroSummary
      return [
        `当前角色为 ${s.capabilities.role}，设置入口按权限收敛，避免普通用户看到过多配置项。`,
        `配置类页面必须保留失败诊断：缺字段、去哪填、下一步跑什么。`,
        `真实外部闭环仍需客户环境授权后复跑，平台内负责记录配置和回执。`
      ]
    }
  }
}

const config = computed(() => configs[props.section])
const actionOptions = computed(() => config.value.actions(projectId.value))
const assetOperations = computed(() => buildAssetOperations(projectId.value))
const selectedAction = computed(() => {
  return actionOptions.value.find((action) => action.title === selectedActionTitle.value) || actionOptions.value[0]
})
const secondaryActions = computed(() => actionOptions.value.filter((action) => action.title !== selectedAction.value.title))
const selectedAssetOperation = computed(() => {
  return assetOperations.value.find((operation) => operation.title === selectedAssetOperationTitle.value) || assetOperations.value[0]
})

watch(
  () => [props.section, projectId.value] as const,
  () => {
    selectedActionTitle.value = actionOptions.value[0]?.title || ''
  },
  { immediate: true }
)

async function load() {
  if (!projectId.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    summary.value = await fetchWorkspaceSummary(projectId.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载工作台摘要失败'
    summary.value = zeroSummary
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
