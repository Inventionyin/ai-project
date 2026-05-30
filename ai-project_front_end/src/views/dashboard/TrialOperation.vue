<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import {
  AlertTriangle,
  BarChart3,
  Bug,
  CheckCircle2,
  Download,
  FileText,
  GitBranch,
  ListFilter,
  RefreshCw,
  Save,
  Settings2,
  ShieldAlert,
  Sparkles,
  TestTube2,
  UploadCloud
} from 'lucide-vue-next'
import {
  applyTrialOperationGovernanceSuggestions,
  generateTrialOperationGovernanceSuggestions,
  getTrialOperationCaseGovernance,
  getTrialOperationDashboard,
  getTrialOperationGovernanceHistory,
  getTrialOperationImportRecords,
  getTrialOperationReport,
  getTrialOperationReportSnapshot,
  getTrialOperationReportSnapshots,
  importTrialOperationDefects,
  importTrialOperationExecutionResults,
  importTrialOperationRequirementDoc,
  importTrialOperationTestcases,
  previewTrialOperationImport,
  recordTrialOperationImport,
  saveTrialOperationReportSnapshot,
  type TrialOperationCaseGovernanceData,
  type TrialOperationDashboardData,
  type TrialOperationAcceptanceSummary,
  type TrialOperationImportPreview,
  type TrialOperationImportRecord,
  type TrialOperationImportResult,
  type TrialOperationReportData,
  type TrialOperationReportSnapshot,
  type TrialOperationGovernanceSuggestionBatch,
  type TrialOperationGovernanceSuggestionItem,
  type TrialOperationGovernanceHistoryData
} from '@/lib/api/trialOperation'

type ChartMode = 'bar' | 'list'
type DimensionKey =
  | 'testcasePriorityDistribution'
  | 'testcaseStatusDistribution'
  | 'testcaseTypeDistribution'
  | 'testcaseFeatureDistribution'
  | 'defectSeverityDistribution'
  | 'defectStatusDistribution'

type ImportType = 'requirements' | 'testcases' | 'defects'
type ImportQueueStatus = 'queued' | 'previewing' | 'ready' | 'importing' | 'success' | 'failed'
type TrialView = 'overview' | 'import' | 'governance' | 'details'

type ImportQueueItem = {
  id: string
  file: File
  label: string
  preview: TrialOperationImportPreview | null
  mapping: Record<string, string>
  status: ImportQueueStatus
  result: TrialOperationImportResult | null
  error: string
}

const route = useRoute()
const isLoading = ref(false)
const errorMessage = ref('')
const dashboard = ref<TrialOperationDashboardData | null>(null)
const caseGovernance = ref<TrialOperationCaseGovernanceData | null>(null)
const chartMode = ref<ChartMode>('bar')
const selectedDimension = ref<DimensionKey>('testcasePriorityDistribution')
const topLimit = ref(10)
const activeView = ref<TrialView>('overview')
const importType = ref<ImportType>('testcases')
const isImporting = ref(false)
const importMessage = ref('')
const importResult = ref<TrialOperationImportResult | null>(null)
const importPreview = ref<TrialOperationImportPreview | null>(null)
const importMapping = ref<Record<string, string>>({})
const isPreviewing = ref(false)
const importQueue = ref<ImportQueueItem[]>([])
const activeImportId = ref('')
const showImportMoreActions = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const directoryInputRef = ref<HTMLInputElement | null>(null)
const importHistory = ref<TrialOperationImportRecord[]>([])
const isLoadingImportHistory = ref(false)
const isGeneratingReport = ref(false)
const reportMarkdown = ref('')
const reportTitle = ref('')
const reportGeneratedAt = ref(0)
const isReportExpanded = ref(false)
const reportMessage = ref('')
const reportSnapshots = ref<TrialOperationReportSnapshot[]>([])
const isSavingSnapshot = ref(false)
const isLoadingSnapshots = ref(false)
const activeSnapshotId = ref('')
const deliveryNoteMessage = ref('')
const governanceBatch = ref<TrialOperationGovernanceSuggestionBatch | null>(null)
const governanceHistory = ref<TrialOperationGovernanceHistoryData | null>(null)
const selectedGovernanceSuggestionIds = ref<string[]>([])
const governanceMessage = ref('')
const isGeneratingGovernanceSuggestions = ref(false)
const isApplyingGovernanceSuggestions = ref(false)
const executionImportLimit = ref(27)
const executionImportMessage = ref('')
const isImportingExecutionResults = ref(false)
let previewChain = Promise.resolve()
let previewBatchToken = 0

const projectId = computed(() => String(route.params.projectId || '').trim())
const storageKey = computed(() => `trial-operation-view:${projectId.value}`)
const metrics = computed(() => dashboard.value?.metrics || {})
const trialCompletion = computed(() => {
  const checks = [
    Number(metrics.value.requirementDocs || 0) > 0,
    Number(metrics.value.testcases || 0) > 0,
    Number(metrics.value.defects || 0) > 0,
    Boolean(caseGovernance.value && (caseGovernance.value.totalCases || 0) > 0),
    Boolean(governanceHistory.value && (governanceHistory.value.appliedSuggestions || 0) > 0),
    Number(metrics.value.executedCaseRuns || 0) > 0,
    reportSnapshots.value.length > 0
  ]
  const done = checks.filter(Boolean).length
  const score = Math.round((done / checks.length) * 100)
  return {
    done,
    total: checks.length,
    score,
    label: score >= 86 ? '演示闭环已完成' : score >= 60 ? '试运行基本闭环' : '试运行待补齐'
  }
})

const scoreLevelTone: Record<TrialOperationAcceptanceSummary['level'], string> = {
  PASS: 'text-[#008236] bg-[#F0FDF4] border-[#BBF7D0]',
  WARNING: 'text-[#B45309] bg-[#FFFBEB] border-[#FDE68A]',
  BLOCKED: 'text-[#C10007] bg-[#FEF2F2] border-[#FECACA]',
  INSUFFICIENT: 'text-[#475569] bg-[#F8FAFC] border-[#CBD5E1]'
}

const scoreLevelLabel: Record<TrialOperationAcceptanceSummary['level'], string> = {
  PASS: '通过',
  WARNING: '预警',
  BLOCKED: '阻塞',
  INSUFFICIENT: '数据不足'
}

const fallbackAcceptanceSummary = computed<TrialOperationAcceptanceSummary>(() => {
  const requirementDocs = Number(metrics.value.requirementDocs || 0)
  const testcases = Number(metrics.value.testcases || 0)
  const defects = Number(metrics.value.defects || 0)
  const riskHints = Number(metrics.value.riskHints || 0)
  const defectClusters = Number(metrics.value.defectClusters || 0)
  const coverageBase = requirementDocs + testcases
  const qualityDelta = Math.max(0, 100 - defects * 3 - riskHints * 5 - defectClusters * 2)
  const score = coverageBase <= 0 ? 0 : Math.max(20, Math.min(95, qualityDelta))
  const level: TrialOperationAcceptanceSummary['level'] =
    coverageBase <= 0 ? 'INSUFFICIENT' : score >= 75 ? 'PASS' : score >= 55 ? 'WARNING' : 'BLOCKED'
  const conclusion =
    level === 'PASS'
      ? '当前试运行质量可进入验收评审。'
      : level === 'WARNING'
        ? '当前质量存在风险项，建议完成修复后再验收。'
        : level === 'BLOCKED'
          ? '当前阻塞风险较高，不建议进入验收。'
          : '当前数据量不足，无法形成可靠验收结论。'
  return {
    conclusion,
    score,
    level,
    highlights: [
      `需求文档 ${requirementDocs} 份`,
      `测试用例 ${testcases} 条`,
      `最近导入记录 ${importHistory.value.length} 条`
    ],
    risks: [`缺陷 ${defects} 条`, `风险提示 ${riskHints} 条`, `缺陷聚类 ${defectClusters} 组`],
    nextActions: [
      '补充缺陷复现与修复验证',
      '聚焦高风险模块回归',
      '更新本轮验收结论并复核评分'
    ]
  }
})

const acceptanceSummary = computed<TrialOperationAcceptanceSummary>(() => {
  const raw = dashboard.value?.acceptanceSummary
  if (!raw) return fallbackAcceptanceSummary.value
  return {
    conclusion: String(raw.conclusion || fallbackAcceptanceSummary.value.conclusion),
    score: Number.isFinite(raw.score) ? Number(raw.score) : fallbackAcceptanceSummary.value.score,
    level: raw.level || fallbackAcceptanceSummary.value.level,
    highlights: Array.isArray(raw.highlights) && raw.highlights.length ? raw.highlights : fallbackAcceptanceSummary.value.highlights,
    risks: Array.isArray(raw.risks) && raw.risks.length ? raw.risks : fallbackAcceptanceSummary.value.risks,
    nextActions: Array.isArray(raw.nextActions) && raw.nextActions.length ? raw.nextActions : fallbackAcceptanceSummary.value.nextActions
  }
})

const metricCards = computed(() => [
  { label: '需求文档', value: metrics.value.requirementDocs || 0, icon: FileText, tone: 'bg-[#EFF6FF] text-[#155DFC]' },
  { label: '测试用例', value: metrics.value.testcases || 0, icon: TestTube2, tone: 'bg-[#F0FDF4] text-[#008236]' },
  { label: '缺陷', value: metrics.value.defects || 0, icon: Bug, tone: 'bg-[#FEF2F2] text-[#C10007]' },
  { label: '缺陷聚类', value: metrics.value.defectClusters || 0, icon: GitBranch, tone: 'bg-[#FFF7ED] text-[#C2410C]' },
  { label: '风险提示', value: metrics.value.riskHints || 0, icon: ShieldAlert, tone: 'bg-[#FDF2F8] text-[#BE185D]' }
])
const assetBaselineCards = computed(() => metricCards.value.slice(0, 3))
const riskBaselineCards = computed(() => metricCards.value.slice(3))

const dimensionOptions: Array<{ key: DimensionKey; label: string; accent: string }> = [
  { key: 'testcasePriorityDistribution', label: '用例优先级', accent: '#155DFC' },
  { key: 'testcaseStatusDistribution', label: '用例状态', accent: '#008236' },
  { key: 'testcaseTypeDistribution', label: '用例类型', accent: '#0F766E' },
  { key: 'testcaseFeatureDistribution', label: 'Top 功能模块', accent: '#7C3AED' },
  { key: 'defectSeverityDistribution', label: '缺陷严重级别', accent: '#C2410C' },
  { key: 'defectStatusDistribution', label: '缺陷状态', accent: '#BE123C' }
]

const importOptions: Array<{ type: ImportType; title: string; accept: string; description: string }> = [
  { type: 'requirements', title: '需求文档', accept: '.md,.txt,.docx,.pdf', description: '支持 MD / TXT / DOCX / PDF，上传后自动创建文档版本并触发解析' },
  { type: 'testcases', title: '测试用例', accept: '.csv,.xlsx', description: '支持 CSV / XLSX，表头沿用平台用例导入模板' },
  { type: 'defects', title: '缺陷数据', accept: '.json,.md', description: '支持 JSON 数组、{ items: [] } 或 Markdown 缺陷列表/表格，可直接导入 bug数量 目录里的 .md' }
]

