import { authHeader, requestJson } from '@/lib/api/client'
import { createRequirementDoc, parseRequirementDocVersion, uploadRequirementDocVersion } from '@/lib/api/requirements'
import { importTestcases, type TestCaseImportData } from '@/lib/aiTestingPlatformApi'

export type TrialOperationClusterItem = {
  clusterKey: string
  count: number
  sampleTitles: string[]
  rootCauseHint: string
  confidence: number
}

export type TrialOperationRiskHint = {
  defectId: string
  title: string
  status: string
  severity: string
  updatedAt: number
  riskScore: number
  hint: string
}

export type TrialOperationAcceptanceSummary = {
  conclusion: string
  score: number
  level: 'PASS' | 'WARNING' | 'BLOCKED' | 'INSUFFICIENT'
  highlights: string[]
  risks: string[]
  nextActions: string[]
}

export type TrialOperationDashboardData = {
  metrics: Record<string, number>
  acceptanceSummary?: TrialOperationAcceptanceSummary
  testcasePriorityDistribution: Record<string, number>
  testcaseStatusDistribution: Record<string, number>
  testcaseTypeDistribution: Record<string, number>
  testcaseFeatureDistribution: Record<string, number>
  defectSeverityDistribution: Record<string, number>
  defectStatusDistribution: Record<string, number>
  topDefectClusters: TrialOperationClusterItem[]
  topRiskHints: TrialOperationRiskHint[]
  sampleTestcases: string[]
}

export type TrialOperationReportData = {
  title: string
  generatedAt: number
  markdown: string
  summary: TrialOperationAcceptanceSummary
}

export type TrialOperationReportSnapshot = {
  id: string
  title: string
  generatedAt: number
  score?: number | null
  level?: TrialOperationAcceptanceSummary['level'] | null
  createdAt?: number | null
}

export type TrialOperationReportSnapshotDetail = TrialOperationReportSnapshot & {
  markdown: string
  summary?: TrialOperationAcceptanceSummary | null
}

export type TrialOperationRequirementImportData = {
  docId: string
  versionId: string
  title: string
  parseStarted: boolean
}

export type TrialOperationDefectImportItem = {
  title: string
  description?: string | null
  severity?: string | null
  runId?: string | null
  caseRunId?: string | null
  testcaseId?: string | null
  source?: string | null
}

export type TrialOperationDefectImportData = {
  total: number
  success: number
  failed: number
  errors: Array<{ index: number; title?: string | null; error: string }>
}

export type TrialOperationImportResult =
  | { type: 'requirements'; data: TrialOperationRequirementImportData }
  | { type: 'testcases'; data: TestCaseImportData }
  | { type: 'defects'; data: TrialOperationDefectImportData }

export type TrialOperationImportType = 'requirements' | 'testcases' | 'defects'
export type TrialOperationImportStatus = 'SUCCESS' | 'PARTIAL_SUCCESS' | 'FAILED'

export type TrialOperationImportPreview = {
  fileName: string
  importType: TrialOperationImportType
  headers: string[]
  sampleRows: Array<Record<string, string>>
  totalRows: number
  suggestedMapping: Record<string, string>
  warnings: string[]
}

export type TrialOperationImportRecord = {
  id: string
  projectId?: string | null
  importType: TrialOperationImportType
  fileName: string
  status: TrialOperationImportStatus
  totalRows: number
  successRows: number
  failedRows: number
  summary?: string | null
  detail: Record<string, unknown>
  createdBy?: string | null
  createdAt: number
}

type PageData<T> = {
  page: number
  pageSize: number
  total: number
  items: T[]
}

const filenameWithoutExtension = (fileName: string) => {
  const normalized = String(fileName || '').trim()
  const lastDot = normalized.lastIndexOf('.')
  return lastDot > 0 ? normalized.slice(0, lastDot) : normalized || '导入文档'
}

const decodeText = async (file: File) => {
  const buffer = await file.arrayBuffer()
  const utf8 = new TextDecoder('utf-8').decode(buffer)
  if (!utf8.includes('\uFFFD')) return utf8.replace(/^\uFEFF/, '')
  try {
    return new TextDecoder('gb18030').decode(buffer).replace(/^\uFEFF/, '')
  } catch {
    return utf8.replace(/^\uFEFF/, '')
  }
}

const parseCsvLine = (line: string) => {
  const cells: string[] = []
  let current = ''
  let quoted = false
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index]
    const next = line[index + 1]
    if (char === '"' && quoted && next === '"') {
      current += '"'
      index += 1
    } else if (char === '"') {
      quoted = !quoted
    } else if (char === ',' && !quoted) {
      cells.push(current.trim())
      current = ''
    } else {
      current += char
    }
  }
  cells.push(current.trim())
  return cells
}

const parseCsvPreviewRows = async (file: File) => {
  const text = await decodeText(file)
  const lines = text.split(/\r?\n/).filter((line) => line.trim())
  const headers = parseCsvLine(lines[0] || '').map((item) => item.trim()).filter(Boolean)
  const rows = lines.slice(1).map((line) => {
    const cells = parseCsvLine(line)
    return Object.fromEntries(headers.map((header, index) => [header, cells[index] || '']))
  })
  return { headers, rows }
}

