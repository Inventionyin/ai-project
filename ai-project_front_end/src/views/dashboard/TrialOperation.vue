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
  TestTube2,
  UploadCloud
} from 'lucide-vue-next'
import {
  getTrialOperationDashboard,
  getTrialOperationImportRecords,
  getTrialOperationReport,
  getTrialOperationReportSnapshot,
  getTrialOperationReportSnapshots,
  importTrialOperationDefects,
  importTrialOperationRequirementDoc,
  importTrialOperationTestcases,
  previewTrialOperationImport,
  recordTrialOperationImport,
  saveTrialOperationReportSnapshot,
  type TrialOperationDashboardData,
  type TrialOperationAcceptanceSummary,
  type TrialOperationImportPreview,
  type TrialOperationImportRecord,
  type TrialOperationImportResult,
  type TrialOperationReportData,
  type TrialOperationReportSnapshot
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

const route = useRoute()
const isLoading = ref(false)
const errorMessage = ref('')
const dashboard = ref<TrialOperationDashboardData | null>(null)
const chartMode = ref<ChartMode>('bar')
const selectedDimension = ref<DimensionKey>('testcasePriorityDistribution')
const topLimit = ref(10)
const importType = ref<ImportType>('testcases')
const importFile = ref<File | null>(null)
const isImporting = ref(false)
const importMessage = ref('')
const importResult = ref<TrialOperationImportResult | null>(null)
const fileInputKey = ref(0)
const importPreview = ref<TrialOperationImportPreview | null>(null)
const importMapping = ref<Record<string, string>>({})
const isPreviewing = ref(false)
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

const projectId = computed(() => String(route.params.projectId || '').trim())
const storageKey = computed(() => `trial-operation-view:${projectId.value}`)
const metrics = computed(() => dashboard.value?.metrics || {})

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
  { type: 'defects', title: '缺陷数据', accept: '.json', description: '支持 JSON 数组或 { items: [] }，字段可用 title、description、severity' }
]

const currentDimension = computed(() => dimensionOptions.find((item) => item.key === selectedDimension.value) || dimensionOptions[0])
const currentRows = computed(() => entries(dashboard.value?.[selectedDimension.value], topLimit.value))
const chartTotal = computed(() => currentRows.value.reduce((sum, [, value]) => sum + value, 0))
const maxRowValue = computed(() => Math.max(...currentRows.value.map(([, value]) => value), 1))
const selectedImportOption = computed(() => importOptions.find((item) => item.type === importType.value) || importOptions[0])
const importFileLabel = computed(() => {
  if (!importFile.value) return '未选择文件'
  const kb = Math.max(1, Math.round(importFile.value.size / 1024))
  return `${importFile.value.name}（${kb} KB）`
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

const metricLabelMap: Record<string, string> = {
  requirementDocs: '需求文档',
  testcases: '测试用例',
  defects: '缺陷记录',
  defectClusters: '缺陷聚类',
  riskHints: '风险提示'
}

const topLimitOptions = [5, 10, 16, 24]

const percentWidth = (value: number) => {
  return `${Math.max(3, Math.round((value / maxRowValue.value) * 100))}%`
}

const percentText = (value: number) => {
  if (!chartTotal.value) return '0%'
  return `${Math.round((value / chartTotal.value) * 100)}%`
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
    '',
    '## 已接入真实数据',
    ...(metricLines.length ? metricLines : ['- 暂无数据']),
    '',
    '## 已完成的平台能力',
    '- 真实需求、用例、缺陷数据导入与可视化',
    '- 维度可切换的柱状图/列表看板',
    '- 验收结论自动汇总、报告生成、复制与下载',
    '- 验收报告快照归档、历史查看、复制与下载',
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

const copyReport = async () => {
  const text = reportMarkdown.value.trim()
  if (!text) {
    reportMessage.value = '请先生成报告'
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    reportMessage.value = '报告内容已复制'
  } catch {
    try {
      fallbackCopyText(text)
      reportMessage.value = '报告内容已复制'
    } catch {
      reportMessage.value = '复制失败，请手动复制'
    }
  }
}

const copyMarkdownText = async (text: string, successMessage: string) => {
  const normalized = text.trim()
  if (!normalized) {
    reportMessage.value = '暂无可复制内容'
    return
  }
  try {
    await navigator.clipboard.writeText(normalized)
    reportMessage.value = successMessage
  } catch {
    try {
      fallbackCopyText(normalized)
      reportMessage.value = successMessage
    } catch {
      reportMessage.value = '复制失败，请手动复制'
    }
  }
}

const copyDeliveryNote = async () => {
  await copyMarkdownText(deliveryNoteMarkdown.value, '验收汇报稿已复制')
  deliveryNoteMessage.value = '验收汇报稿已复制'
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
  importFile.value = null
  importMessage.value = ''
  importResult.value = null
  importPreview.value = null
  importMapping.value = {}
  fileInputKey.value += 1
}

const onImportFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0] || null
  importMessage.value = ''
  importResult.value = null
  importPreview.value = null
  importMapping.value = {}
  if (!file) {
    importFile.value = null
    return
  }
  const extension = `.${String(file.name || '').split('.').pop()?.toLowerCase() || ''}`
  const allowList = selectedImportOption.value.accept.split(',').map((item) => item.trim().toLowerCase())
  if (!allowList.includes(extension)) {
    importFile.value = null
    input.value = ''
    importMessage.value = `当前类型只支持 ${selectedImportOption.value.accept}`
    return
  }
  importFile.value = file
  void buildImportPreview(file)
}

const buildImportPreview = async (file: File) => {
  isPreviewing.value = true
  try {
    const preview = await previewTrialOperationImport(file, importType.value)
    importPreview.value = preview
    importMapping.value = { ...preview.suggestedMapping }
    if (preview.warnings.length) {
      importMessage.value = preview.warnings[0]
    }
  } catch (error) {
    importPreview.value = null
    importMapping.value = {}
    importMessage.value = error instanceof Error ? error.message : '预览失败'
  } finally {
    isPreviewing.value = false
  }
}

const mappedCell = (row: Record<string, string>, key: string) => {
  const header = importMapping.value[key]
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
    total: importPreview.value?.totalRows || importResult.value.data.importedCount + importResult.value.data.failedCount,
    success: importResult.value.data.importedCount,
    failed: importResult.value.data.failedCount
  }
}