const currentDimension = computed(() => dimensionOptions.find((item) => item.key === selectedDimension.value) || dimensionOptions[0])
const currentRows = computed(() => entries(dashboard.value?.[selectedDimension.value], topLimit.value))
const chartTotal = computed(() => currentRows.value.reduce((sum, [, value]) => sum + value, 0))
const maxRowValue = computed(() => Math.max(...currentRows.value.map(([, value]) => value), 1))
const governanceModuleRows = computed(() => entries(caseGovernance.value?.moduleDistribution, 10))
const governanceModuleTotal = computed(() => governanceModuleRows.value.reduce((sum, [, value]) => sum + value, 0))
const governanceMaxModuleValue = computed(() => Math.max(...governanceModuleRows.value.map(([, value]) => value), 1))
const selectedImportOption = computed(() => importOptions.find((item) => item.type === importType.value) || importOptions[0])
const activeQueueItem = computed(() => importQueue.value.find((item) => item.id === activeImportId.value) || null)
const currentImportPreview = computed(() => activeQueueItem.value ? activeQueueItem.value.preview : importPreview.value)
const currentImportMapping = computed({
  get: () => activeQueueItem.value ? activeQueueItem.value.mapping : importMapping.value,
  set: (value: Record<string, string>) => {
    if (activeQueueItem.value) {
      activeQueueItem.value.mapping = { ...value }
      return
    }
    importMapping.value = { ...value }
  }
})
const queueSummary = computed(() => ({
  total: importQueue.value.length,
  ready: importQueue.value.filter((item) => item.status === 'ready' || item.status === 'success').length,
  failed: importQueue.value.filter((item) => item.status === 'failed').length
}))
const governanceSuggestions = computed(() => governanceBatch.value?.items || [])
const governanceGenerateLabel = computed(() => governanceBatch.value ? '重新生成建议' : '生成治理建议')
const selectedGovernanceSuggestions = computed(() => {
  const selected = new Set(selectedGovernanceSuggestionIds.value)
  return governanceSuggestions.value.filter((item) => selected.has(item.id))
})
const canApplyGovernanceSuggestions = computed(() => selectedGovernanceSuggestions.value.some((item) => item.canApply))
const hasPreviewingQueue = computed(() => importQueue.value.some((item) => item.status === 'previewing'))
const importableQueue = computed(() => importQueue.value.filter((item) => item.preview && ['ready', 'success', 'failed'].includes(item.status)))
const importFileLabel = computed(() => {
  if (!activeQueueItem.value?.file) return '未选择文件'
  const kb = Math.max(1, Math.round(activeQueueItem.value.file.size / 1024))
  return `${activeQueueItem.value.file.name}（${kb} KB）`
})
const importErrors = computed(() => {
  if (!importResult.value) return []
  if (importResult.value.type === 'testcases') {
    return importResult.value.data.errors.map((item) => ({
      key: `case-${item.rowNumber}-${item.field || ''}-${item.message}`,
      title: `第 ${item.rowNumber} 行${item.field ? ` · ${item.field}` : ''}`,
      message: item.message
    }))
  }
  if (importResult.value.type === 'defects') {
    return importResult.value.data.errors.map((item) => ({
      key: `defect-${item.index}-${item.title || ''}-${item.error}`,
      title: `第 ${item.index + 1} 条${item.title ? ` · ${item.title}` : ''}`,
      message: item.error
    }))
  }
  return []
})
const mappingFields = computed(() => {
  if (importType.value === 'defects') {
    return [
      { key: 'title', label: '标题', required: true },
      { key: 'description', label: '描述', required: false },
      { key: 'severity', label: '严重级别', required: false },
      { key: 'source', label: '来源', required: false }
    ]
  }
  if (importType.value === 'testcases') {
    return [
      { key: 'title', label: '用例标题', required: true },
      { key: 'feature', label: '功能模块', required: false },
      { key: 'priority', label: '优先级', required: false },
      { key: 'type', label: '类型', required: false },
      { key: 'status', label: '状态', required: false }
    ]
  }
  return [
    { key: 'title', label: '需求标题', required: false },
    { key: 'content', label: '内容', required: false }
  ]
})
const importHistoryStatusLabel = (status: string) => {
  if (status === 'SUCCESS') return '成功'
  if (status === 'PARTIAL_SUCCESS') return '部分成功'
  return '失败'
}

const importQueueStatusLabel = (status: ImportQueueStatus) => {
  if (status === 'queued') return '排队'
  if (status === 'previewing') return '预览中'
  if (status === 'ready') return '可导入'
  if (status === 'importing') return '导入中'
  if (status === 'success') return '成功'
  return '失败'
}

const importQueueStatusClass = (status: ImportQueueStatus) => {
  if (status === 'success') return 'bg-[#F0FDF4] text-[#008236]'
  if (status === 'failed') return 'bg-[#FEF2F2] text-[#C10007]'
  if (status === 'importing' || status === 'previewing') return 'bg-[#EFF6FF] text-[#155DFC]'
  return 'bg-[#F6F7F9] text-[#717182]'
}

const governanceCategoryLabel = (category: TrialOperationGovernanceSuggestionItem['category']) => {
  if (category === 'DUPLICATE_TITLE') return '重复标题'
  if (category === 'LOW_VALUE') return '低价值'
  if (category === 'PROMOTE_TEST_POINT') return '待转正式'
  return 'P0 覆盖'
}

const governanceSeverityClass = (severity: TrialOperationGovernanceSuggestionItem['severity']) => {
  if (severity === 'HIGH') return 'bg-[#FEF2F2] text-[#C10007]'
  if (severity === 'MEDIUM') return 'bg-[#FFFBEB] text-[#B45309]'
  return 'bg-[#F0FDF4] text-[#008236]'
}

const governanceHistoryStatusLabel = (status: string) => {
  if (status === 'APPLIED') return '已应用'
  if (status === 'PARTIAL_APPLIED') return '部分应用'
  return '已生成'
}

const governanceHistoryStatusClass = (status: string) => {
  if (status === 'APPLIED') return 'text-[#008236]'
  if (status === 'PARTIAL_APPLIED') return 'text-[#B45309]'
  return 'text-[#717182]'
}

const metricLabelMap: Record<string, string> = {
  requirementDocs: '需求文档',
  testcases: '测试资产',
  defects: '缺陷记录',
  defectClusters: '缺陷聚类',
  riskHints: '风险提示',
  executedCaseRuns: '已执行用例'
}

const topLimitOptions = [5, 10, 16, 24]
const trialViewOptions: Array<{ key: TrialView; label: string; description: string }> = [
  { key: 'overview', label: '演示概览', description: '资产基线、验收结论、汇报稿和快照' },
  { key: 'import', label: '数据导入', description: '选择文件、字段映射、多文件导入' },
  { key: 'governance', label: '治理分析', description: '用例治理、AI建议、执行结果接入' },
  { key: 'details', label: '缺陷明细', description: '图表、缺陷聚类、风险提示和样例用例' }
]

const percentWidth = (value: number) => {
  return `${Math.max(3, Math.round((value / maxRowValue.value) * 100))}%`
}

const percentWidthByMax = (value: number, max: number) => {
  return `${Math.max(3, Math.round((value / Math.max(max, 1)) * 100))}%`
}

const percentText = (value: number) => {
  if (!chartTotal.value) return '0%'
  return `${Math.round((value / chartTotal.value) * 100)}%`
}

const percentTextByTotal = (value: number, total: number) => {
  if (!total) return '0%'
  return `${Math.round((value / total) * 100)}%`
}

const entries = (rows?: Record<string, number>, limit = 12) => {
  return Object.entries(rows || {})
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, limit)
}

const formatTime = (value?: number | null) => {
  if (!value) return '-'
  const date = new Date(value * 1000)
  if (Number.isNaN(date.getTime())) return '-'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date)
}

const formatReportDatePart = (date: Date) => {
  const pad = (value: number) => String(value).padStart(2, '0')
  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
    pad(date.getHours()),
    pad(date.getMinutes())
  ].join('')
}

const fallbackReportMarkdown = () => {
  const summary = acceptanceSummary.value
  const lines = [
    '# 试运行验收报告',
    '',
    `生成时间：${new Date().toLocaleString('zh-CN', { hour12: false })}`,
    '',
    '## 验收结论',
    summary.conclusion,
    '',
    `- 评分：${summary.score}`,
    `- 等级：${scoreLevelLabel[summary.level]}`,
    '',
    '## 亮点',
    ...summary.highlights.map((item) => `- ${item}`),
    '',
    '## 风险',
    ...summary.risks.map((item) => `- ${item}`),
    '',
    '## 下一步',
    ...summary.nextActions.map((item) => `- ${item}`),
    '',
    '## 核心指标'
  ]
  for (const [key, value] of Object.entries(metrics.value || {})) {
    lines.push(`- ${key}: ${value}`)
  }
  return lines.join('\n')
}

const deliveryNoteMarkdown = computed(() => {
  const summary = acceptanceSummary.value
  const completion = trialCompletion.value
  const metricLines = Object.entries(metrics.value || {}).map(([key, value]) => {
    return `- ${metricLabelMap[key] || key}：${value}`
  })
  const latestSnapshot = reportSnapshots.value[0]
  const latestImports = importHistory.value.slice(0, 3)
  const lines = [
    '# 试运行验收汇报稿',
    '',
    `生成时间：${new Date().toLocaleString('zh-CN', { hour12: false })}`,
    '',
    '## 当前结论',
    `- 验收建议：${summary.conclusion}`,
    `- 质量评分：${summary.score}`,
    `- 风险等级：${scoreLevelLabel[summary.level]}（${summary.level}）`,
    `- 试运行完成度：${completion.score}%（${completion.done}/${completion.total}，${completion.label}）`,
    '',
    '## 已接入真实数据',
    ...(metricLines.length ? metricLines : ['- 暂无数据']),
    '',
    '## 已完成的平台能力',
    '- 真实需求、用例、缺陷数据导入与可视化',
    '- 维度可切换的柱状图/列表看板',
    '- 验收结论自动汇总、报告生成、复制与下载',
    '- 验收报告快照归档、历史查看、复制与下载',
    '- AI 治理建议生成、确认应用与审计留痕',
    '',
    '## 主要亮点',
    ...(summary.highlights.length ? summary.highlights.map((item) => `- ${item}`) : ['- 暂无']),
    '',
    '## 当前风险',
    ...(summary.risks.length ? summary.risks.map((item) => `- ${item}`) : ['- 暂无阻塞风险']),
    '',
    '## 下一步建议',
    ...(summary.nextActions.length ? summary.nextActions.map((item) => `- ${item}`) : ['- 持续跟踪新增缺陷与回归结果']),
    '',
    '## 交付留痕',
    governanceHistory.value
      ? `- 治理建议：生成批次 ${governanceHistory.value.generatedBatches} 个，已应用建议 ${governanceHistory.value.appliedSuggestions} 条，更新用例 ${governanceHistory.value.updatedCases} 条`
      : '- 治理建议：暂无历史',
    latestSnapshot
      ? `- 最新验收报告快照：${latestSnapshot.title || '试运行验收报告'}，${formatTime(latestSnapshot.createdAt || latestSnapshot.generatedAt)}`
      : '- 最新验收报告快照：暂无',
    latestImports.length
      ? `- 最近导入记录：${latestImports.map((item) => `${item.fileName}（${importHistoryStatusLabel(item.status)}）`).join('；')}`
      : '- 最近导入记录：暂无'
  ]
  return lines.join('\n')
})

const applyReportData = (data: Pick<TrialOperationReportData, 'title' | 'generatedAt' | 'markdown'>) => {
  reportTitle.value = String(data.title || '试运行验收报告')
  reportGeneratedAt.value = Number(data.generatedAt || Math.floor(Date.now() / 1000))
  reportMarkdown.value = String(data.markdown || '').trim() || fallbackReportMarkdown()
  isReportExpanded.value = true
}

const generateReport = async () => {
  if (!projectId.value) return
  isGeneratingReport.value = true
  reportMessage.value = ''
  try {
    const data = await getTrialOperationReport(projectId.value)
    applyReportData(data)
    reportMessage.value = '报告已生成'
  } catch {
    applyReportData({
      title: '试运行验收报告（本地生成）',
      generatedAt: Math.floor(Date.now() / 1000),
      markdown: fallbackReportMarkdown()
    })
    reportMessage.value = '后端报告暂不可用，已使用当前看板数据生成本地报告'
  } finally {
    isGeneratingReport.value = false
  }
}

const fallbackCopyText = (text: string) => {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', 'true')
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  const copied = document.execCommand('copy')
  textarea.remove()
  if (!copied) throw new Error('copy-failed')
}

