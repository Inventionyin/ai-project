import { expect, test, type APIRequestContext } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const runRealE2E = process.env.WEITESTING_REAL_E2E === '1'
const apiBaseUrl = process.env.WEITESTING_API_BASE_URL || 'https://api.evanshine.me'

const dataRoot = process.env.WEITESTING_REAL_DATA_ROOT || 'D:\\OtherProject\\NewTestPlatform'
const requirementDir = path.join(dataRoot, 'requirement_analysis', 'requirement_analysis')
const testcaseFile = path.join(requirementDir, 'case_repository', 'case_repository.xlsx')
const defectDir = path.join(dataRoot, 'bug数量', 'bug数量')
const hasRealBusinessData = fs.existsSync(requirementDir) && fs.existsSync(testcaseFile) && fs.existsSync(defectDir)

type ApiEnvelope<T> = {
  code?: number
  message?: string
  data?: T
  requestId?: string
}

type DefectImportItem = {
  title: string
  description?: string
  severity?: string
  source?: string
}

async function expectApiOk<T>(responsePromise: Promise<import('@playwright/test').APIResponse>, label: string) {
  const response = await responsePromise
  const payload = (await response.json().catch(() => ({}))) as ApiEnvelope<T>
  expect(response.ok(), `${label} HTTP failed: ${response.status()} ${JSON.stringify(payload)}`).toBeTruthy()
  expect(payload.code, `${label} business failed: ${JSON.stringify(payload)}`).toBe(0)
  expect(payload.data, `${label} missing data`).toBeTruthy()
  return payload.data as T
}