const handleImport = async () => {
  if (!projectId.value) return
  if (!importFile.value) {
    importMessage.value = '请先选择要导入的文件'
    return
  }
  isImporting.value = true
  importMessage.value = ''
  importResult.value = null
  const importingFile = importFile.value
  try {
    if (importType.value === 'requirements') {
      const data = await importTrialOperationRequirementDoc(projectId.value, importingFile)
      importResult.value = { type: 'requirements', data }
      importMessage.value = data.parseStarted ? '需求文档已导入，解析任务已触发' : '需求文档已导入，解析可在文档中心继续'
    } else if (importType.value === 'defects') {
      const data = await importTrialOperationDefects(projectId.value, importingFile)
      importResult.value = { type: 'defects', data }
      importMessage.value = `缺陷导入完成：成功 ${data.success} 条，失败 ${data.failed} 条`
    } else {
      const data = await importTrialOperationTestcases(projectId.value, importingFile)
      importResult.value = { type: 'testcases', data }
      importMessage.value = `用例导入完成：成功 ${data.importedCount} 条，失败 ${data.failedCount} 条`
    }
    const counts = importResultCounts()
    const status = counts.failed === 0 ? 'SUCCESS' : counts.success > 0 ? 'PARTIAL_SUCCESS' : 'FAILED'
    await recordTrialOperationImport(projectId.value, {
      importType: importType.value,
      fileName: importingFile.name,
      status,
      totalRows: counts.total || importPreview.value?.totalRows || 0,
      successRows: counts.success,
      failedRows: counts.failed,
      summary: importMessage.value,
      detail: {
        previewRows: importPreview.value?.sampleRows.length || 0,
        mapping: importMapping.value,
        warnings: importPreview.value?.warnings || []
      }
    })
    importFile.value = null
    importPreview.value = null
    importMapping.value = {}
    fileInputKey.value += 1
    await loadDashboard()
    await loadImportHistory()
  } catch (error) {
    importMessage.value = error instanceof Error ? error.message : '导入失败'
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
      'defects-import-template.json',
      JSON.stringify(
        {
          items: [
            {
              title: '登录失败时错误提示不清晰',
              description: '输入错误密码后提示文案不明确，需要给出具体失败原因或操作建议。',
              severity: 'P1',
              source: 'manual-import'
            }
          ]
        },
        null,
        2
      ),
      'application/json;charset=utf-8'
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

    <section class="mb-[16px] rounded-[8px] border border-black/10 bg-white p-[14px] md:p-[16px]">
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

    <section class="grid grid-cols-1 gap-[12px] sm:grid-cols-2 xl:grid-cols-5">
      <div v-for="card in metricCards" :key="card.label" class="rounded-[8px] border border-black/10 bg-white p-[16px]">
        <div class="flex items-center justify-between">
          <div class="text-[12px] leading-[16px] text-[#717182]">{{ card.label }}</div>
          <div class="flex h-[30px] w-[30px] items-center justify-center rounded-[8px]" :class="card.tone">
            <component :is="card.icon" class="h-[15px] w-[15px]" />
          </div>
        </div>
        <div class="mt-[12px] text-[24px] font-semibold leading-[32px] text-[#0A0A0A]">{{ card.value }}</div>
      </div>
    </section>

    <section class="mt-[16px] grid grid-cols-1 gap-[16px] 2xl:grid-cols-[minmax(0,1.55fr)_minmax(360px,0.8fr)]">
      <div class="rounded-[8px] border border-black/10 bg-white p-[18px]">
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

      <div class="rounded-[8px] border border-black/10 bg-white p-[18px]">
        <div class="flex items-center gap-[8px] text-[15px] font-semibold leading-[22px] text-[#0A0A0A]">
          <UploadCloud class="h-[16px] w-[16px] text-[#155DFC]" />
          自助导入
        </div>
        <div class="mt-[14px] grid grid-cols-3 gap-[8px]">
          <button
            v-for="item in importOptions"
            :key="item.type"
            type="button"
            class="h-[34px] rounded-[8px] border px-[10px] text-[13px] font-medium"
            :class="importType === item.type ? 'border-[#155DFC] bg-[#EFF6FF] text-[#155DFC]' : 'border-black/10 bg-white text-[#374151]'"
            @click="importType = item.type"
          >
            {{ item.title }}
          </button>
        </div>

        <div class="mt-[14px] rounded-[8px] bg-[#F6F7F9] p-[12px] text-[12px] leading-[18px] text-[#717182]">
          {{ selectedImportOption.description }}
        </div>

        <div class="mt-[14px] flex flex-col gap-[10px]">
          <button
            type="button"
            class="inline-flex h-[34px] items-center justify-center gap-[6px] rounded-[8px] border border-black/10 bg-white px-[12px] text-[13px] font-medium text-[#0A0A0A] hover:bg-[#F9FAFB]"
            @click="downloadImportTemplate"
          >
            <Download class="h-[14px] w-[14px]" />
            下载当前模板
          </button>

          <label class="flex min-h-[82px] cursor-pointer flex-col justify-center rounded-[8px] border border-dashed border-black/20 bg-white px-[12px] py-[12px]">
            <input :key="fileInputKey" class="hidden" type="file" :accept="selectedImportOption.accept" @change="onImportFileChange" />
            <span class="text-[13px] font-medium leading-[18px] text-[#0A0A0A]">选择文件</span>
            <span class="mt-[4px] break-all text-[12px] leading-[18px] text-[#717182]">{{ importFileLabel }}</span>
          </label>

          <div v-if="isPreviewing" class="rounded-[8px] border border-black/10 bg-white px-[12px] py-[10px] text-[12px] text-[#717182]">正在解析预览...</div>

          <div v-if="importPreview" class="rounded-[8px] border border-black/10 bg-white">
            <div class="border-b border-black/10 px-[12px] py-[10px]">
              <div class="text-[13px] font-medium text-[#0A0A0A]">导入前预览</div>
              <div class="mt-[2px] text-[12px] text-[#717182]">{{ importPreview.fileName }} · 识别 {{ importPreview.totalRows }} 行</div>
            </div>
            <div class="grid grid-cols-1 gap-[8px] px-[12px] py-[10px] sm:grid-cols-2">
              <label v-for="field in mappingFields" :key="field.key" class="flex flex-col gap-[5px]">
                <span class="text-[12px] text-[#717182]">{{ field.label }}{{ field.required ? ' *' : '' }}</span>
                <select v-model="importMapping[field.key]" class="h-[32px] rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] text-[#0A0A0A]">
                  <option value="">不映射</option>
                  <option v-for="header in importPreview.headers" :key="header" :value="header">{{ header }}</option>
                </select>
              </label>
            </div>
            <div v-if="importPreview.warnings.length" class="mx-[12px] mb-[10px] rounded-[8px] bg-[#FFFBEB] px-[10px] py-[8px] text-[12px] leading-[16px] text-[#92400E]">
              {{ importPreview.warnings.join('；') }}
            </div>
            <div v-if="importPreview.sampleRows.length" class="max-h-[180px] overflow-auto border-t border-black/10">
              <table class="w-full min-w-[520px] text-left text-[12px]">
                <thead class="sticky top-0 bg-[#F6F7F9] text-[#717182]">
                  <tr>
                    <th v-for="field in mappingFields.slice(0, 4)" :key="field.key" class="px-[10px] py-[8px] font-medium">{{ field.label }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, index) in importPreview.sampleRows" :key="index" class="border-t border-black/5">
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
            :disabled="isImporting || isPreviewing"
            @click="handleImport"
          >
            <RefreshCw v-if="isImporting" class="h-[14px] w-[14px] animate-spin" />
            <UploadCloud v-else class="h-[14px] w-[14px]" />
            {{ isImporting ? '导入中' : '开始导入' }}
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

    <section class="mt-[16px] grid grid-cols-1 gap-[16px] xl:grid-cols-2">
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
            :to="`/projects/${projectId}/defects/${item.defectId}`"
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

    <section class="mt-[16px] rounded-[8px] border border-black/10 bg-white p-[18px]">
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