const normalizeHeader = (value: string) => String(value || '').trim().toLowerCase().replace(/\s+/g, '')

const findHeader = (headers: string[], candidates: string[]) => {
  const normalized = headers.map((header) => ({ header, key: normalizeHeader(header) }))
  for (const candidate of candidates) {
    const key = normalizeHeader(candidate)
    const exact = normalized.find((item) => item.key === key)
    if (exact) return exact.header
  }
  for (const candidate of candidates) {
    const key = normalizeHeader(candidate)
    const fuzzy = normalized.find((item) => item.key.includes(key) || key.includes(item.key))
    if (fuzzy) return fuzzy.header
  }
  return ''
}

const buildSuggestedMapping = (importType: TrialOperationImportType, headers: string[]) => {
  const mapping: Record<string, string> = {}
  if (importType === 'defects') {
    mapping.title = findHeader(headers, ['title', 'name', 'summary', '缺陷标题', '标题', '问题标题'])
    mapping.description = findHeader(headers, ['description', 'detail', 'desc', '缺陷描述', '描述', '详情'])
    mapping.severity = findHeader(headers, ['severity', 'priority', '严重级别', '严重程度', '优先级'])
    mapping.source = findHeader(headers, ['source', '来源', '文件来源'])
    return mapping
  }
  if (importType === 'testcases') {
    mapping.title = findHeader(headers, ['title', 'name', '用例标题', '标题', '测试点'])
    mapping.feature = findHeader(headers, ['feature', 'module', '模块', '功能模块', '所属模块'])
    mapping.priority = findHeader(headers, ['priority', '优先级'])
    mapping.type = findHeader(headers, ['type', '类型', '用例类型'])
    mapping.status = findHeader(headers, ['status', '状态'])
    return mapping
  }
  mapping.title = findHeader(headers, ['title', 'name', '需求标题', '标题'])
  mapping.module = findHeader(headers, ['module', 'feature', '模块', '功能模块'])
  return mapping
}

export async function previewTrialOperationImport(file: File, importType: TrialOperationImportType): Promise<TrialOperationImportPreview> {
  if (!file) throw new Error('请选择文件')
  if (importType === 'requirements') {
    const text = await decodeText(file)
    const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
    const title = lines.find((line) => line.startsWith('#'))?.replace(/^#+\s*/, '') || filenameWithoutExtension(file.name)
    return {
      fileName: file.name,
      importType,
      headers: ['title', 'content'],
      sampleRows: [{ title, content: lines.slice(0, 4).join(' ').slice(0, 160) }],
      totalRows: 1,
      suggestedMapping: { title: 'title', content: 'content' },
      warnings: []
    }
  }

  if (importType === 'defects' && file.name.toLowerCase().endsWith('.json')) {
    const raw = JSON.parse(await file.text()) as unknown
    const items = Array.isArray(raw) ? raw : (raw as { items?: unknown[] })?.items
    if (!Array.isArray(items)) throw new Error('缺陷 JSON 需要是数组，或包含 items 数组')
    const rows = items.map((item) => {
      const row = (item || {}) as Record<string, unknown>
      return Object.fromEntries(Object.entries(row).map(([key, value]) => [key, value == null ? '' : String(value)]))
    })
    const headers = Array.from(new Set(rows.flatMap((row) => Object.keys(row))))
    const mapping = buildSuggestedMapping(importType, headers)
    return {
      fileName: file.name,
      importType,
      headers,
      sampleRows: rows.slice(0, 5),
      totalRows: rows.length,
      suggestedMapping: mapping,
      warnings: mapping.title ? [] : ['未自动识别缺陷标题字段，请手动选择 title/name/summary 对应列']
    }
  }

  if (file.name.toLowerCase().endsWith('.xlsx')) {
    return {
      fileName: file.name,
      importType,
      headers: [],
      sampleRows: [],
      totalRows: 0,
      suggestedMapping: {},
      warnings: ['浏览器内暂不解析 XLSX 预览，确认导入时仍会交给后端导入器处理']
    }
  }

  const { headers, rows } = await parseCsvPreviewRows(file)
  const mapping = buildSuggestedMapping(importType, headers)
  const warnings: string[] = []
  if (!headers.length) warnings.push('未识别到表头，请确认文件第一行为字段名')
  if (importType === 'testcases' && !mapping.title) warnings.push('未自动识别用例标题字段，请手动选择')
  return {
    fileName: file.name,
    importType,
    headers,
    sampleRows: rows.slice(0, 5),
    totalRows: rows.length,
    suggestedMapping: mapping,
    warnings
  }
}

export async function getTrialOperationDashboard(projectId: string) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('projectId 不能为空')
  return requestJson<TrialOperationDashboardData>(
    `/api/projects/${encodeURIComponent(pid)}/dashboard/trial-operation`,
    { method: 'GET', headers: authHeader() }
  )
}