async function postJson<T>(request: APIRequestContext, pathName: string, token: string | null, body: unknown, label: string) {
  return expectApiOk<T>(
    request.post(`${apiBaseUrl}${pathName}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      data: body
    }),
    label
  )
}

async function getJson<T>(request: APIRequestContext, pathName: string, token: string, label: string) {
  return expectApiOk<T>(
    request.get(`${apiBaseUrl}${pathName}`, {
      headers: { Authorization: `Bearer ${token}` }
    }),
    label
  )
}

async function recordImport(
  request: APIRequestContext,
  token: string,
  projectId: string,
  payload: {
    importType: 'requirements' | 'testcases' | 'defects'
    fileName: string
    status: 'SUCCESS' | 'PARTIAL_SUCCESS' | 'FAILED'
    totalRows: number
    successRows: number
    failedRows: number
    summary: string
    detail?: Record<string, unknown>
  }
) {
  return postJson(
    request,
    `/api/projects/${projectId}/platform/trial-operation/import-records`,
    token,
    { ...payload, detail: payload.detail || {} },
    `record ${payload.importType} import`
  )
}

function listRequirementFiles() {
  return fs
    .readdirSync(requirementDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith('.md') && !entry.name.startsWith('._'))
    .map((entry) => path.join(requirementDir, entry.name))
    .sort((a, b) => path.basename(a).localeCompare(path.basename(b), 'zh-CN'))
}

function listDefectFiles() {
  return fs
    .readdirSync(defectDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith('.md') && !entry.name.startsWith('._'))
    .map((entry) => path.join(defectDir, entry.name))
    .sort((a, b) => path.basename(a).localeCompare(path.basename(b), 'zh-CN'))
}

function stripExtension(fileName: string) {
  return path.basename(fileName).replace(/\.[^.]+$/, '')
}

function decodeText(filePath: string) {
  return fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, '')
}

function parseMarkdownTableLine(line: string) {
  const trimmed = line.trim()
  if (!trimmed.startsWith('|') || !trimmed.endsWith('|')) return []
  return trimmed
    .slice(1, -1)
    .split('|')
    .map((cell) => cell.trim())
}

function isMarkdownMetadataLine(line: string) {
  const trimmed = line.trim()
  if (!trimmed) return true
  if (/^-{3,}$/.test(trimmed)) return true
  if (/^\*\*[^*]+?\*\*\s*[:：]/.test(trimmed)) return true
  if (/^_{2}[^_]+?_{2}\s*[:：]/.test(trimmed)) return true
  return false
}

function isValidMarkdownDefectTitle(value: string) {
  const title = String(value || '').trim()
  if (!title) return false
  if (/^-{2,}$/.test(title)) return false
  if (/^\*{1,2}[^*]+?\*{1,2}\s*[:：]/.test(title)) return false
  if (/^_+[^_]+?_+\s*[:：]/.test(title)) return false
  if (/^(优先级|状态|缺陷标题|标题|测试id)$/i.test(title)) return false
  return true
}

function normalizeDefectSeverity(value?: string | null) {
  const raw = String(value || '').trim().toUpperCase()
  if (/^P[0-4]$/.test(raw)) return raw
  if (['BLOCKER', 'CRITICAL'].includes(raw)) return 'P0'
  if (['HIGH', 'MAJOR', '严重'].includes(raw)) return 'P1'
  if (['MEDIUM', 'NORMAL', '一般'].includes(raw)) return 'P2'
  if (['LOW', 'MINOR', '轻微'].includes(raw)) return 'P3'
  return 'P2'
}

function parseMarkdownDefectRows(filePath: string): DefectImportItem[] {
  const fileName = path.basename(filePath)
  const text = decodeText(filePath)
  const rows: DefectImportItem[] = []
  let tableHeaders: string[] = []
  let currentSection = ''

  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim()
    if (!line) continue
    if (isMarkdownMetadataLine(line)) continue

    const sectionMatch = line.match(/^#{1,6}\s+(.+)$/)
    if (sectionMatch) {
      currentSection = sectionMatch[1].trim()
      continue
    }

    const cells = parseMarkdownTableLine(line)
    if (cells.length) {
      const isSeparator = cells.every((cell) => /^:?-{3,}:?$/.test(cell))
      if (isSeparator) continue
      if (!tableHeaders.length || cells.includes('缺陷标题') || cells.includes('标题')) {
        tableHeaders = cells
        continue
      }
      if (tableHeaders.length && cells.length >= tableHeaders.length) {
        const row = Object.fromEntries(tableHeaders.map((header, index) => [header, cells[index] || '']))
        const title = row['缺陷标题'] || row['标题'] || row.title || row.summary || ''
        if (isValidMarkdownDefectTitle(title)) {
          rows.push({
            title,
            description: [currentSection, row['负责人'] ? `负责人：${row['负责人']}` : '', row['状态'] ? `状态：${row['状态']}` : '']
              .filter(Boolean)
              .join('；'),
            severity: normalizeDefectSeverity(row['优先级'] || row['严重级别'] || row.priority || row.severity),
            source: fileName
          })
        }
      }
      continue
    }

    const bulletMatch = line.match(/^[-*]\s*(.+?)(?:\s*[（(]\s*执行者\s*[:：]\s*([^,，)）]+)\s*[,，]\s*状态\s*[:：]\s*([^)）]+)\s*[)）])?\s*$/)
    if (bulletMatch) {
      const title = bulletMatch[1].trim()
      if (isValidMarkdownDefectTitle(title)) {
        rows.push({
          title,
          description: [currentSection, bulletMatch[2] ? `执行者：${bulletMatch[2].trim()}` : '', bulletMatch[3] ? `状态：${bulletMatch[3].trim()}` : '']
            .filter(Boolean)
            .join('；'),
          severity: 'P2',
          source: fileName
        })
      }
    }
  }

  return rows
}

test.describe('real business data acceptance flow', () => {
  test.skip(!runRealE2E, 'Set WEITESTING_REAL_E2E=1 to import real business data into the configured environment.')
  test.skip(!hasRealBusinessData, `Set WEITESTING_REAL_DATA_ROOT to a directory containing requirement_analysis, case_repository.xlsx, and bug数量. Current root: ${dataRoot}`)

  test('imports real requirements, cases, defects and captures acceptance screens', async ({ page, request }, testInfo) => {
    test.setTimeout(240_000)

    const health = await request.get(`${apiBaseUrl}/health`)
    expect(health.ok(), `Backend health check failed at ${apiBaseUrl}/health`).toBeTruthy()

    const suffix = `${Date.now()}${Math.floor(Math.random() * 1000)}`.slice(-10)
    const username = `accept_${suffix}`
    const phone = `13${suffix.slice(0, 9)}`
    const password = 'RealE2e123'
    const projectName = `真实业务数据验收 ${suffix}`

    const registered = await postJson<{ userId: string }>(
      request,
      '/api/auth/register',
      null,
      { phone, username, password, confirmPassword: password, captcha: '123456' },
      'register acceptance user'
    )

    const login = await postJson<{ accessToken: string; expiresIn: number }>(
      request,
      '/api/auth/login',
      null,
      { username, password },
      'login acceptance user'
    )
    const token = login.accessToken

    const project = await postJson<{ id: string }>(
      request,
      '/api/projects',
      token,
      {
        name: projectName,
        description: '由 Playwright 真实业务数据验收脚本创建，用于导入需求、用例、缺陷并生成验收快照。',
        ownerId: registered.userId
      },
      'create acceptance project'
    )

    const requirementFiles = listRequirementFiles()
    expect(requirementFiles.length, 'expected real requirement markdown files').toBeGreaterThan(0)
    for (const filePath of requirementFiles) {
      const title = stripExtension(filePath).slice(0, 100)
      const doc = await postJson<{ id: string }>(
        request,
        `/api/projects/${project.id}/requirements/docs`,
        token,
        {
          title,
          sourceType: 'PRD',
          status: 'DRAFT',
          tags: ['real-business-data', 'playwright-acceptance']
        },
        `create requirement doc ${title}`
      )
      const version = await expectApiOk<{ id: string }>(
        request.post(`${apiBaseUrl}/api/projects/${project.id}/requirements/docs/${doc.id}/versions`, {
          headers: { Authorization: `Bearer ${token}` },
          multipart: {
            file: {
              name: path.basename(filePath),
              mimeType: 'text/markdown',
              buffer: fs.readFileSync(filePath)
            },
            changeSummary: 'Playwright 真实业务数据验收导入',
            effectiveScope: '真实业务数据验收'
          }
        }),
        `upload requirement version ${title}`
      )
      await postJson(
        request,
        `/api/projects/${project.id}/requirements/docs/${doc.id}/versions/${version.id}/parse`,
        token,
        {},
        `parse requirement doc ${title}`
      )
    }
    await recordImport(request, token, project.id, {
      importType: 'requirements',
      fileName: 'requirement_analysis/*.md',
      status: 'SUCCESS',
      totalRows: requirementFiles.length,
      successRows: requirementFiles.length,
      failedRows: 0,
      summary: `需求文档导入完成：${requirementFiles.length} 份`,
      detail: { files: requirementFiles.map((item) => path.basename(item)) }
    })

    const testcaseImport = await expectApiOk<{ importedCount: number; failedCount: number; errors: unknown[] }>(
      request.post(`${apiBaseUrl}/api/testcases/import`, {
        headers: { Authorization: `Bearer ${token}` },
        multipart: {
          projectId: project.id,
          mode: 'partial',
          file: {
            name: 'case_repository.xlsx',
            mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            buffer: fs.readFileSync(testcaseFile)
          }
        }
      }),
      'import real testcase repository'
    )
    await recordImport(request, token, project.id, {
      importType: 'testcases',
      fileName: 'case_repository.xlsx',
      status: testcaseImport.failedCount > 0 ? 'PARTIAL_SUCCESS' : 'SUCCESS',
      totalRows: testcaseImport.importedCount + testcaseImport.failedCount,
      successRows: testcaseImport.importedCount,
      failedRows: testcaseImport.failedCount,
      summary: `用例导入完成：成功 ${testcaseImport.importedCount} 条，失败 ${testcaseImport.failedCount} 条`,
      detail: { errors: testcaseImport.errors.slice(0, 20) }
    })
    expect(testcaseImport.importedCount, 'expected imported real testcases').toBeGreaterThan(0)

    const defectFiles = listDefectFiles()
    const defectItems = defectFiles.flatMap((filePath) => parseMarkdownDefectRows(filePath))
    expect(defectItems.length, 'expected parsed real defects').toBeGreaterThan(0)
    const defectImport = await postJson<{ total: number; success: number; failed: number; errors: unknown[] }>(
      request,
      `/api/projects/${project.id}/defects/import`,
      token,
      { items: defectItems },
      'import real defects'
    )
    await recordImport(request, token, project.id, {
      importType: 'defects',
      fileName: 'bug数量/*.md',
      status: defectImport.failed > 0 ? 'PARTIAL_SUCCESS' : 'SUCCESS',
      totalRows: defectImport.total,
      successRows: defectImport.success,
      failedRows: defectImport.failed,
      summary: `缺陷导入完成：成功 ${defectImport.success} 条，失败 ${defectImport.failed} 条`,
      detail: { files: defectFiles.map((item) => path.basename(item)), errors: defectImport.errors.slice(0, 20) }
    })
    expect(defectImport.success, 'expected imported real defects').toBeGreaterThan(0)

    const suggestions = await postJson<{ batchId: string; items: Array<{ id: string; canApply: boolean }> }>(
      request,
      `/api/projects/${project.id}/dashboard/trial-operation/governance/suggestions`,
      token,
      {},
      'generate governance suggestions'
    )
    const suggestionIds = suggestions.items.filter((item) => item.canApply).slice(0, 10).map((item) => item.id)
    if (suggestionIds.length) {
      await postJson(
        request,
        `/api/projects/${project.id}/dashboard/trial-operation/governance/apply`,
        token,
        { batchId: suggestions.batchId, suggestionIds },
        'apply governance suggestions'
      )
    }

    await postJson(
      request,
      `/api/projects/${project.id}/dashboard/trial-operation/execution-results`,
      token,
      { totalLimit: 120, note: 'Playwright 真实业务数据验收：模拟导入一批执行结果用于验收看板闭环。' },
      'import execution results'
    )

    const dashboard = await getJson<{ metrics: Record<string, number>; acceptanceSummary: { score: number; level: string } }>(
      request,
      `/api/projects/${project.id}/dashboard/trial-operation`,
      token,
      'verify trial operation dashboard api'
    )
    expect(Number(dashboard.metrics.requirementDocs || 0), 'dashboard requirement docs').toBe(requirementFiles.length)
    expect(Number(dashboard.metrics.testcases || 0), 'dashboard testcases').toBe(testcaseImport.importedCount)
    expect(Number(dashboard.metrics.defects || 0), 'dashboard defects').toBe(defectImport.success)

    const report = await getJson<{ title: string; generatedAt: number; markdown: string; summary: unknown }>(
      request,
      `/api/projects/${project.id}/dashboard/trial-operation/report`,
      token,
      'get trial operation report'
    )
    await postJson(
      request,
      `/api/projects/${project.id}/dashboard/trial-operation/report/snapshots`,
      token,
      report,
      'save trial operation report snapshot'
    )

    await page.addInitScript(
      ({ accessToken, expiresAt }) => {
        localStorage.setItem('accessToken', accessToken)
        localStorage.setItem('accessTokenExpiresAt', String(expiresAt))
        localStorage.setItem('loginUsername', 'playwright-acceptance')
      },
      { accessToken: token, expiresAt: Date.now() + Math.max(60, login.expiresIn || 3600) * 1000 }
    )

    await page.setViewportSize({ width: 1440, height: 1200 })
    await page.goto(`/projects/${project.id}/trial-operation`, { waitUntil: 'networkidle' })
    await expect(page.getByText('试运行看板').first()).toBeVisible()
    await expect(page.getByText('需求文档').first()).toBeVisible()
    await expect(page.getByText('测试用例').first()).toBeVisible()
    await expect(page.getByText('缺陷').first()).toBeVisible()
    await expect(page.getByText('维度').first()).toBeVisible()
    await page.getByRole('combobox').first().selectOption('defectSeverityDistribution')
    await expect(page.getByText('缺陷严重级别').first()).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('trial-operation-dashboard.png'), fullPage: true })

    await page.goto(`/projects/${project.id}/settings/acceptance`, { waitUntil: 'networkidle' })
    await expect(page.getByText('生产验收中心', { exact: true })).toBeVisible()
    await expect(page.getByText('报告预览', { exact: true })).toBeVisible()
    await expect(page.getByRole('cell', { name: '真实数据基线' })).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('acceptance-center.png'), fullPage: true })

    const summaryPath = testInfo.outputPath('real-business-data-acceptance-summary.json')
    fs.writeFileSync(
      summaryPath,
      JSON.stringify(
        {
          projectId: project.id,
          projectName,
          frontendUrl: `${process.env.WEITESTING_FRONTEND_URL || 'https://app.evanshine.me'}/projects/${project.id}/trial-operation`,
          acceptanceUrl: `${process.env.WEITESTING_FRONTEND_URL || 'https://app.evanshine.me'}/projects/${project.id}/settings/acceptance`,
          requirementDocs: requirementFiles.length,
          importedTestcases: testcaseImport.importedCount,
          failedTestcases: testcaseImport.failedCount,
          parsedDefects: defectItems.length,
          importedDefects: defectImport.success,
          failedDefects: defectImport.failed,
          governanceSuggestions: suggestions.items.length,
          appliedGovernanceSuggestions: suggestionIds.length,
          acceptanceScore: dashboard.acceptanceSummary.score,
          acceptanceLevel: dashboard.acceptanceSummary.level
        },
        null,
        2
      ),
      'utf8'
    )

    testInfo.attachments.push({ name: 'acceptance-summary', path: summaryPath, contentType: 'application/json' })
  })
})