const copyMarkdownText = async (
  text: string,
  successMessage: string,
  messageTarget: { value: string } = reportMessage
) => {
  const normalized = text.trim()
  if (!normalized) {
    messageTarget.value = '暂无可复制内容'
    return false
  }
  try {
    await navigator.clipboard.writeText(normalized)
    messageTarget.value = successMessage
    return true
  } catch {
    try {
      fallbackCopyText(normalized)
      messageTarget.value = successMessage
      return true
    } catch {
      messageTarget.value = '复制失败，请手动复制'
      return false
    }
  }
}

const copyReport = async () => {
  const text = reportMarkdown.value.trim()
  if (!text) {
    reportMessage.value = '请先生成报告'
    return
  }
  await copyMarkdownText(text, '报告内容已复制')
}

const copyDeliveryNote = async () => {
  await copyMarkdownText(deliveryNoteMarkdown.value, '验收汇报稿已复制', deliveryNoteMessage)
}

const downloadDeliveryNote = () => {
  downloadTextFile(
    `trial-operation-delivery-note-${formatReportDatePart(new Date())}.md`,
    deliveryNoteMarkdown.value,
    'text/markdown;charset=utf-8'
  )
  deliveryNoteMessage.value = '验收汇报稿已下载'
}

const buildReportFileName = (generatedAt?: number | null) => {
  const date = generatedAt ? new Date(generatedAt * 1000) : new Date()
  return `trial-operation-report-${formatReportDatePart(date)}.md`
}

const downloadMarkdownText = (text: string, generatedAt: number | null | undefined, successMessage: string) => {
  const normalized = text.trim()
  if (!normalized) {
    reportMessage.value = '暂无可下载内容'
    return
  }
  downloadTextFile(buildReportFileName(generatedAt), normalized, 'text/markdown;charset=utf-8')
  reportMessage.value = successMessage
}

const downloadReport = () => {
  const text = reportMarkdown.value.trim()
  if (!text) {
    reportMessage.value = '请先生成报告'
    return
  }
  downloadMarkdownText(text, reportGeneratedAt.value, '报告已下载')
}

const loadReportSnapshots = async () => {
  if (!projectId.value) return
  isLoadingSnapshots.value = true
  try {
    const page = await getTrialOperationReportSnapshots(projectId.value, 5)
    reportSnapshots.value = page.items
  } catch {
    reportSnapshots.value = []
  } finally {
    isLoadingSnapshots.value = false
  }
}

const saveReportSnapshot = async () => {
  if (!projectId.value) return
  if (!reportMarkdown.value.trim()) {
    reportMessage.value = '请先生成报告'
    return
  }
  isSavingSnapshot.value = true
  reportMessage.value = ''
  try {
    const snapshot = await saveTrialOperationReportSnapshot(projectId.value, {
      title: reportTitle.value || '试运行验收报告',
      generatedAt: reportGeneratedAt.value || Math.floor(Date.now() / 1000),
      markdown: reportMarkdown.value.trim(),
      summary: acceptanceSummary.value
    })
    activeSnapshotId.value = snapshot.id
    reportMessage.value = '报告快照已保存'
    await loadReportSnapshots()
  } catch (error) {
    reportMessage.value = error instanceof Error ? error.message : '保存快照失败'
  } finally {
    isSavingSnapshot.value = false
  }
}

const viewReportSnapshot = async (snapshotId: string) => {
  if (!projectId.value) return
  activeSnapshotId.value = snapshotId
  reportMessage.value = ''
  try {
    const snapshot = await getTrialOperationReportSnapshot(projectId.value, snapshotId)
    applyReportData(snapshot)
    reportMessage.value = '已载入历史快照'
  } catch (error) {
    reportMessage.value = error instanceof Error ? error.message : '读取快照失败'
  }
}

const copyReportSnapshot = async (snapshotId: string) => {
  if (!projectId.value) return
  activeSnapshotId.value = snapshotId
  try {
    const snapshot = await getTrialOperationReportSnapshot(projectId.value, snapshotId)
    await copyMarkdownText(snapshot.markdown, '快照内容已复制')
  } catch (error) {
    reportMessage.value = error instanceof Error ? error.message : '复制快照失败'
  }
}

const downloadReportSnapshot = async (snapshotId: string) => {
  if (!projectId.value) return
  activeSnapshotId.value = snapshotId
  try {
    const snapshot = await getTrialOperationReportSnapshot(projectId.value, snapshotId)
    downloadMarkdownText(snapshot.markdown, snapshot.generatedAt, '快照已下载')
  } catch (error) {
    reportMessage.value = error instanceof Error ? error.message : '下载快照失败'
  }
}

const restoreViewConfig = () => {
  if (!storageKey.value) return
  try {
    const raw = localStorage.getItem(storageKey.value)
    if (!raw) return
    const config = JSON.parse(raw) as Partial<{
      chartMode: ChartMode
      selectedDimension: DimensionKey
      topLimit: number
    }>
    if (config.chartMode === 'bar' || config.chartMode === 'list') chartMode.value = config.chartMode
    if (dimensionOptions.some((item) => item.key === config.selectedDimension)) {
      selectedDimension.value = config.selectedDimension as DimensionKey
    }
    if (topLimitOptions.includes(Number(config.topLimit))) topLimit.value = Number(config.topLimit)
  } catch {
    localStorage.removeItem(storageKey.value)
  }
}

const persistViewConfig = () => {
  if (!storageKey.value) return
  localStorage.setItem(
    storageKey.value,
    JSON.stringify({
      chartMode: chartMode.value,
      selectedDimension: selectedDimension.value,
      topLimit: topLimit.value
    })
  )
}

const loadDashboard = async () => {
  if (!projectId.value) return
  isLoading.value = true
  errorMessage.value = ''
  try {
    dashboard.value = await getTrialOperationDashboard(projectId.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '获取试运行看板失败'
  } finally {
    isLoading.value = false
  }
}

const loadImportHistory = async () => {
  if (!projectId.value) return
  isLoadingImportHistory.value = true
  try {
    const page = await getTrialOperationImportRecords(projectId.value, 6)
    importHistory.value = page.items
  } catch {
    importHistory.value = []
  } finally {
    isLoadingImportHistory.value = false
  }
}

const resetImportState = () => {
  previewBatchToken += 1
  importQueue.value = []
  activeImportId.value = ''
  importMessage.value = ''
  importResult.value = null
  importPreview.value = null
  importMapping.value = {}
  isPreviewing.value = false
  if (fileInputRef.value) fileInputRef.value.value = ''
  if (directoryInputRef.value) directoryInputRef.value.value = ''
}

const loadCaseGovernance = async () => {
  if (!projectId.value) return
  try {
    caseGovernance.value = await getTrialOperationCaseGovernance(projectId.value)
  } catch {
    caseGovernance.value = null
  }
}

const loadGovernanceHistory = async () => {
  if (!projectId.value) return
  try {
    governanceHistory.value = await getTrialOperationGovernanceHistory(projectId.value, 5)
  } catch {
    governanceHistory.value = null
  }
}

const toggleGovernanceSuggestion = (id: string, checked: boolean) => {
  const current = new Set(selectedGovernanceSuggestionIds.value)
  if (checked) current.add(id)
  else current.delete(id)
  selectedGovernanceSuggestionIds.value = Array.from(current)
}

const generateGovernanceSuggestions = async () => {
  if (!projectId.value) return
  isGeneratingGovernanceSuggestions.value = true
  governanceMessage.value = ''
  try {
    const batch = await generateTrialOperationGovernanceSuggestions(projectId.value)
    governanceBatch.value = batch
    selectedGovernanceSuggestionIds.value = batch.items.filter((item) => item.canApply).map((item) => item.id)
    governanceMessage.value = batch.items.length
      ? `已生成 ${batch.items.length} 条治理建议；已应用过的同类建议会自动过滤`
      : '当前没有新的治理建议；已应用过的同类建议不会重复出现'
  } catch (error) {
    governanceMessage.value = error instanceof Error ? error.message : '生成治理建议失败'
  } finally {
    isGeneratingGovernanceSuggestions.value = false
  }
}

const applyGovernanceSuggestions = async () => {
  if (!projectId.value || !governanceBatch.value) return
  if (!selectedGovernanceSuggestionIds.value.length) {
    governanceMessage.value = '请先选择要应用的建议'
    return
  }
  isApplyingGovernanceSuggestions.value = true
  governanceMessage.value = ''
  try {
    const result = await applyTrialOperationGovernanceSuggestions(projectId.value, {
      batchId: governanceBatch.value.batchId,
      suggestionIds: selectedGovernanceSuggestionIds.value
    })
    governanceMessage.value = result.summary
    selectedGovernanceSuggestionIds.value = []
    await Promise.all([loadDashboard(), loadCaseGovernance(), loadGovernanceHistory()])
  } catch (error) {
    governanceMessage.value = error instanceof Error ? error.message : '应用治理建议失败'
  } finally {
    isApplyingGovernanceSuggestions.value = false
  }
}

const importExecutionResults = async () => {
  if (!projectId.value) return
  isImportingExecutionResults.value = true
  executionImportMessage.value = ''
  try {
    const result = await importTrialOperationExecutionResults(projectId.value, {
      totalLimit: executionImportLimit.value,
      note: '试运行看板一键写入核心用例执行结果'
    })
    executionImportMessage.value = `${result.summary}，Run ID：${result.runId}`
    await loadDashboard()
  } catch (error) {
    executionImportMessage.value = error instanceof Error ? error.message : '写入执行结果失败'
  } finally {
    isImportingExecutionResults.value = false
  }
}

const clearImportQueue = () => {
  resetImportState()
  importMessage.value = '已清空待导入文件'
}

const allowedExtensions = computed(() => selectedImportOption.value.accept.split(',').map((item) => item.trim().toLowerCase()))

const canAcceptFile = (file: File) => {
  const extension = `.${String(file.name || '').split('.').pop()?.toLowerCase() || ''}`
  return allowedExtensions.value.includes(extension)
}

const buildQueueLabel = (file: File) => {
  const relativePath = (file as File & { webkitRelativePath?: string }).webkitRelativePath
  return relativePath || file.name
}

const queueFile = (file: File) => {
  if (!canAcceptFile(file)) {
    importMessage.value = `当前类型只支持 ${selectedImportOption.value.accept}`
    return
  }
  const label = buildQueueLabel(file)
  const duplicated = importQueue.value.some((item) => item.label === label && item.file.size === file.size && item.file.lastModified === file.lastModified)
  if (duplicated) return
  const id = `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2, 8)}`
  importQueue.value = [
    ...importQueue.value,
    {
      id,
      file,
      label,
      preview: null,
      mapping: {},
      status: 'queued',
      result: null,
      error: ''
    }
  ]
  activeImportId.value = id
  const token = previewBatchToken
  previewChain = previewChain.then(async () => {
    if (token !== previewBatchToken) return
    await buildImportPreview(id)
  })
  void previewChain
}

const onImportFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  importMessage.value = ''
  importResult.value = null
  if (!files.length) return
  files.forEach((file) => queueFile(file))
}

const onImportDirectoryChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  importMessage.value = ''
  importResult.value = null
  if (!files.length) return
  files.forEach((file) => queueFile(file))
}

const onImportDrop = (event: DragEvent) => {
  const files = Array.from(event.dataTransfer?.files || [])
  if (!files.length) return
  importMessage.value = ''
  importResult.value = null
  files.forEach((file) => queueFile(file))
}

const buildImportPreview = async (queueId: string) => {
  const item = importQueue.value.find((entry) => entry.id === queueId)
  if (!item) return
  item.status = 'previewing'
  isPreviewing.value = true
  try {
    const preview = await previewTrialOperationImport(item.file, importType.value)
    item.preview = preview
    item.mapping = { ...preview.suggestedMapping }
    item.status = 'ready'
    if (activeImportId.value === item.id) {
      importPreview.value = preview
      importMapping.value = { ...item.mapping }
      if (preview.warnings.length) {
        importMessage.value = preview.warnings[0]
      }
    }
  } catch (error) {
    item.preview = null
    item.mapping = {}
    item.status = 'failed'
    item.error = error instanceof Error ? error.message : '预览失败'
    if (activeImportId.value === item.id) {
      importPreview.value = null
      importMapping.value = {}
      importMessage.value = item.error
    }
  } finally {
    isPreviewing.value = false
  }
}