export async function getTrialOperationReport(projectId: string) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('projectId 不能为空')
  return requestJson<TrialOperationReportData>(
    `/api/projects/${encodeURIComponent(pid)}/dashboard/trial-operation/report`,
    { method: 'GET', headers: authHeader() }
  )
}

export async function saveTrialOperationReportSnapshot(
  projectId: string,
  payload: Pick<TrialOperationReportData, 'title' | 'generatedAt' | 'markdown' | 'summary'>
) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  return requestJson<TrialOperationReportSnapshotDetail>(
    `/api/projects/${encodeURIComponent(pid)}/dashboard/trial-operation/report/snapshots`,
    {
      method: 'POST',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }
  )
}

export async function getTrialOperationReportSnapshots(projectId: string, pageSize = 5) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  return requestJson<PageData<TrialOperationReportSnapshot>>(
    `/api/projects/${encodeURIComponent(pid)}/dashboard/trial-operation/report/snapshots?page=1&pageSize=${pageSize}`,
    { method: 'GET', headers: authHeader() }
  )
}

export async function getTrialOperationReportSnapshot(projectId: string, snapshotId: string) {
  const pid = String(projectId || '').trim()
  const sid = String(snapshotId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!sid) throw new Error('快照 ID 不能为空')
  return requestJson<TrialOperationReportSnapshotDetail>(
    `/api/projects/${encodeURIComponent(pid)}/dashboard/trial-operation/report/snapshots/${encodeURIComponent(sid)}`,
    { method: 'GET', headers: authHeader() }
  )
}

export async function importTrialOperationRequirementDoc(projectId: string, file: File) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!file) throw new Error('请选择需求文档')
  const title = filenameWithoutExtension(file.name)
  const doc = await createRequirementDoc(pid, {
    title,
    status: 'DRAFT',
    tags: ['trial-operation-import'],
    sourceType: 'PRD'
  })
  const version = await uploadRequirementDocVersion(pid, doc.id, {
    file,
    changeSummary: '试运行看板自助导入',
    effectiveScope: '当前项目'
  })
  let parseStarted = false
  try {
    await parseRequirementDocVersion(pid, doc.id, version.id)
    parseStarted = true
  } catch {
    parseStarted = false
  }
  return {
    docId: doc.id,
    versionId: version.id,
    title,
    parseStarted
  }
}

export async function importTrialOperationTestcases(projectId: string, file: File) {
  return importTestcases({ projectId, file, mode: 'partial' })
}

export async function importTrialOperationDefects(projectId: string, file: File) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  if (!file) throw new Error('请选择缺陷 JSON 文件')
  let payload: unknown
  try {
    payload = JSON.parse(await file.text())
  } catch (error) {
    throw new Error('缺陷文件不是合法 JSON')
  }
  const items = Array.isArray(payload) ? payload : (payload as { items?: unknown[] })?.items
  if (!Array.isArray(items) || items.length === 0) {
    throw new Error('缺陷 JSON 需要是数组，或包含 items 数组')
  }
  const normalizedItems = items.map((item) => {
    const row = (item || {}) as Record<string, unknown>
    const title = String(row.title || row.name || row.summary || '').trim()
    if (!title) throw new Error('缺陷 JSON 中每条记录都需要 title/name/summary')
    return {
      title,
      description: row.description ? String(row.description) : row.detail ? String(row.detail) : undefined,
      severity: row.severity ? String(row.severity).toUpperCase() : row.priority ? String(row.priority).toUpperCase() : 'P2',
      runId: row.runId ? String(row.runId) : undefined,
      caseRunId: row.caseRunId ? String(row.caseRunId) : undefined,
      testcaseId: row.testcaseId ? String(row.testcaseId) : undefined,
      source: row.source ? String(row.source) : file.name
    } satisfies TrialOperationDefectImportItem
  })
  return requestJson<TrialOperationDefectImportData>(
    `/api/projects/${encodeURIComponent(pid)}/defects/import`,
    {
      method: 'POST',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: normalizedItems })
    }
  )
}

export async function getTrialOperationImportRecords(projectId: string, pageSize = 6) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  return requestJson<PageData<TrialOperationImportRecord>>(
    `/api/projects/${encodeURIComponent(pid)}/platform/trial-operation/import-records?page=1&pageSize=${pageSize}`,
    { method: 'GET', headers: authHeader() }
  )
}

export async function recordTrialOperationImport(
  projectId: string,
  payload: {
    importType: TrialOperationImportType
    fileName: string
    status: TrialOperationImportStatus
    totalRows: number
    successRows: number
    failedRows: number
    summary?: string | null
    detail?: Record<string, unknown>
  }
) {
  const pid = String(projectId || '').trim()
  if (!pid) throw new Error('项目 ID 不能为空')
  return requestJson<TrialOperationImportRecord>(
    `/api/projects/${encodeURIComponent(pid)}/platform/trial-operation/import-records`,
    {
      method: 'POST',
      headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...payload, detail: payload.detail || {} })
    }
  )
}