const selectQueueItem = async (queueId: string) => {
  activeImportId.value = queueId
  const item = importQueue.value.find((entry) => entry.id === queueId)
  if (!item) return
  importPreview.value = item.preview
  importMapping.value = { ...item.mapping }
  if (!item.preview && item.status !== 'failed') {
    await buildImportPreview(queueId)
  }
}

const removeQueueItem = (queueId: string) => {
  const nextQueue = importQueue.value.filter((item) => item.id !== queueId)
  importQueue.value = nextQueue
  if (activeImportId.value === queueId) {
    const nextActive = nextQueue[0] || null
    activeImportId.value = nextActive?.id || ''
    importPreview.value = nextActive?.preview || null
    importMapping.value = nextActive?.mapping ? { ...nextActive.mapping } : {}
  }
}

const updateCurrentMapping = (key: string, value: string) => {
  currentImportMapping.value = { ...currentImportMapping.value, [key]: value }
}

const mappedCell = (row: Record<string, string>, key: string) => {
  const header = currentImportMapping.value[key]
  if (!header) return ''
  return row[header] || ''
}

const importResultCounts = () => {
  if (!importResult.value) return { total: 0, success: 0, failed: 0 }
  if (importResult.value.type === 'requirements') return { total: 1, success: 1, failed: 0 }
  if (importResult.value.type === 'defects') {
    return {
      total: importResult.value.data.total,
      success: importResult.value.data.success,
      failed: importResult.value.data.failed
    }
  }
  return {
    total: currentImportPreview.value?.totalRows || importResult.value.data.importedCount + importResult.value.data.failedCount,
    success: importResult.value.data.importedCount,
    failed: importResult.value.data.failedCount
  }
}

const countsForImportResult = (result: TrialOperationImportResult, preview?: TrialOperationImportPreview | null) => {
  if (result.type === 'requirements') return { total: 1, success: 1, failed: 0 }
  if (result.type === 'defects') {
    return {
      total: result.data.total,
      success: result.data.success,
      failed: result.data.failed
    }
  }
  return {
    total: preview?.totalRows || result.data.importedCount + result.data.failedCount,
    success: result.data.importedCount,
    failed: result.data.failedCount
  }
}

const summaryForImportResult = (fileName: string, result: TrialOperationImportResult) => {
  if (result.type === 'requirements') return `${fileName}：${result.data.parseStarted ? '解析已触发' : '导入完成'}`
  const counts = countsForImportResult(result)
  return `${fileName}：成功 ${counts.success} / 失败 ${counts.failed}`
}

const handleImport = async () => {
  if (!projectId.value) return
  const queue = importQueue.value.filter((item) => item.preview && item.status !== 'importing')
  if (!queue.length) {
    importMessage.value = '请先选择要导入的文件'
    return
  }
  isImporting.value = true
  importMessage.value = ''
  importResult.value = null
  try {
    const importedSummaries: string[] = []
    const failedSummaries: string[] = []
    for (const item of queue) {
      activeImportId.value = item.id
      item.status = 'importing'
      importPreview.value = item.preview
      importMapping.value = { ...item.mapping }
      if (item.preview) {
        currentImportMapping.value = { ...item.mapping }
      }
      try {
        if (importType.value === 'requirements') {
          const data = await importTrialOperationRequirementDoc(projectId.value, item.file)
          item.result = { type: 'requirements', data }
        } else if (importType.value === 'defects') {
          const data = await importTrialOperationDefects(projectId.value, item.file)
          item.result = { type: 'defects', data }
        } else {
          const data = await importTrialOperationTestcases(projectId.value, item.file)
          item.result = { type: 'testcases', data }
        }
        item.status = 'success'
        item.error = ''
        importResult.value = item.result
        importedSummaries.push(summaryForImportResult(item.file.name, item.result))
        const counts = countsForImportResult(item.result, item.preview)
        const status = counts.failed === 0 ? 'SUCCESS' : counts.success > 0 ? 'PARTIAL_SUCCESS' : 'FAILED'
        await recordTrialOperationImport(projectId.value, {
          importType: importType.value,
          fileName: item.file.name,
          status,
          totalRows: counts.total || item.preview?.totalRows || 0,
          successRows: counts.success,
          failedRows: counts.failed,
          summary: item.result.type === 'requirements'
            ? `需求文档导入完成：${item.file.name}`
            : item.result.type === 'defects'
              ? `缺陷导入完成：${item.file.name}`
              : `用例导入完成：${item.file.name}`,
          detail: {
            previewRows: item.preview?.sampleRows.length || 0,
            mapping: item.mapping,
            warnings: item.preview?.warnings || []
          }
        })
      } catch (error) {
        const message = error instanceof Error ? error.message : '导入失败'
        item.status = 'failed'
        item.error = message
        failedSummaries.push(`${item.file.name}：${message}`)
        await recordTrialOperationImport(projectId.value, {
          importType: importType.value,
          fileName: item.file.name,
          status: 'FAILED',
          totalRows: item.preview?.totalRows || 0,
          successRows: 0,
          failedRows: item.preview?.totalRows || 0,
          summary: `导入失败：${message}`,
          detail: {
            previewRows: item.preview?.sampleRows.length || 0,
            mapping: item.mapping,
            warnings: item.preview?.warnings || [],
            error: message
          }
        })
      }
    }
    importMessage.value = [...importedSummaries, ...failedSummaries].join('；')
    if (queue.length === 1 && importResult.value) {
      const counts = importResultCounts()
      importMessage.value =
        importResult.value.type === 'requirements'
          ? importMessage.value || '需求文档已导入，解析任务已触发'
          : importResult.value.type === 'defects'
            ? `缺陷导入完成：成功 ${counts.success} 条，失败 ${counts.failed} 条`
            : `用例导入完成：成功 ${counts.success} 条，失败 ${counts.failed} 条`
    }
    await loadDashboard()
    await loadCaseGovernance()
    await loadImportHistory()
  } finally {
    isImporting.value = false
  }
}

const downloadTextFile = (fileName: string, content: string, mimeType: string) => {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

const csvCell = (value: string) => `"${String(value).replace(/"/g, '""')}"`

const downloadImportTemplate = () => {
  if (importType.value === 'requirements') {
    downloadTextFile(
      'requirement-import-template.md',
      [
        '# 需求文档标题',
        '',
        '## 背景',
        '填写业务背景、目标用户、约束条件。',
        '',
        '## 功能范围',
        '- 功能点一',
        '- 功能点二',
        '',
        '## 验收标准',
        '- 给定某前置条件，当用户执行某操作，则系统应该返回某结果。'
      ].join('\n'),
      'text/markdown;charset=utf-8'
    )
    return
  }

  if (importType.value === 'defects') {
    downloadTextFile(
      'defects-import-template.md',
      [
        '# 缺陷导入模板',
        '',
        '| 优先级 | 状态 | 负责人 | 缺陷标题 |',
        '| --- | --- | --- | --- |',
        '| P1 | 未完成 | 张三 | 登录失败时错误提示不清晰 |',
        '| P2 | 已完成 | 李四 | 列表筛选条件刷新后丢失 |',
        '',
        '- 【活动页】按钮点击后没有 loading 反馈 (执行者: 王五, 状态: 未完成)'
      ].join('\n'),
      'text/markdown;charset=utf-8'
    )
    return
  }

  const headers = [
    'test_case_id',
    'feature',
    'title',
    'type',
    'priority',
    'status',
    'apiMethod',
    'apiUrl',
    'apiHeaders',
    'apiParams',
    'expected_status_code',
    'expectedResult',
    'preconditions',
    'postconditions',
    'tags'
  ]
  const row = [
    'TC_LOGIN_001',
    '登录',
    '用户名密码登录成功',
    'API',
    'P1',
    'ACTIVE',
    'POST',
    '/api/auth/login',
    '{"Content-Type":"application/json"}',
    '{"username":"qa","password":"***"}',
    '200',
    '返回 accessToken',
    '{}',
    '{}',
    '登录,冒烟'
  ]
  downloadTextFile(
    'testcases-import-template.csv',
    `${headers.map(csvCell).join(',')}\n${row.map(csvCell).join(',')}\n`,
    'text/csv;charset=utf-8'
  )
}

watch([chartMode, selectedDimension, topLimit], persistViewConfig)

watch(importType, resetImportState)

onMounted(() => {
  restoreViewConfig()
  void loadDashboard()
  void loadCaseGovernance()
  void loadGovernanceHistory()
  void loadImportHistory()
  void loadReportSnapshots()
})
</script>

<template>
  <main class="min-h-[calc(100vh-48px)] bg-[#F6F7F9] px-[16px] py-[16px] md:px-[24px] md:py-[24px]">
    <div class="mb-[16px] flex flex-col gap-[12px] md:flex-row md:items-center md:justify-between">
      <div>
        <div class="text-[13px] leading-[18px] text-[#717182]">真实数据试运行</div>
        <h1 class="mt-[2px] text-[20px] font-semibold leading-[28px] text-[#0A0A0A]">项目可视化看板</h1>
      </div>
      <button
        type="button"
        class="inline-flex h-[34px] items-center justify-center gap-[6px] rounded-[8px] border border-black/10 bg-white px-[12px] text-[14px] font-medium text-[#0A0A0A]"
        @click="loadDashboard"
      >
        <RefreshCw class="h-[14px] w-[14px]" :class="isLoading ? 'animate-spin' : ''" />
        {{ isLoading ? '刷新中' : '刷新' }}
      </button>
    </div>

    <div v-if="errorMessage" class="mb-[16px] flex items-start gap-[8px] rounded-[8px] border border-[#FCA5A5] bg-[#FEF2F2] p-[12px] text-[14px] text-[#991B1B]">
      <AlertTriangle class="mt-[2px] h-[16px] w-[16px] shrink-0" />
      <span>{{ errorMessage }}</span>
    </div>

    <div class="mb-[16px] rounded-[8px] border border-black/10 bg-white p-[8px]">
      <div class="grid grid-cols-2 gap-[6px] xl:grid-cols-4">
        <button
          v-for="item in trialViewOptions"
          :key="item.key"
          type="button"
          class="rounded-[8px] px-[12px] py-[10px] text-left transition-colors"
          :class="activeView === item.key ? 'bg-[#155DFC] text-white' : 'bg-white text-[#0A0A0A] hover:bg-[#F6F7F9]'"
          @click="activeView = item.key"
        >
          <span class="block text-[14px] font-semibold leading-[20px]">{{ item.label }}</span>
          <span class="mt-[2px] block text-[12px] leading-[16px]" :class="activeView === item.key ? 'text-white/75' : 'text-[#717182]'">
            {{ item.description }}
          </span>
        </button>
      </div>
    </div>

    <section v-if="activeView === 'overview'" class="mb-[16px] rounded-[8px] border border-black/10 bg-white p-[14px]">
      <div class="flex flex-col gap-[12px] lg:flex-row lg:items-center lg:justify-between">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-[8px]">
            <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">试运行完成度</div>
            <span class="rounded-[7px] bg-[#EFF6FF] px-[8px] py-[2px] text-[12px] font-medium text-[#155DFC]">{{ trialCompletion.label }}</span>
          </div>
          <div class="mt-[5px] text-[12px] leading-[18px] text-[#717182]">
            已完成 {{ trialCompletion.done }} / {{ trialCompletion.total }} 项：数据导入、用例治理、执行接入、报告快照会共同影响演示闭环。
          </div>
        </div>
        <div class="w-full shrink-0 lg:w-[340px]">
          <div class="flex items-center justify-between text-[12px] text-[#717182]">
            <span>完成度</span>
            <span class="font-medium text-[#0A0A0A]">{{ trialCompletion.score }}%</span>
          </div>
          <div class="mt-[7px] h-[10px] overflow-hidden rounded-full bg-[#EEF1F5]">
            <div class="h-full rounded-full bg-[#155DFC]" :style="{ width: `${Math.max(4, trialCompletion.score)}%` }" />
          </div>
        </div>
      </div>
    </section>

    <section v-if="activeView === 'overview'" class="mb-[16px] grid grid-cols-1 gap-[12px] xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
      <div class="rounded-[8px] border border-black/10 bg-white p-[14px]">
        <div class="flex flex-col gap-[4px] sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">资产基线</div>
            <div class="mt-[2px] text-[12px] leading-[16px] text-[#717182]">需求、用例和缺陷是本轮验收的数据资产入口。</div>
          </div>
          <RouterLink
            :to="`/projects/${encodeURIComponent(projectId)}/assets`"
            class="text-[12px] font-medium text-[#155DFC] hover:underline"
          >
            进入资产中心
          </RouterLink>
        </div>
        <div class="mt-[12px] grid grid-cols-1 gap-[10px] sm:grid-cols-3">
          <div v-for="card in assetBaselineCards" :key="card.label" class="rounded-[8px] border border-black/10 bg-[#FAFBFC] p-[12px]">
            <div class="flex items-center justify-between">
              <div class="text-[12px] leading-[16px] text-[#717182]">{{ card.label }}</div>
              <div class="flex h-[28px] w-[28px] items-center justify-center rounded-[8px]" :class="card.tone">
                <component :is="card.icon" class="h-[14px] w-[14px]" />
              </div>
            </div>
            <div class="mt-[10px] text-[22px] font-semibold leading-[30px] text-[#0A0A0A]">{{ card.value }}</div>
          </div>
        </div>
      </div>

      <div class="rounded-[8px] border border-black/10 bg-white p-[14px]">
        <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">风险基线</div>
        <div class="mt-[2px] text-[12px] leading-[16px] text-[#717182]">聚类和风险提示用于验收判断，不再和资产入口混在页面底部。</div>
        <div class="mt-[12px] grid grid-cols-1 gap-[10px] sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
          <div v-for="card in riskBaselineCards" :key="card.label" class="rounded-[8px] border border-black/10 bg-[#FAFBFC] p-[12px]">
            <div class="flex items-center justify-between">
              <div class="text-[12px] leading-[16px] text-[#717182]">{{ card.label }}</div>
              <div class="flex h-[28px] w-[28px] items-center justify-center rounded-[8px]" :class="card.tone">
                <component :is="card.icon" class="h-[14px] w-[14px]" />
              </div>
            </div>
            <div class="mt-[10px] text-[22px] font-semibold leading-[30px] text-[#0A0A0A]">{{ card.value }}</div>
          </div>
        </div>
      </div>
    </section>

    <section v-if="activeView === 'overview'" class="mb-[16px] rounded-[8px] border border-black/10 bg-white p-[14px] md:p-[16px]">
      <div class="grid grid-cols-1 gap-[14px] xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.55fr)] xl:items-start">
        <div class="min-w-0">
          <div class="text-[12px] leading-[16px] text-[#717182]">验收结论 / 质量报告摘要</div>
          <div class="mt-[6px] text-[16px] font-semibold leading-[24px] text-[#0A0A0A]">{{ acceptanceSummary.conclusion }}</div>
          <div class="mt-[10px] flex flex-wrap items-center gap-[8px]">
            <span class="inline-flex items-center rounded-[8px] border border-black/10 bg-[#F6F7F9] px-[10px] py-[4px] text-[12px] font-medium text-[#0A0A0A]">
              评分 {{ acceptanceSummary.score }}
            </span>
            <span
              class="inline-flex items-center rounded-[8px] border px-[10px] py-[4px] text-[12px] font-medium"
              :class="scoreLevelTone[acceptanceSummary.level]"
            >
              {{ scoreLevelLabel[acceptanceSummary.level] }}
            </span>
          </div>
          <div class="mt-[10px] flex flex-wrap items-center gap-[8px]">
            <button
              type="button"
              class="inline-flex h-[32px] items-center justify-center gap-[6px] rounded-[8px] border border-[#155DFC] bg-[#EFF6FF] px-[10px] text-[12px] font-medium text-[#155DFC] disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="isGeneratingReport"
              @click="generateReport"
            >
              <RefreshCw class="h-[13px] w-[13px]" :class="isGeneratingReport ? 'animate-spin' : ''" />
              {{ isGeneratingReport ? '生成中' : '生成报告' }}
            </button>
            <button
              type="button"
              class="inline-flex h-[32px] items-center justify-center gap-[6px] rounded-[8px] border border-black/10 bg-white px-[10px] text-[12px] font-medium text-[#374151]"
              @click="copyReport"
            >
              复制报告
            </button>
            <button
              type="button"
              class="inline-flex h-[32px] items-center justify-center gap-[6px] rounded-[8px] border border-black/10 bg-white px-[10px] text-[12px] font-medium text-[#374151]"
              @click="downloadReport"
            >
              <Download class="h-[13px] w-[13px]" />
              下载 .md
            </button>
            <button
              type="button"
              class="inline-flex h-[32px] items-center justify-center gap-[6px] rounded-[8px] border border-[#0F766E] bg-[#F0FDFA] px-[10px] text-[12px] font-medium text-[#0F766E] disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="isSavingSnapshot"
              @click="saveReportSnapshot"
            >
              <Save class="h-[13px] w-[13px]" />
              {{ isSavingSnapshot ? '保存中' : '保存快照' }}
            </button>
          </div>
          <div v-if="reportMessage" class="mt-[8px] text-[12px] leading-[16px] text-[#4B5563]">{{ reportMessage }}</div>
        </div>

        <div class="grid grid-cols-1 gap-[10px] md:grid-cols-3">
          <div class="rounded-[8px] bg-[#F8FAFC] p-[10px]">
            <div class="text-[12px] font-medium leading-[16px] text-[#334155]">亮点</div>
            <ul class="mt-[6px] space-y-[4px] text-[12px] leading-[17px] text-[#475569]">
              <li v-for="(item, index) in acceptanceSummary.highlights" :key="`highlight-${index}-${item}`" class="break-words">
                {{ item }}
              </li>
            </ul>
          </div>
          <div class="rounded-[8px] bg-[#FFFBEB] p-[10px]">
            <div class="text-[12px] font-medium leading-[16px] text-[#92400E]">风险</div>
            <ul class="mt-[6px] space-y-[4px] text-[12px] leading-[17px] text-[#B45309]">
              <li v-for="(item, index) in acceptanceSummary.risks" :key="`risk-${index}-${item}`" class="break-words">
                {{ item }}
              </li>
            </ul>
          </div>
          <div class="rounded-[8px] bg-[#EEF6FF] p-[10px]">
            <div class="text-[12px] font-medium leading-[16px] text-[#1D4ED8]">下一步</div>
            <ul class="mt-[6px] space-y-[4px] text-[12px] leading-[17px] text-[#1E40AF]">
              <li v-for="(item, index) in acceptanceSummary.nextActions" :key="`action-${index}-${item}`" class="break-words">
                {{ item }}
              </li>
            </ul>
          </div>
        </div>
      </div>
      <div v-if="reportMarkdown" class="mt-[12px] rounded-[8px] border border-black/10 bg-[#FAFBFC]">
        <button
          type="button"
          class="flex w-full items-center justify-between rounded-[8px] px-[12px] py-[10px] text-left"
          @click="isReportExpanded = !isReportExpanded"
        >
          <span class="truncate text-[13px] font-medium text-[#0A0A0A]">
            {{ reportTitle || '试运行验收报告' }} · {{ formatTime(reportGeneratedAt) }}
          </span>
          <span class="shrink-0 text-[12px] text-[#155DFC]">{{ isReportExpanded ? '收起' : '展开' }}</span>
        </button>
        <div v-if="isReportExpanded" class="border-t border-black/10 px-[12px] py-[10px]">
          <pre class="max-h-[280px] overflow-auto whitespace-pre-wrap break-words rounded-[8px] bg-white p-[10px] text-[12px] leading-[18px] text-[#334155]">{{ reportMarkdown }}</pre>
        </div>
      </div>
      <div class="mt-[12px] rounded-[8px] border border-black/10 bg-white">
        <div class="flex items-center justify-between gap-[10px] border-b border-black/10 px-[12px] py-[10px]">
          <div>
            <div class="text-[13px] font-medium leading-[18px] text-[#0A0A0A]">快照历史</div>
            <div class="mt-[2px] text-[12px] leading-[16px] text-[#717182]">最新验收报告快照</div>
          </div>
          <button type="button" class="shrink-0 text-[12px] text-[#155DFC]" @click="loadReportSnapshots">刷新</button>
        </div>
        <div v-if="isLoadingSnapshots" class="px-[12px] py-[10px] text-[12px] text-[#717182]">加载快照历史...</div>
        <div v-else-if="!reportSnapshots.length" class="px-[12px] py-[12px] text-[12px] text-[#717182]">暂无快照</div>
        <div v-else class="divide-y divide-black/5">
          <div v-for="snapshot in reportSnapshots" :key="snapshot.id" class="px-[12px] py-[10px]">
            <div class="flex flex-col gap-[8px] md:flex-row md:items-center md:justify-between">
              <div class="min-w-0">
                <div class="truncate text-[13px] font-medium leading-[18px] text-[#0A0A0A]" :title="snapshot.title">
                  {{ snapshot.title || '试运行验收报告' }}
                </div>
                <div class="mt-[3px] flex flex-wrap items-center gap-[6px] text-[11px] leading-[15px] text-[#717182]">
                  <span>{{ formatTime(snapshot.generatedAt) }}</span>
                  <span v-if="typeof snapshot.score === 'number'">评分 {{ snapshot.score }}</span>
                  <span
                    v-if="snapshot.level"
                    class="inline-flex items-center rounded-[6px] border px-[6px] py-[1px] text-[11px] font-medium"
                    :class="scoreLevelTone[snapshot.level]"
                  >
                    {{ scoreLevelLabel[snapshot.level] }}
                  </span>
                </div>
              </div>
              <div class="flex shrink-0 flex-wrap items-center gap-[6px]">
                <button
                  type="button"
                  class="inline-flex h-[28px] items-center justify-center rounded-[7px] border border-black/10 bg-white px-[9px] text-[12px] font-medium text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-60"
                  :disabled="activeSnapshotId === snapshot.id && isLoadingSnapshots"
                  @click="viewReportSnapshot(snapshot.id)"
                >
                  查看
                </button>
                <button
                  type="button"
                  class="inline-flex h-[28px] items-center justify-center rounded-[7px] border border-black/10 bg-white px-[9px] text-[12px] font-medium text-[#374151] hover:bg-[#F9FAFB]"
                  @click="copyReportSnapshot(snapshot.id)"
                >
                  复制
                </button>
                <button
                  type="button"
                  class="inline-flex h-[28px] items-center justify-center gap-[5px] rounded-[7px] border border-black/10 bg-white px-[9px] text-[12px] font-medium text-[#374151] hover:bg-[#F9FAFB]"
                  @click="downloadReportSnapshot(snapshot.id)"
                >
                  <Download class="h-[12px] w-[12px]" />
                  下载
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="mt-[12px] rounded-[8px] border border-black/10 bg-[#FAFBFC]">
        <div class="flex flex-col gap-[10px] border-b border-black/10 px-[12px] py-[10px] md:flex-row md:items-center md:justify-between">
          <div>
            <div class="text-[13px] font-medium leading-[18px] text-[#0A0A0A]">验收汇报稿</div>
            <div class="mt-[2px] text-[12px] leading-[16px] text-[#717182]">面向项目汇报的交付摘要</div>
          </div>
          <div class="flex shrink-0 flex-wrap items-center gap-[6px]">
            <button
              type="button"
              class="inline-flex h-[28px] items-center justify-center rounded-[7px] border border-black/10 bg-white px-[9px] text-[12px] font-medium text-[#374151] hover:bg-[#F9FAFB]"
              @click="copyDeliveryNote"
            >
              复制汇报稿
            </button>
            <button
              type="button"
              class="inline-flex h-[28px] items-center justify-center gap-[5px] rounded-[7px] border border-black/10 bg-white px-[9px] text-[12px] font-medium text-[#374151] hover:bg-[#F9FAFB]"
              @click="downloadDeliveryNote"
            >
              <Download class="h-[12px] w-[12px]" />
              下载
            </button>
          </div>
        </div>
        <div v-if="deliveryNoteMessage" class="px-[12px] pt-[8px] text-[12px] text-[#4B5563]">{{ deliveryNoteMessage }}</div>
        <div class="px-[12px] py-[10px]">
          <pre class="max-h-[220px] overflow-auto whitespace-pre-wrap break-words rounded-[8px] bg-white p-[10px] text-[12px] leading-[18px] text-[#334155]">{{ deliveryNoteMarkdown }}</pre>
        </div>
      </div>
    </section>

    <section v-if="activeView === 'governance'" class="mt-[16px] rounded-[8px] border border-black/10 bg-white p-[18px]">
      <div class="flex flex-col gap-[10px] lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 class="flex items-center gap-[8px] text-[15px] font-semibold leading-[22px] text-[#0A0A0A]">
            <Sparkles class="h-[16px] w-[16px] text-[#7C3AED]" />
            用例库治理
          </h2>
          <div class="mt-[4px] text-[12px] leading-[18px] text-[#717182]">按需求/模块/优先级/类型分层，辅助识别重复标题、低价值候选和 P0 覆盖密度</div>
          <div class="mt-[3px] text-[12px] leading-[18px] text-[#B45309]">资产总量包含历史测试点；正式用例按源文件原始用例 ID 统计，平台补号项建议治理后再进入验收执行。</div>
        </div>
        <div class="grid grid-cols-2 gap-[8px] sm:grid-cols-4">
          <div class="rounded-[8px] bg-[#F6F7F9] px-[12px] py-[9px]">
            <div class="text-[11px] leading-[15px] text-[#717182]">资产总量</div>
            <div class="mt-[3px] text-[18px] font-semibold leading-[24px] text-[#0A0A0A]">{{ caseGovernance?.totalCases || 0 }}</div>
          </div>
          <div class="rounded-[8px] bg-[#F0FDF4] px-[12px] py-[9px]">
            <div class="text-[11px] leading-[15px] text-[#166534]">正式用例</div>
            <div class="mt-[3px] text-[18px] font-semibold leading-[24px] text-[#008236]">{{ caseGovernance?.formalCases || 0 }}</div>
          </div>
          <div class="rounded-[8px] bg-[#FEF2F2] px-[12px] py-[9px]">
            <div class="text-[11px] leading-[15px] text-[#991B1B]">测试点</div>
            <div class="mt-[3px] text-[18px] font-semibold leading-[24px] text-[#C10007]">{{ caseGovernance?.testPointCases || 0 }}</div>
          </div>
          <div class="rounded-[8px] bg-[#EFF6FF] px-[12px] py-[9px]">
            <div class="text-[11px] leading-[15px] text-[#155DFC]">平台补号</div>
            <div class="mt-[3px] text-[18px] font-semibold leading-[24px] text-[#155DFC]">{{ caseGovernance?.generatedImportIds || 0 }}</div>
          </div>
        </div>
      </div>

      <div class="mt-[16px] grid grid-cols-1 gap-[16px] xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
        <div class="rounded-[8px] border border-black/10 p-[14px]">
          <div class="flex items-center justify-between gap-[12px]">
            <div class="text-[13px] font-medium text-[#0A0A0A]">模块用例分布 Top10</div>
            <div class="text-[12px] text-[#717182]">当前合计 {{ governanceModuleTotal }} 条</div>
          </div>
          <div class="mt-[12px] space-y-[9px]">
            <div v-for="[name, value] in governanceModuleRows" :key="name" class="grid grid-cols-[minmax(92px,240px)_1fr_78px] items-center gap-[10px]">
              <div class="truncate text-[12px] text-[#374151]" :title="name">{{ name }}</div>
              <div class="h-[12px] overflow-hidden rounded-full bg-[#EEF1F5]">
                <div class="h-full rounded-full bg-[#7C3AED]" :style="{ width: percentWidthByMax(value, governanceMaxModuleValue) }" />
              </div>
              <div class="text-right text-[11px] text-[#717182]">{{ value }} · {{ percentTextByTotal(value, governanceModuleTotal) }}</div>
            </div>
            <div v-if="!governanceModuleRows.length" class="rounded-[8px] bg-[#F6F7F9] px-[10px] py-[8px] text-[12px] text-[#717182]">暂无模块分布数据</div>
          </div>
        </div>

        <div class="rounded-[8px] border border-black/10 p-[14px]">
          <div class="text-[13px] font-medium text-[#0A0A0A]">P0 覆盖密度 Top</div>
          <div class="mt-[12px] space-y-[8px]">
            <div v-for="item in caseGovernance?.moduleP0Density || []" :key="item.feature" class="rounded-[8px] bg-[#F6F7F9] px-[10px] py-[8px]">
              <div class="flex items-center justify-between gap-[8px]">
                <div class="min-w-0 truncate text-[12px] font-medium text-[#0A0A0A]" :title="item.feature">{{ item.feature }}</div>
                <div class="shrink-0 text-[12px] text-[#C10007]">{{ item.p0Density }}%</div>
              </div>
              <div class="mt-[4px] text-[11px] text-[#717182]">P0 {{ item.p0 }} / 总量 {{ item.total }}</div>
            </div>
            <div v-if="!(caseGovernance?.moduleP0Density || []).length" class="rounded-[8px] bg-[#F6F7F9] px-[10px] py-[8px] text-[12px] text-[#717182]">暂无 P0 密度数据</div>
          </div>
        </div>
      </div>

      <div class="mt-[16px] grid grid-cols-1 gap-[16px] xl:grid-cols-2">
        <div class="rounded-[8px] border border-black/10 p-[14px]">
          <div class="flex items-center justify-between gap-[12px]">
            <div class="text-[13px] font-medium text-[#0A0A0A]">重复标题候选</div>
            <div class="text-[12px] text-[#717182]">{{ (caseGovernance?.duplicateTitleCandidates || []).length }} 组</div>
          </div>
          <div class="mt-[12px] max-h-[260px] overflow-auto">
            <div v-for="item in caseGovernance?.duplicateTitleCandidates || []" :key="item.title" class="border-b border-black/5 py-[8px] last:border-b-0">
              <div class="flex items-center justify-between gap-[10px]">
                <div class="min-w-0 truncate text-[12px] font-medium text-[#0A0A0A]" :title="item.title">{{ item.title }}</div>
                <div class="shrink-0 rounded-full bg-[#FFFBEB] px-[7px] py-[2px] text-[11px] text-[#B45309]">{{ item.count }} 条</div>
              </div>
              <div class="mt-[4px] truncate text-[11px] text-[#717182]" :title="(item.modules || []).join(' / ')">{{ (item.modules || []).join(' / ') || '未分组' }}</div>
            </div>
            <div v-if="!(caseGovernance?.duplicateTitleCandidates || []).length" class="rounded-[8px] bg-[#F6F7F9] px-[10px] py-[8px] text-[12px] text-[#717182]">暂无重复标题候选</div>
          </div>
        </div>

        <div class="rounded-[8px] border border-black/10 p-[14px]">
          <div class="flex items-center justify-between gap-[12px]">
            <div class="text-[13px] font-medium text-[#0A0A0A]">低价值候选</div>
            <div class="text-[12px] text-[#717182]">{{ (caseGovernance?.lowValueCandidates || []).length }} 条</div>
          </div>
          <div class="mt-[12px] max-h-[260px] overflow-auto">
            <div v-for="item in caseGovernance?.lowValueCandidates || []" :key="item.id" class="border-b border-black/5 py-[8px] last:border-b-0">
              <div class="flex items-center justify-between gap-[10px]">
                <div class="min-w-0 truncate text-[12px] font-medium text-[#0A0A0A]" :title="item.title">{{ item.title }}</div>
                <div class="shrink-0 text-[11px] text-[#717182]">{{ item.priority }} · {{ item.type }}</div>
              </div>
              <div class="mt-[3px] truncate text-[11px] text-[#717182]" :title="item.feature || ''">{{ item.testCaseId || '-' }} · {{ item.feature || '未分组' }}</div>
              <div class="mt-[5px] flex flex-wrap gap-[5px]">
                <span v-for="reason in item.reasons" :key="reason" class="rounded-full bg-[#FEF2F2] px-[7px] py-[2px] text-[11px] text-[#C10007]">{{ reason }}</span>
              </div>
            </div>
            <div v-if="!(caseGovernance?.lowValueCandidates || []).length" class="rounded-[8px] bg-[#F6F7F9] px-[10px] py-[8px] text-[12px] text-[#717182]">暂无低价值候选</div>
          </div>
        </div>
      </div>

      <div class="mt-[16px] rounded-[8px] border border-black/10 bg-[#FAFBFC] p-[14px]">
        <div class="flex flex-col gap-[10px] lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div class="flex items-center gap-[8px] text-[13px] font-medium text-[#0A0A0A]">
              <Sparkles class="h-[15px] w-[15px] text-[#7C3AED]" />
              AI 自动治理
            </div>
            <div class="mt-[4px] text-[12px] leading-[18px] text-[#717182]">生成建议后先预览勾选，确认后才会给用例打治理标签或转入评审状态。</div>
            <div v-if="governanceBatch" class="mt-[3px] text-[12px] leading-[18px] text-[#B45309]">当前批次：{{ governanceBatch.batchId }}；重新生成会覆盖当前预览，不会重复展示已应用过的同类建议。</div>
          </div>
          <div class="flex shrink-0 flex-wrap items-center gap-[8px]">
            <button
              type="button"
              class="inline-flex h-[32px] items-center justify-center gap-[6px] rounded-[8px] bg-[#7C3AED] px-[12px] text-[13px] font-medium text-white disabled:bg-black/20"
              :disabled="isGeneratingGovernanceSuggestions"
              @click="generateGovernanceSuggestions"
            >
              <RefreshCw v-if="isGeneratingGovernanceSuggestions" class="h-[14px] w-[14px] animate-spin" />
              <Sparkles v-else class="h-[14px] w-[14px]" />
              {{ isGeneratingGovernanceSuggestions ? '生成中' : governanceGenerateLabel }}
            </button>
            <button
              type="button"
              class="inline-flex h-[32px] items-center justify-center gap-[6px] rounded-[8px] bg-[#155DFC] px-[12px] text-[13px] font-medium text-white disabled:bg-black/20"
              :disabled="isApplyingGovernanceSuggestions || !canApplyGovernanceSuggestions"
              @click="applyGovernanceSuggestions"
            >
              <RefreshCw v-if="isApplyingGovernanceSuggestions" class="h-[14px] w-[14px] animate-spin" />
              <CheckCircle2 v-else class="h-[14px] w-[14px]" />
              {{ isApplyingGovernanceSuggestions ? '应用中' : `确认应用 ${selectedGovernanceSuggestionIds.length} 条` }}
            </button>
          </div>
        </div>
        <div v-if="governanceMessage" class="mt-[10px] rounded-[8px] border border-black/10 bg-white px-[10px] py-[8px] text-[12px] text-[#374151]">{{ governanceMessage }}</div>
        <div v-if="governanceBatch" class="mt-[12px] grid grid-cols-2 gap-[8px] md:grid-cols-5">
          <div class="rounded-[8px] bg-white px-[10px] py-[8px]">
            <div class="text-[11px] text-[#717182]">总建议</div>
            <div class="mt-[3px] text-[18px] font-semibold text-[#0A0A0A]">{{ governanceBatch.summary.total || governanceSuggestions.length }}</div>
          </div>
          <div class="rounded-[8px] bg-white px-[10px] py-[8px]">
            <div class="text-[11px] text-[#717182]">重复</div>
            <div class="mt-[3px] text-[18px] font-semibold text-[#B45309]">{{ governanceBatch.summary.duplicates || 0 }}</div>
          </div>
          <div class="rounded-[8px] bg-white px-[10px] py-[8px]">
            <div class="text-[11px] text-[#717182]">低价值</div>
            <div class="mt-[3px] text-[18px] font-semibold text-[#C10007]">{{ governanceBatch.summary.lowValue || 0 }}</div>
          </div>
          <div class="rounded-[8px] bg-white px-[10px] py-[8px]">
            <div class="text-[11px] text-[#717182]">待转正式</div>
            <div class="mt-[3px] text-[18px] font-semibold text-[#155DFC]">{{ governanceBatch.summary.promotableTestPoints || 0 }}</div>
          </div>
          <div class="rounded-[8px] bg-white px-[10px] py-[8px]">
            <div class="text-[11px] text-[#717182]">P0 缺口</div>
            <div class="mt-[3px] text-[18px] font-semibold text-[#7C3AED]">{{ governanceBatch.summary.p0CoverageGaps || 0 }}</div>
          </div>
        </div>
        <div v-if="governanceSuggestions.length" class="mt-[12px] max-h-[360px] overflow-auto rounded-[8px] border border-black/10 bg-white">
          <label
            v-for="item in governanceSuggestions"
            :key="item.id"
            class="flex cursor-pointer items-start gap-[10px] border-b border-black/5 px-[10px] py-[9px] last:border-b-0 hover:bg-[#F9FAFB]"
          >
            <input
              type="checkbox"
              class="mt-[3px] h-4 w-4 accent-[#155DFC]"
              :checked="selectedGovernanceSuggestionIds.includes(item.id)"
              :disabled="!item.canApply"
              @change="toggleGovernanceSuggestion(item.id, ($event.target as HTMLInputElement).checked)"
            />
            <span class="min-w-0 flex-1">
              <span class="flex flex-wrap items-center gap-[6px]">
                <span class="text-[12px] font-medium text-[#0A0A0A]">{{ item.title }}</span>
                <span class="rounded-full px-[7px] py-[2px] text-[11px]" :class="governanceSeverityClass(item.severity)">{{ item.severity }}</span>
                <span class="rounded-full bg-[#F6F7F9] px-[7px] py-[2px] text-[11px] text-[#717182]">{{ governanceCategoryLabel(item.category) }}</span>
              </span>
              <span class="mt-[4px] block text-[12px] leading-[17px] text-[#4B5563]">{{ item.reason }}</span>
              <span class="mt-[3px] block text-[12px] leading-[17px] text-[#717182]">{{ item.recommendation }}</span>
              <span class="mt-[5px] block text-[11px] text-[#9CA3AF]">影响 {{ item.targetCount }} 条 · 置信度 {{ Math.round(item.confidence * 100) }}%</span>
            </span>
          </label>
        </div>
        <div class="mt-[12px] rounded-[8px] border border-black/10 bg-white">
          <div class="flex items-center justify-between gap-[10px] border-b border-black/10 px-[10px] py-[8px]">
            <div>
              <div class="text-[13px] font-medium text-[#0A0A0A]">治理历史</div>
              <div class="mt-[2px] text-[12px] text-[#717182]">
                已应用 {{ governanceHistory?.appliedSuggestions || 0 }} 条建议，更新 {{ governanceHistory?.updatedCases || 0 }} 条用例
              </div>
            </div>
            <button type="button" class="shrink-0 text-[12px] text-[#155DFC]" @click="loadGovernanceHistory">刷新</button>
          </div>
          <div v-if="!(governanceHistory?.items || []).length" class="px-[10px] py-[10px] text-[12px] text-[#717182]">暂无治理历史</div>
          <div v-else class="max-h-[190px] overflow-auto divide-y divide-black/5">
            <div v-for="item in governanceHistory?.items || []" :key="item.batchId" class="px-[10px] py-[8px]">
              <div class="flex items-center justify-between gap-[10px]">
                <div class="min-w-0 truncate text-[12px] font-medium text-[#0A0A0A]" :title="item.batchId">{{ item.batchId }}</div>
                <div class="shrink-0 text-[11px]" :class="governanceHistoryStatusClass(item.status)">{{ governanceHistoryStatusLabel(item.status) }}</div>
              </div>
              <div class="mt-[3px] text-[11px] leading-[15px] text-[#717182]">{{ item.summary }} · {{ formatTime(item.generatedAt) }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="mt-[16px] rounded-[8px] border border-black/10 bg-white p-[14px]">
        <div class="flex flex-col gap-[10px] md:flex-row md:items-center md:justify-between">
          <div>
            <div class="text-[13px] font-medium text-[#0A0A0A]">执行结果接入</div>
            <div class="mt-[4px] text-[12px] leading-[18px] text-[#717182]">先写入一轮核心正式用例执行记录，让验收结论从“待执行验证”进入可评估状态。</div>
          </div>
          <div class="flex shrink-0 flex-wrap items-center gap-[8px]">
            <label class="flex items-center gap-[6px] text-[12px] text-[#717182]">
              核心用例数
              <input v-model.number="executionImportLimit" type="number" min="1" max="500" class="h-[32px] w-[76px] rounded-[8px] border border-black/10 px-[8px] text-[12px] text-[#0A0A0A]" />
            </label>
            <button
              type="button"
              class="inline-flex h-[32px] items-center justify-center gap-[6px] rounded-[8px] bg-[#008236] px-[12px] text-[13px] font-medium text-white disabled:bg-black/20"
              :disabled="isImportingExecutionResults"
              @click="importExecutionResults"
            >
              <RefreshCw v-if="isImportingExecutionResults" class="h-[14px] w-[14px] animate-spin" />
              <CheckCircle2 v-else class="h-[14px] w-[14px]" />
              {{ isImportingExecutionResults ? '写入中' : '写入执行结果' }}
            </button>
          </div>
        </div>
        <div v-if="executionImportMessage" class="mt-[10px] rounded-[8px] bg-[#F0FDF4] px-[10px] py-[8px] text-[12px] leading-[18px] text-[#166534]">{{ executionImportMessage }}</div>
      </div>
    </section>

    <section v-if="activeView === 'details' || activeView === 'import'" class="mt-[16px] grid grid-cols-1 gap-[16px]" :class="activeView === 'details' ? '2xl:grid-cols-[minmax(0,1.55fr)_minmax(360px,0.8fr)]' : ''">
      <div v-if="activeView === 'details'" class="rounded-[8px] border border-black/10 bg-white p-[18px]">
        <div class="flex flex-col gap-[14px] xl:flex-row xl:items-start xl:justify-between">
          <div>
            <div class="flex items-center gap-[8px] text-[15px] font-semibold leading-[22px] text-[#0A0A0A]">
              <BarChart3 class="h-[16px] w-[16px] text-[#155DFC]" />
              {{ currentDimension.label }}
            </div>
            <div class="mt-[4px] text-[12px] leading-[18px] text-[#717182]">当前展示 {{ currentRows.length }} 项，总计 {{ chartTotal }} 条</div>
          </div>

          <div class="grid grid-cols-1 gap-[8px] sm:grid-cols-3">
            <label class="flex flex-col gap-[5px]">
              <span class="text-[12px] leading-[16px] text-[#717182]">维度</span>
              <select v-model="selectedDimension" class="h-[34px] rounded-[8px] border border-black/10 bg-white px-[10px] text-[13px] text-[#0A0A0A]">
                <option v-for="item in dimensionOptions" :key="item.key" :value="item.key">{{ item.label }}</option>
              </select>
            </label>
            <label class="flex flex-col gap-[5px]">
              <span class="text-[12px] leading-[16px] text-[#717182]">图表</span>
              <select v-model="chartMode" class="h-[34px] rounded-[8px] border border-black/10 bg-white px-[10px] text-[13px] text-[#0A0A0A]">
                <option value="bar">柱状图</option>
                <option value="list">列表条形图</option>
              </select>
            </label>
            <label class="flex flex-col gap-[5px]">
              <span class="text-[12px] leading-[16px] text-[#717182]">TopN</span>
              <select v-model.number="topLimit" class="h-[34px] rounded-[8px] border border-black/10 bg-white px-[10px] text-[13px] text-[#0A0A0A]">
                <option v-for="item in topLimitOptions" :key="item" :value="item">Top {{ item }}</option>
              </select>
            </label>
          </div>
        </div>

        <div v-if="chartMode === 'bar'" class="mt-[20px] flex h-[300px] items-end gap-[10px] overflow-x-auto border-b border-l border-black/10 px-[8px] pb-[8px] pt-[10px]">
          <div v-for="[name, value] in currentRows" :key="name" class="flex h-full min-w-[56px] flex-1 flex-col items-center justify-end gap-[8px]">
            <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">{{ value }}</div>
            <div
              class="w-full rounded-t-[7px] transition-all"
              :style="{ height: percentWidth(value), backgroundColor: currentDimension.accent }"
            />
            <div class="line-clamp-2 min-h-[32px] w-full text-center text-[11px] leading-[16px] text-[#717182]" :title="name">{{ name }}</div>
          </div>
        </div>

        <div v-else class="mt-[16px] space-y-[10px]">
          <div v-for="[name, value] in currentRows" :key="name" class="grid grid-cols-[minmax(90px,220px)_1fr_74px] items-center gap-[10px]">
            <div class="truncate text-[13px] text-[#374151]" :title="name">{{ name }}</div>
            <div class="h-[12px] overflow-hidden rounded-full bg-[#EEF1F5]">
              <div class="h-full rounded-full" :style="{ width: percentWidth(value), backgroundColor: currentDimension.accent }" />
            </div>
            <div class="text-right text-[12px] text-[#717182]">{{ value }} · {{ percentText(value) }}</div>
          </div>
        </div>

        <div v-if="!currentRows.length" class="mt-[18px] rounded-[8px] bg-[#F6F7F9] px-[12px] py-[16px] text-[13px] text-[#717182]">暂无可展示数据</div>
      </div>

      <div v-if="activeView === 'import'" class="rounded-[8px] border border-black/10 bg-white p-[18px]">
        <div class="flex items-center gap-[8px] text-[15px] font-semibold leading-[22px] text-[#0A0A0A]">
          <UploadCloud class="h-[16px] w-[16px] text-[#155DFC]" />
          自助导入
        </div>
        <div class="mt-[14px] rounded-[8px] border border-black/10 bg-[#FAFAFC] p-[12px]">
          <label class="flex flex-wrap items-center justify-between gap-[10px] text-[12px] leading-[18px] text-[#717182]">
            <span class="font-medium text-[#374151]">1. 选择导入类型</span>
            <select
              v-model="importType"
              aria-label="选择导入类型"
              class="h-[34px] min-w-[180px] rounded-[8px] border border-black/10 bg-white px-[10px] text-[13px] font-medium text-[#0A0A0A]"
            >
              <option v-for="item in importOptions" :key="item.type" :value="item.type">{{ item.title }}</option>
            </select>
          </label>
          <div class="mt-[10px] text-[12px] leading-[18px] text-[#717182]">
            {{ selectedImportOption.description }}
          </div>
        </div>

        <div
          class="mt-[14px] flex flex-col gap-[10px]"
          @dragover.prevent
          @drop.prevent="onImportDrop"
        >
          <div class="rounded-[8px] border border-dashed border-black/20 bg-white px-[12px] py-[12px]">
            <input ref="fileInputRef" class="hidden" type="file" multiple :accept="selectedImportOption.accept" @change="onImportFileChange" />
            <input ref="directoryInputRef" class="hidden" type="file" multiple webkitdirectory :accept="selectedImportOption.accept" @change="onImportDirectoryChange" />
            <div class="mb-[8px] text-[12px] font-medium leading-[18px] text-[#374151]">2. 上传文件</div>
            <div class="flex flex-wrap items-center gap-[8px]">
              <button
                type="button"
                class="inline-flex h-[32px] items-center justify-center rounded-[8px] bg-[#155DFC] px-[12px] text-[13px] font-medium text-white"
                @click="fileInputRef?.click()"
              >
                选择文件
              </button>
              <button
                type="button"
                class="inline-flex h-[32px] items-center justify-center rounded-[8px] border border-black/10 bg-white px-[12px] text-[13px] font-medium text-[#0A0A0A] hover:bg-[#F9FAFB]"
                @click="showImportMoreActions = !showImportMoreActions"
              >
                更多
              </button>
            </div>
            <div v-if="showImportMoreActions" class="mt-[8px] flex flex-wrap gap-[8px]">
              <button
                type="button"
                class="inline-flex h-[30px] items-center justify-center rounded-[8px] border border-black/10 bg-white px-[10px] text-[12px] font-medium text-[#0A0A0A] hover:bg-[#F9FAFB]"
                @click="directoryInputRef?.click()"
              >
                选择目录
              </button>
              <button
                type="button"
                class="inline-flex h-[30px] items-center justify-center gap-[5px] rounded-[8px] border border-black/10 bg-white px-[10px] text-[12px] font-medium text-[#0A0A0A] hover:bg-[#F9FAFB]"
                @click="downloadImportTemplate"
              >
                <Download class="h-[13px] w-[13px]" />
                下载模板
              </button>
              <button
                type="button"
                class="inline-flex h-[30px] items-center justify-center rounded-[8px] border border-black/10 bg-white px-[10px] text-[12px] font-medium text-[#C10007] hover:bg-[#FEF2F2]"
                :disabled="!importQueue.length || isImporting"
                @click="clearImportQueue"
              >
                重置本次导入
              </button>
            </div>
            <div class="mt-[8px] text-[12px] leading-[18px] text-[#717182]">
              可一次选择多个文件，也可以把解压后的文件拖进来。当前支持：{{ selectedImportOption.accept }}
            </div>
            <div v-if="importQueue.length" class="mt-[8px] text-[12px] leading-[18px] text-[#717182]">
              已选择 {{ queueSummary.total }} 个，{{ queueSummary.ready }} 个可导入，{{ queueSummary.failed }} 个失败；当前：{{ importFileLabel }}
            </div>
          </div>

          <div v-if="isPreviewing || hasPreviewingQueue" class="rounded-[8px] border border-black/10 bg-white px-[12px] py-[10px] text-[12px] text-[#717182]">正在解析预览...</div>

          <div v-if="importQueue.length" class="max-h-[190px] overflow-auto rounded-[8px] border border-black/10 bg-white">
            <button
              v-for="item in importQueue"
              :key="item.id"
              type="button"
              class="flex w-full items-start justify-between gap-[10px] border-b border-black/5 px-[10px] py-[8px] text-left last:border-b-0 hover:bg-[#F9FAFB]"
              :class="activeImportId === item.id ? 'bg-[#EFF6FF]' : 'bg-white'"
              @click="selectQueueItem(item.id)"
            >
              <span class="min-w-0">
                <span class="block truncate text-[12px] font-medium text-[#0A0A0A]" :title="item.label">{{ item.label }}</span>
                <span class="mt-[2px] block truncate text-[11px] text-[#717182]">
                  {{ item.preview ? `识别 ${item.preview.totalRows} 行` : item.error || '等待解析' }}
                </span>
              </span>
              <span class="flex shrink-0 items-center gap-[6px]">
                <span class="rounded-full px-[7px] py-[2px] text-[11px]" :class="importQueueStatusClass(item.status)">
                  {{ importQueueStatusLabel(item.status) }}
                </span>
                <span
                  class="rounded-full px-[7px] py-[2px] text-[11px] text-[#717182] hover:bg-black/5"
                  @click.stop="removeQueueItem(item.id)"
                >
                  移除
                </span>
              </span>
            </button>
          </div>

          <div v-if="currentImportPreview" class="rounded-[8px] border border-black/10 bg-white">
            <div class="border-b border-black/10 px-[12px] py-[10px]">
              <div class="text-[13px] font-medium text-[#0A0A0A]">3. 字段映射并导入</div>
              <div class="mt-[2px] text-[12px] text-[#717182]">{{ currentImportPreview.fileName }} · 识别 {{ currentImportPreview.totalRows }} 行</div>
            </div>
            <div class="grid grid-cols-1 gap-[8px] px-[12px] py-[10px] sm:grid-cols-2">
              <label v-for="field in mappingFields" :key="field.key" class="flex flex-col gap-[5px]">
                <span class="text-[12px] text-[#717182]">{{ field.label }}{{ field.required ? ' *' : '' }}</span>
                <select
                  :value="currentImportMapping[field.key] || ''"
                  class="h-[32px] rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] text-[#0A0A0A]"
                  @change="updateCurrentMapping(field.key, ($event.target as HTMLSelectElement).value)"
                >
                  <option value="">不映射</option>
                  <option v-for="header in currentImportPreview.headers" :key="header" :value="header">{{ header }}</option>
                </select>
              </label>
            </div>
            <div v-if="currentImportPreview.warnings.length" class="mx-[12px] mb-[10px] rounded-[8px] bg-[#FFFBEB] px-[10px] py-[8px] text-[12px] leading-[16px] text-[#92400E]">
              {{ currentImportPreview.warnings.join('；') }}
            </div>
            <div v-if="currentImportPreview.sampleRows.length" class="max-h-[180px] overflow-auto border-t border-black/10">
              <table class="w-full min-w-[520px] text-left text-[12px]">
                <thead class="sticky top-0 bg-[#F6F7F9] text-[#717182]">
                  <tr>
                    <th v-for="field in mappingFields.slice(0, 4)" :key="field.key" class="px-[10px] py-[8px] font-medium">{{ field.label }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, index) in currentImportPreview.sampleRows" :key="index" class="border-t border-black/5">
                    <td v-for="field in mappingFields.slice(0, 4)" :key="field.key" class="max-w-[180px] truncate px-[10px] py-[8px] text-[#374151]" :title="mappedCell(row, field.key)">
                      {{ mappedCell(row, field.key) || '-' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <button
            type="button"
            class="inline-flex h-[36px] items-center justify-center gap-[6px] rounded-[8px] bg-[#155DFC] px-[14px] text-[14px] font-medium text-white disabled:cursor-not-allowed disabled:bg-black/20"
            :disabled="isImporting || isPreviewing || hasPreviewingQueue || !importableQueue.length"
            @click="handleImport"
          >
            <RefreshCw v-if="isImporting" class="h-[14px] w-[14px] animate-spin" />
            <UploadCloud v-else class="h-[14px] w-[14px]" />
            {{ isImporting ? '导入中' : '确认导入' }}
          </button>
        </div>

        <div v-if="importMessage" class="mt-[12px] flex items-start gap-[8px] rounded-[8px] border border-black/10 bg-[#FAFAFC] p-[10px] text-[13px] leading-[18px] text-[#374151]">
          <CheckCircle2 v-if="importResult" class="mt-[1px] h-[15px] w-[15px] shrink-0 text-[#008236]" />
          <AlertTriangle v-else class="mt-[1px] h-[15px] w-[15px] shrink-0 text-[#B45309]" />
          <span>{{ importMessage }}</span>
        </div>

        <div v-if="importErrors.length" class="mt-[10px] max-h-[180px] overflow-auto rounded-[8px] border border-black/10 bg-white">
          <div
            v-for="item in importErrors"
            :key="item.key"
            class="border-b border-black/5 px-[10px] py-[8px] last:border-b-0"
          >
            <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">{{ item.title }}</div>
            <div class="mt-[2px] text-[12px] leading-[16px] text-[#717182]">{{ item.message }}</div>
          </div>
        </div>

        <div class="mt-[14px] border-t border-black/10 pt-[12px]">
          <div class="flex items-center justify-between">
            <div class="text-[13px] font-medium text-[#0A0A0A]">最近导入</div>
            <button type="button" class="text-[12px] text-[#155DFC]" @click="loadImportHistory">刷新</button>
          </div>
          <div v-if="isLoadingImportHistory" class="mt-[10px] text-[12px] text-[#717182]">加载导入历史...</div>
          <div v-else-if="!importHistory.length" class="mt-[10px] rounded-[8px] bg-[#F6F7F9] px-[10px] py-[8px] text-[12px] text-[#717182]">暂无导入历史</div>
          <div v-else class="mt-[10px] space-y-[8px]">
            <div v-for="record in importHistory" :key="record.id" class="rounded-[8px] border border-black/10 px-[10px] py-[8px]">
              <div class="flex items-center justify-between gap-[8px]">
                <div class="min-w-0 truncate text-[12px] font-medium text-[#0A0A0A]" :title="record.fileName">{{ record.fileName }}</div>
                <div class="shrink-0 text-[11px]" :class="record.status === 'SUCCESS' ? 'text-[#008236]' : record.status === 'PARTIAL_SUCCESS' ? 'text-[#B45309]' : 'text-[#C10007]'">
                  {{ importHistoryStatusLabel(record.status) }}
                </div>
              </div>
              <div class="mt-[4px] text-[11px] leading-[15px] text-[#717182]">
                {{ record.importType }} · 成功 {{ record.successRows }} / 失败 {{ record.failedRows }} · {{ formatTime(record.createdAt) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section v-if="activeView === 'details'" class="mt-[16px] grid grid-cols-1 gap-[16px] xl:grid-cols-2">
      <div class="rounded-[8px] border border-black/10 bg-white p-[18px]">
        <h2 class="flex items-center gap-[8px] text-[15px] font-semibold leading-[22px] text-[#0A0A0A]">
          <GitBranch class="h-[16px] w-[16px] text-[#C2410C]" />
          缺陷聚类
        </h2>
        <div class="mt-[12px] space-y-[10px]">
          <div v-for="item in dashboard?.topDefectClusters || []" :key="item.clusterKey" class="rounded-[8px] border border-black/10 p-[12px]">
            <div class="flex items-center justify-between gap-[12px]">
              <div class="min-w-0 truncate text-[14px] font-medium text-[#0A0A0A]">{{ item.clusterKey }}</div>
              <div class="shrink-0 text-[13px] text-[#717182]">{{ item.count }} 个</div>
            </div>
            <div class="mt-[6px] text-[13px] leading-[18px] text-[#717182]">{{ item.rootCauseHint }}</div>
          </div>
        </div>
      </div>

      <div class="rounded-[8px] border border-black/10 bg-white p-[18px]">
        <h2 class="flex items-center gap-[8px] text-[15px] font-semibold leading-[22px] text-[#0A0A0A]">
          <ListFilter class="h-[16px] w-[16px] text-[#BE123C]" />
          风险提示
        </h2>
        <div class="mt-[12px] space-y-[10px]">
          <RouterLink
            v-for="item in dashboard?.topRiskHints || []"
            :key="item.defectId"
            :to="`/projects/${encodeURIComponent(projectId)}/defects/${encodeURIComponent(item.defectId)}`"
            class="block rounded-[8px] border border-black/10 p-[12px] hover:bg-[#F9FAFB]"
          >
            <div class="flex items-center justify-between gap-[12px]">
              <div class="min-w-0 truncate text-[14px] font-medium text-[#0A0A0A]">{{ item.title }}</div>
              <div class="shrink-0 text-[12px] text-[#B45309]">{{ item.severity }} · {{ item.riskScore }}</div>
            </div>
            <div class="mt-[6px] text-[13px] leading-[18px] text-[#717182]">{{ item.hint }}</div>
            <div class="mt-[6px] text-[12px] text-[#9CA3AF]">{{ item.status }} · {{ formatTime(item.updatedAt) }}</div>
          </RouterLink>
        </div>
      </div>
    </section>

    <section v-if="activeView === 'details'" class="mt-[16px] rounded-[8px] border border-black/10 bg-white p-[18px]">
      <h2 class="flex items-center gap-[8px] text-[15px] font-semibold leading-[22px] text-[#0A0A0A]">
        <Settings2 class="h-[16px] w-[16px] text-[#155DFC]" />
        样例用例
      </h2>
      <div class="mt-[12px] grid grid-cols-1 gap-[8px] xl:grid-cols-2">
        <div v-for="title in dashboard?.sampleTestcases || []" :key="title" class="truncate rounded-[8px] bg-[#F6F7F9] px-[12px] py-[10px] text-[13px] text-[#374151]" :title="title">
          {{ title }}
        </div>
      </div>
    </section>
  </main>
</template>
