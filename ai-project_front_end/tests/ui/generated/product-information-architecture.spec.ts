import { expect, test } from '@playwright/test'

test.describe('产品信息架构收敛', () => {
  let failureTopQueries: string[]
  let suiteItems: Array<Record<string, unknown>>

  test.beforeEach(async ({ page }) => {
    failureTopQueries = []
    suiteItems = []
    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })
    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      if (req.resourceType() === 'document') return route.continue()
      const projectMatch = url.pathname.match(/^\/api\/projects\/([^/]+)$/)
      if (projectMatch) {
        const projectId = projectMatch[1]
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: projectId, name: `E2E Project ${projectId}` } }),
        })
      }
      if (url.pathname === '/api/projects/1/acceptance/summary') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              overallStatus: 'BLOCKED',
              score: 54,
              generatedAt: 1710000000,
              checks: [
                {
                  key: 'realData',
                  label: '真实数据基线',
                  status: 'BLOCKED',
                  detail: '建议暂缓',
                  recommendation: '治理缺陷后复验',
                },
                {
                  key: 'externalSystems',
                  label: '外部系统联调',
                  status: 'READY',
                  detail: '外部系统已就绪',
                  recommendation: '保持 smoke',
                },
                {
                  key: 'opsHealth',
                  label: '运维可观测性',
                  status: 'READY',
                  detail: '运维健康聚合状态：READY',
                  recommendation: '保持巡检',
                },
              ],
              externalSystems: [],
              metrics: {
                requirementDocs: 31,
                testcases: 5899,
                defects: 460,
                defectClusters: 242,
                riskHints: 460,
                executedCaseRuns: 27,
              },
              nextActions: ['关闭阻塞缺陷后复验'],
            },
          }),
        })
      }
      if (url.pathname === '/api/projects/1/acceptance/report') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { markdown: '# 生产验收报告' } }),
        })
      }
      const workspaceSummaryMatch = url.pathname.match(/^\/api\/projects\/([^/]+)\/workspace\/summary$/)
      if (workspaceSummaryMatch) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              assets: {
                requirementDocs: 31,
                testcases: 5899,
                formalCases: 27,
                testPoints: 5872,
                apiCollections: 3,
                apiRequests: 128,
                suites: 12,
              },
              automation: {
                runs: 27,
                executedCaseRuns: 27,
                passRate: 81.5,
                latestRunAt: 1710000000,
              },
              risks: {
                defects: 460,
                p0Open: 22,
                riskHints: 460,
              },
              capabilities: {
                role: 'admin',
                assets: true,
                ai: true,
                automation: true,
                settings: true,
                ops: true,
              },
            },
          }),
        })
      }
      const requirementDocsMatch = url.pathname.match(/^\/api\/projects\/([^/]+)\/requirements\/docs$/)
      if (requirementDocsMatch) {
        const projectId = requirementDocsMatch[1]
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [
                {
                  id: 'doc-1',
                  projectId,
                  title: '用户中心 PRD',
                  status: 'PUBLISHED',
                  tags: ['user', 'core'],
                  sourceType: 'PRD',
                  latestVersionId: 'ver-2',
                  updatedAt: 1710000000,
                },
                {
                  id: 'doc-2',
                  projectId,
                  title: '支付流程 Spec',
                  status: 'REVIEWING',
                  tags: ['payment'],
                  sourceType: 'SPEC',
                  latestVersionId: 'ver-1',
                  updatedAt: 1710000100,
                },
              ],
              total: 2,
              page: 1,
              pageSize: 8,
            },
          }),
        })
      }
      const requirementAnalysesMatch = url.pathname.match(/^\/api\/projects\/([^/]+)\/requirements\/analyses$/)
      if (requirementAnalysesMatch) {
        const projectId = requirementAnalysesMatch[1]
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: [
              {
                id: 'analysis-1',
                projectId,
                docId: 'doc-1',
                docVersionId: 'ver-2',
                status: 'REVIEWED',
                summary: '已提取核心流程、边界值与异常流。',
                riskLevel: 'HIGH',
                coverageScore: 86,
                analysis: {
                  featurePoints: [],
                  businessRules: [],
                  testPoints: [],
                  riskPoints: [],
                  boundaryCases: [],
                  coverageSuggestions: [],
                },
                updatedAt: 1710000200,
              },
            ],
          }),
        })
      }
      const knowledgeRetrospectivesMatch = url.pathname.match(/^\/api\/projects\/([^/]+)\/knowledge\/retrospectives$/)
      if (knowledgeRetrospectivesMatch) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [],
              total: 0,
              page: 1,
              pageSize: 10,
            },
          }),
        })
      }
      const platformAiJobsMatch = url.pathname.match(/^\/api\/projects\/([^/]+)\/platform\/ai-jobs$/)
      if (platformAiJobsMatch) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [
                {
                  id: 'job-1',
                  projectId: platformAiJobsMatch[1],
                  jobType: 'CASE_GOVERNANCE',
                  status: 'SUCCESS',
                  triggerSource: 'MANUAL',
                  summary: '完成一次治理建议生成',
                  createdBy: 'user-1',
                  createdAt: 1710000500,
                },
              ],
            },
          }),
        })
      }
      const platformAuditLogsMatch = url.pathname.match(/^\/api\/projects\/([^/]+)\/platform\/audit-logs$/)
      if (platformAuditLogsMatch) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [
                {
                  id: 'platform-audit-1',
                  projectId: platformAuditLogsMatch[1],
                  module: 'platform',
                  action: 'REFRESH',
                  resourceType: 'PlatformRecord',
                  resourceId: 'platform-record-1',
                  summary: '刷新平台记录',
                  detail: {},
                  userId: 'user-1',
                  createdAt: 1710000600,
                },
              ],
            },
          }),
        })
      }
      const defectsMatch = url.pathname.match(/^\/api\/projects\/([^/]+)\/defects$/)
      if (defectsMatch) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [],
              total: 0,
            },
          }),
        })
      }
      const auditLogsMatch = url.pathname.match(/^\/api\/projects\/([^/]+)\/security\/audit-logs$/)
      if (auditLogsMatch) {
        const projectId = auditLogsMatch[1]
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              page: 1,
              pageSize: 20,
              total: 1,
              items: [
                {
                  id: 'audit-1',
                  projectId,
                  userId: 'user-1',
                  module: 'runs',
                  action: 'CREATE',
                  resourceType: 'Run',
                  resourceId: 'run-1',
                  summary: '创建运行记录',
                  detail: {},
                  createdAt: 1710000000,
                },
              ],
            },
          }),
        })
      }
      if (url.pathname === '/api/projects/1/dashboard/summary') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              date: '2026-05-25',
              totalRuns: 18,
              passedRuns: 15,
              failedRuns: 2,
              runningRuns: 1,
              canceledRuns: 0,
              passRate: 83.3,
            },
          }),
        })
      }
      if (url.pathname === '/api/projects/1/dashboard/failure-top') {
        failureTopQueries.push(url.search)
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { dimension: 'testcase', items: [] } }),
        })
      }
      if (url.pathname === '/api/projects/1/dashboard/quality-gate') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { overall: 'PASSED', gates: [] } }),
        })
      }
      if (url.pathname === '/api/projects/1/dashboard/trend') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              days: 7,
              items: [
                { date: '05-19', passRate: 80, failCount: 2, totalRuns: 10 },
                { date: '05-20', passRate: 90, failCount: 1, totalRuns: 10 },
              ],
            },
          }),
        })
      }
      if (url.pathname === '/api/doc-ingest/perf-reports') {
        if (url.pathname.endsWith('/perf-1')) {
          return route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              code: 0,
              data: {
                id: 'perf-1',
                name: 'Smoke 压测',
                status: 'PASSED',
                createdAt: 1710000000,
                duration: '5m',
                vus: 20,
                tps: 128.4,
                avgResponseMs: 83.5,
                p95ResponseMs: 124.1,
                successRate: 99.8,
                resources: {
                  cpuAvg: 32.5,
                  cpuMax: 58.2,
                  memoryAvg: 41.7,
                  memoryMax: 63.1,
                  ioReadMb: 10.2,
                  ioWriteMb: 6.8,
                },
                trendPoints: [
                  { tps: 120, avgResponseMs: 80 },
                  { tps: 128, avgResponseMs: 84 },
                ],
                latencyDistribution: [
                  { label: '<100ms', count: 80 },
                  { label: '100-200ms', count: 12 },
                ],
                asserts: [{ apiName: 'POST /api/login', passed: 20, failed: 0 }],
              },
            }),
          })
        }
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [
                {
                  id: 'perf-1',
                  name: 'Smoke 压测',
                  status: 'PASSED',
                  createdAt: 1710000000,
                  duration: '5m',
                  vus: 20,
                },
              ],
            },
          }),
        })
      }
      if (url.pathname === '/api/doc-ingest/perf-reports/perf-1') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: 'perf-1',
              name: 'Smoke 压测',
              status: 'PASSED',
              createdAt: 1710000000,
              duration: '5m',
              vus: 20,
              tps: 128.4,
              avgResponseMs: 83.5,
              p95ResponseMs: 124.1,
              successRate: 99.8,
              resources: {
                cpuAvg: 32.5,
                cpuMax: 58.2,
                memoryAvg: 41.7,
                memoryMax: 63.1,
                ioReadMb: 10.2,
                ioWriteMb: 6.8,
              },
              trendPoints: [
                { tps: 120, avgResponseMs: 80 },
                { tps: 128, avgResponseMs: 84 },
              ],
              latencyDistribution: [
                { label: '<100ms', count: 80 },
                { label: '100-200ms', count: 12 },
              ],
              asserts: [{ apiName: 'POST /api/login', passed: 20, failed: 0 }],
            },
          }),
        })
      }
      if (url.pathname === '/api/ui-tests/reports') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [
                {
                  runId: 'ui-run-1',
                  projectId: '1',
                  pageId: 'login-page',
                  status: 'COMPLETED',
                  result: 'FAILED',
                  assertLevel: 'P0',
                  total: 12,
                  passed: 10,
                  failed: 2,
                  skipped: 0,
                  durationMs: 28500,
                  reportDir: '/reports/ui-run-1',
                  reportIndexUrl: 'https://example.com/ui-run-1/index.html',
                  createdAt: 1710000300,
                  finishedAt: 1710000400,
                },
              ],
            },
          }),
        })
      }
      if (url.pathname === '/api/ui-tests/reports/ui-run-1') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              runId: 'ui-run-1',
              projectId: '1',
              pageId: 'login-page',
              status: 'COMPLETED',
              result: 'FAILED',
              assertLevel: 'P0',
              specPath: 'tests/ui/login.spec.ts',
              reportDir: '/reports/ui-run-1',
              reportIndexUrl: 'https://example.com/ui-run-1/index.html',
              summary: {
                total: 12,
                passed: 10,
                failed: 2,
                skipped: 0,
                durationMs: 28500,
              },
              failedCases: [
                {
                  title: '登录失败提示',
                  error: 'expect visible',
                  screenshot: 'https://example.com/ui-run-1/failure.png',
                  trace: 'https://example.com/ui-run-1/trace.zip',
                },
              ],
              startedAt: 1710000300,
              finishedAt: 1710000400,
            },
          }),
        })
      }
      if (url.pathname === '/api/runs' && req.method() === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: 'run-1',
              status: 'QUEUED',
              progress: { done: 0, total: 1 },
              triggerType: 'MANUAL',
              executionSource: null,
              metrics: { total: 1, done: 0, passed: 0, failed: 0, skipped: 0 },
              suiteId: 'suite-1',
              envId: 'env-1',
              startAt: 1710000000,
            },
          }),
        })
      }
      if (url.pathname === '/api/runs') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 5, total: 0, items: [] } }),
        })
      }
      if (url.pathname === '/api/suites') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              page: 1,
              pageSize: 200,
              total: 1,
              items: [
                {
                  id: 'suite-1',
                  projectId: '1',
                  name: '核心回归套件',
                  defaultEnvId: 'env-1',
                  config: { timeoutSec: 30, concurrency: 1, retryCount: 0 },
                  createdAt: 1710000000,
                  updatedAt: 1710000000,
                },
              ],
            },
          }),
        })
      }
      if (url.pathname === '/api/projects/1/environments') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [{ id: 'env-1', name: '测试环境', baseUrl: 'https://api.test.local' }] }),
        })
      }
      if (url.pathname === '/api/collections/coll-1') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: 'coll-1',
              projectId: '1',
              name: '登录接口集合',
              variables: {},
              groups: [
                {
                  id: 'group-1',
                  collectionId: 'coll-1',
                  name: '认证',
                  order: 1,
                  requests: [
                    {
                      id: 'req-1',
                      collectionId: 'coll-1',
                      groupId: 'group-1',
                      name: '登录成功',
                      method: 'POST',
                      url: '/api/login',
                      headers: { 'Content-Type': 'application/json' },
                      auth: {},
                      body: { raw: '{"username":"demo","password":"demo"}' },
                      asserts: { statusCode: 200 },
                      updatedAt: 1710000000,
                    },
                  ],
                },
              ],
              requests: [],
              updatedAt: 1710000000,
            },
          }),
        })
      }
      if (url.pathname === '/api/collections/coll-1/requests/req-1' && req.method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: 'req-1',
              collectionId: 'coll-1',
              groupId: 'group-1',
              name: '登录成功',
              method: 'POST',
              url: '/api/login',
              headers: { 'Content-Type': 'application/json' },
              auth: {},
              body: { raw: '{"username":"demo","password":"demo"}' },
              asserts: { statusCode: 200 },
              updatedAt: 1710000000,
            },
          }),
        })
      }
      if (url.pathname === '/api/collections/coll-1/requests/req-1/run') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              collectionId: 'coll-1',
              requestId: 'req-1',
              envId: 'env-1',
              ok: true,
              status: 200,
              elapsedMs: 23,
              error: null,
              response: {
                headers: { 'content-type': 'application/json' },
                body: '{"token":"mock-token"}',
              },
            },
          }),
        })
      }
      if (url.pathname === '/api/projects/1/collections/coll-1/bindings') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [] }),
        })
      }
      if (url.pathname === '/api/projects/1/requests/req-1/bindings') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: [
              {
                id: 'binding-1',
                projectId: '1',
                testcaseId: 'tc-1',
                name: '登录成功-接口绑定',
                linkType: 'REQUEST',
                requestId: 'req-1',
                collectionId: 'coll-1',
                sourceType: 'MANUAL',
                assertSummary: '状态码为 200',
                lastRunStatus: null,
                lastRunAt: null,
                params: {},
                priority: 100,
                enabled: true,
                version: 1,
                updatedAt: 1710000000,
              },
            ],
          }),
        })
      }
      if (url.pathname === '/api/testcases') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              page: 1,
              pageSize: 200,
              total: 1,
              items: [{ id: 'tc-1', projectId: '1', title: '登录成功用例', type: 'API', priority: 'P0', status: 'ACTIVE' }],
            },
          }),
        })
      }
      if (url.pathname === '/api/testcases/tc-1/bindings' && req.method() === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: 'binding-1',
              projectId: '1',
              testcaseId: 'tc-1',
              name: '登录成功-接口绑定',
              linkType: 'REQUEST',
              requestId: 'req-1',
              collectionId: 'coll-1',
              sourceType: 'MANUAL',
              assertSummary: '状态码为 200',
              lastRunStatus: null,
              lastRunAt: null,
              params: {},
              priority: 100,
              enabled: true,
              version: 1,
              updatedAt: 1710000000,
            },
          }),
        })
      }
      if (url.pathname === '/api/suites/suite-1/items' && req.method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: suiteItems }),
        })
      }
      if (url.pathname === '/api/suites/suite-1/items' && req.method() === 'POST') {
        const posted = req.postDataJSON() as { items?: Array<Record<string, unknown>> }
        suiteItems = posted.items || []
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: suiteItems.map((item, index) => ({
              id: `suite-item-${index + 1}`,
              suiteId: 'suite-1',
              testcaseId: item.testcaseId,
              orderNo: item.orderNo,
              params: item.params || {},
              testcaseTitle: '登录成功用例',
              testcaseType: 'API',
              testcasePriority: 'P0',
              testcaseStatus: 'ACTIVE',
            })),
          }),
        })
      }
      if (url.pathname === '/api/doc-ingest/generate-csv') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              fileName: 'generated_cases.csv',
              csvText: 'title,apiMethod,apiUrl,expectedResult\n登录成功,POST,/api/login,返回 token',
              itemCount: 1,
              status: 'SUCCESS',
            },
          }),
        })
      }
      if (url.pathname === '/api/testcases/import') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { imported: 1, skipped: 0, errors: [] } }),
        })
      }
      return route.continue()
    })
  })

  test('侧边栏按当前模块收起非当前分组', async ({ page }) => {
    await page.goto('/projects/1/settings/acceptance', { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('button', { name: /^仪表盘$/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /资产中心/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /AI能力/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /自动化执行/ })).toBeVisible()
    await expect(page.getByRole('button', { name: '设置', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: /设置总览/ })).toBeVisible()

    await expect(page.getByRole('button', { name: /资产总览/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /需求管理/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /用例管理/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /接口管理/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /测试套件/ })).not.toBeVisible()

    await expect(page.getByRole('button', { name: /AI总览/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /自动生成测试用例/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /执行总览/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /UI自动化/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /接口自动化/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /性能自动化/ })).not.toBeVisible()

    await page.getByRole('button', { name: /资产中心/ }).click()
    await expect(page.getByRole('button', { name: /资产总览/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /设置总览/ })).not.toBeVisible()

    await expect(page.getByRole('button', { name: /AI 助手/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /接口集合/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /执行中心/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /Worker 管理/ })).not.toBeVisible()
  })

  test('验收中心不再重复展示资产总量指标卡', async ({ page }) => {
    await page.goto('/projects/1/settings/acceptance', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('生产验收中心')).toBeVisible()
    await expect(page.getByText('验收演示路线')).toBeVisible()
    await expect(page.getByText('接口调试后加入套件，并触发Run结果。')).toBeVisible()
    await expect(page.getByRole('link', { name: '测试套件' })).toHaveAttribute('href', '/projects/1/assets/suites')
    await expect(page.getByText('阻塞治理概览')).toBeVisible()
    await expect(page.getByText('未关闭缺陷', { exact: true })).toBeVisible()
    await expect(page.getByText('风险提示', { exact: true })).toBeVisible()
    await expect(page.getByText('已执行用例', { exact: true })).toBeVisible()

    await expect(page.getByText('需求文档', { exact: true })).not.toBeVisible()
    await expect(page.getByText('测试用例', { exact: true })).not.toBeVisible()
    await expect(page.getByText('缺陷聚类', { exact: true })).not.toBeVisible()
  })

  test('四个一级工作台首页显示聚合指标和操作入口', async ({ page }) => {
    await page.goto('/projects/1/assets', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: '资产中心' })).toBeVisible()
    await expect(page.getByText('测试用例', { exact: true })).toBeVisible()
    await expect(page.getByText('5899', { exact: true })).toBeVisible()
    await expect(page.getByLabel('选择资产类型')).toBeVisible()
    await expect(page.getByText('统一资产操作')).toBeVisible()
    await expect(page.getByLabel('选择资产操作')).toBeVisible()
    await page.getByLabel('选择资产操作').selectOption('批量编辑')
    await expect(page.getByText('批量编辑字段、标签、模块和关联关系')).toBeVisible()
    await expect(page.getByRole('link', { name: '前往用例管理' })).toHaveAttribute('href', '/projects/1/assets/testcases')
    await page.getByLabel('选择资产类型').selectOption('接口管理')
    await expect(page.getByRole('link', { name: /进入接口/ })).toHaveAttribute('href', '/projects/1/assets/apis')

    await page.goto('/projects/1/ai', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: 'AI能力' })).toBeVisible()
    await expect(page.getByText('AI 不直接改正式资产')).toBeVisible()
    await expect(page.getByLabel('选择AI任务')).toBeVisible()
    await page.getByLabel('选择AI任务').selectOption('用例治理')
    await expect(page.getByRole('link', { name: /进入治理/ })).toHaveAttribute('href', '/projects/1/ai/case-governance')
    await expect(page.getByRole('link', { name: '自动生成测试用例' })).toHaveAttribute('href', '/projects/1/ai/generate-cases')

    await page.goto('/projects/1/automation', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: '自动化执行' })).toBeVisible()
    await expect(page.getByText('81.5%')).toBeVisible()
    await expect(page.getByLabel('选择执行类型')).toBeVisible()
    await page.getByLabel('选择执行类型').selectOption('性能自动化')
    await expect(page.getByRole('link', { name: /查看性能报告/ })).toHaveAttribute('href', '/projects/1/automation/performance')
    await expect(page.getByRole('link', { name: '运行记录' })).toHaveAttribute('href', '/projects/1/runs')

    await page.goto('/projects/1/settings', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: '设置' })).toBeVisible()
    await expect(page.getByText('admin', { exact: true })).toBeVisible()
    await expect(page.getByLabel('选择配置项')).toBeVisible()
    await page.getByLabel('选择配置项').selectOption('集成配置')
    await expect(page.getByRole('link', { name: /进入集成/ })).toHaveAttribute('href', '/projects/1/settings/integrations')
    await expect(page.getByRole('link', { name: 'API Token / CI Token' })).toHaveAttribute('href', '/projects/1/settings/ci-token-governance')
  })

  test('仪表盘支持自定义模块显示并持久保存', async ({ page }) => {
    await page.goto('/projects/1/dashboard', { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('heading', { name: '近 7 天趋势' })).toBeVisible()
    await expect(page.getByText('质量门禁')).toBeVisible()
    await expect(page.getByLabel('时间范围')).toBeVisible()
    await expect(page.getByLabel('统计维度')).toBeVisible()
    await page.getByLabel('时间范围').selectOption('14')
    await page.getByLabel('统计维度').selectOption('suite')
    await expect(page.getByText('当前筛选：近 14 天 · 按套件')).toBeVisible()
    await expect.poll(() => failureTopQueries.some((query) => query.includes('days=14') && query.includes('dimension=suite'))).toBeTruthy()

    await page.getByRole('button', { name: /自定义/ }).click()
    await page.getByRole('checkbox', { name: '近 7 天趋势' }).uncheck()
    await page.getByRole('button', { name: /保存布局/ }).click()

    await expect(page.getByRole('heading', { name: '近 7 天趋势' })).not.toBeVisible()
    await expect(page.getByText('布局已保存')).toBeVisible()

    await page.reload({ waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: '近 7 天趋势' })).not.toBeVisible()
    await expect(page.getByText('质量门禁')).toBeVisible()
  })

  test('仪表盘卡片入口可跳转到报告与运行记录', async ({ page }) => {
    await page.goto('/projects/1/dashboard', { waitUntil: 'domcontentloaded' })

    await page.getByRole('button', { name: '查看报告' }).click()
    await expect(page).toHaveURL('/projects/1/reports?tab=trend')

    await page.goto('/projects/1/dashboard', { waitUntil: 'domcontentloaded' })
    await page.getByRole('button', { name: '全部记录' }).click()
    await expect(page).toHaveURL('/projects/1/runs')
  })

  test('仪表盘请求失败时显示内联错误且不会弹原生提示', async ({ page }) => {
    let dialogMessage = ''
    page.on('dialog', async (dialog) => {
      dialogMessage = dialog.message()
      await dialog.dismiss()
    })
    await page.route('**/api/projects/1/dashboard/summary', async (route) => {
      await route.abort('failed')
    })

    await page.goto('/projects/1/dashboard', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('仪表盘')).toBeVisible()
    await expect(page.getByText('获取仪表盘汇总失败，请稍后重试')).toBeVisible()
    await expect.poll(() => dialogMessage).toBe('')
  })

  test('AI生成页用下拉选择智能体类型', async ({ page }) => {
    await page.goto('/projects/1/ai/generate-cases', { waitUntil: 'domcontentloaded' })

    await expect(page.getByLabel('智能体类型')).toBeVisible()
    await expect(page.getByText(/^1\s*文档检查$/)).toBeVisible()
    await expect(page.getByText(/^2\s*候选用例$/)).toBeVisible()
    await expect(page.getByText(/^3\s*人工确认$/)).toBeVisible()
    await expect(page.getByText(/^4\s*正式入库$/)).toBeVisible()
    await expect(page.getByText('生成结果', { exact: true })).toBeVisible()
    await expect(page.getByText('Generation Result')).not.toBeVisible()
    await expect(page.getByText('Cloud Sync')).not.toBeVisible()
    await expect(page.getByText('生成并导入到用例列表')).not.toBeVisible()
    await expect(page.getByText('生成候选用例，确认后入库')).toBeVisible()
    await page.getByPlaceholder('粘贴接口文档内容（支持 Markdown / OpenAPI JSON 或 YAML）...').fill('POST /api/login')
    await page.getByRole('button', { name: '生成候选用例，确认后入库' }).click()
    await expect(page.getByText('登录成功')).toBeVisible()
    await expect(page.getByText('去重状态')).toBeVisible()
    await expect(page.getByLabel('确认已完成去重检查和人工审核')).toBeVisible()
    await page.getByLabel('更多操作').selectOption('import')
    await expect(page.getByRole('button', { name: '执行操作' })).toBeDisabled()
    await page.getByLabel('确认已完成去重检查和人工审核').check()
    await expect(page.getByRole('button', { name: '执行操作' })).toBeEnabled()
    await expect(page.locator('div').filter({ hasText: /^测试用例生成$/ })).toBeVisible()
    await page.getByLabel('智能体类型').selectOption('PERF')
    await expect(page.locator('div').filter({ hasText: /^性能脚本生成$/ })).toBeVisible()
    await expect(page.getByText('性能参数')).toBeVisible()
  })

  test('变更影响分析入口应展示匹配的页面标题，而不是需求文档中心', async ({ page }) => {
    await page.goto('/projects/1/ai/change-impact', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('变更影响分析')).toBeVisible()
    await expect(page.getByText('需求文档中心')).not.toBeVisible()
    await expect(page.getByRole('link', { name: '打开文档' }).first()).toBeVisible()
  })

  test('UI自动化入口应默认展示 UI 测试报告视图', async ({ page }) => {
    await page.goto('/projects/1/automation/ui', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('login-page · P0', { exact: true })).toBeVisible()
    await expect(page.getByText('失败用例')).toBeVisible()
    await expect(page.getByText('质量趋势与单次报告')).not.toBeVisible()
  })

  test('性能自动化入口应默认展示性能报告视图', async ({ page }) => {
    await page.goto('/projects/1/automation/performance', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('Smoke 压测', { exact: true })).toBeVisible()
    await expect(page.getByText('TPS 趋势图 / 平均响应时间趋势图')).toBeVisible()
    await expect(page.getByText('质量趋势与单次报告')).not.toBeVisible()
  })

  test('自动化执行入口应高亮自动化分组，而不是落到资产分组', async ({ page }) => {
    await page.goto('/projects/1/automation/api', { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('button', { name: '自动化执行' })).toHaveAttribute('aria-expanded', 'true')
    await expect(page.getByRole('button', { name: '接口自动化' })).toBeVisible()
  })

  test('AI 用例治理入口应展开 AI 分组并显示用例治理导航', async ({ page }) => {
    await page.goto('/projects/1/ai/case-governance', { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('button', { name: 'AI能力' })).toHaveAttribute('aria-expanded', 'true')
    await expect(page.getByRole('button', { name: '用例治理' })).toBeVisible()
  })

  test('知识沉淀入口应归属 AI 分组并显示导航入口', async ({ page }) => {
    await page.goto('/projects/1/knowledge/retrospectives', { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('button', { name: 'AI能力' })).toHaveAttribute('aria-expanded', 'true')
    await expect(page.getByRole('button', { name: '知识沉淀' })).toBeVisible()
  })

  test('缺陷管理入口应归属自动化分组并显示导航入口', async ({ page }) => {
    await page.goto('/projects/1/defects', { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('button', { name: '自动化执行' })).toHaveAttribute('aria-expanded', 'true')
    await expect(page.getByRole('button', { name: '缺陷管理' })).toBeVisible()
  })

  test('平台记录入口应归属设置分组并显示平台配置导航', async ({ page }) => {
    await page.goto('/projects/1/settings/platform-records', { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('button', { name: '设置', exact: true })).toHaveAttribute('aria-expanded', 'true')
    await expect(page.getByRole('button', { name: '平台配置' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '平台记录' })).toBeVisible()
  })

  test('需求解析入口应展示解析工作台，而不是直接落到文档列表页', async ({ page }) => {
    await page.goto('/projects/1/ai/requirements', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('需求解析')).toBeVisible()
    await expect(page.getByText('最近解析', { exact: true })).toBeVisible()
    await expect(page.getByText('需求文档中心')).not.toBeVisible()
    await expect(page.getByRole('link', { name: '查看解析' })).toBeVisible()
  })

  test('项目级权限入口保持当前 projectId，不会回落到 project 1', async ({ page }) => {
    await page.goto('/projects/2/settings', { waitUntil: 'domcontentloaded' })

    await page.getByRole('button', { name: /权限/ }).click()
    await expect(page).toHaveURL('/projects/2/settings/rbac')
    await expect(page.getByRole('heading', { name: '权限与成员' })).toBeVisible()
    await expect(page.getByLabel('选择项目角色')).toBeVisible()
    await page.getByLabel('选择项目角色').selectOption('editor')
    await expect(page.getByText('可维护需求、用例、接口和执行资产')).toBeVisible()
    await expect(page.getByRole('link', { name: '进入项目设置' })).toHaveAttribute('href', '/projects/2/settings')
  })

  test('遗留权限路径优先回到最近访问项目', async ({ page }) => {
    await page.goto('/projects/2/dashboard', { waitUntil: 'domcontentloaded' })
    await page.goto('/settings/rbac', { waitUntil: 'domcontentloaded' })

    await expect(page).toHaveURL('/projects/2/settings/rbac')
    await expect(page.getByRole('link', { name: '进入项目设置' })).toHaveAttribute('href', '/projects/2/settings')
  })

  test('设置侧边栏的审计日志入口进入真实项目审计页', async ({ page }) => {
    await page.goto('/projects/1/settings', { waitUntil: 'domcontentloaded' })

    await page.getByRole('button', { name: /审计日志/ }).click()
    await expect(page).toHaveURL('/projects/1/settings/audit')
    await expect(page.getByText('安全审计日志')).toBeVisible()
    await expect(page.getByText('查看关键操作的审计记录，敏感信息已自动脱敏')).toBeVisible()
    await expect(page.getByText('创建运行记录')).toBeVisible()
    await expect(page.getByText('projectId: -')).not.toBeVisible()
  })

  test('接口集合详情支持调试请求并加入测试套件', async ({ page }) => {
    await page.goto('/projects/1/assets/apis/coll-1', { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('heading', { name: 'API 调试台' })).toBeVisible()
    await expect(page.getByLabel('调试环境')).toBeVisible()
    await page.getByLabel('调试环境').selectOption('env-1')
    await page.getByRole('button', { name: '运行请求' }).click()
    await expect(page.getByText('状态码 200')).toBeVisible()
    await expect(page.getByText('耗时 23 ms')).toBeVisible()
    await expect(page.getByText('mock-token')).toBeVisible()

    await expect(page.getByLabel('选择绑定用例')).toBeVisible()
    await page.getByLabel('选择绑定用例').selectOption('tc-1')
    await page.getByRole('button', { name: '保存为用例绑定' }).click()
    await expect(page.getByText('绑定已创建')).toBeVisible()

    await expect(page.getByLabel('选择加入套件')).toBeVisible()
    await page.getByLabel('选择加入套件').selectOption('suite-1')
    await page.getByRole('button', { name: '加入测试套件' }).click()
    await expect(page.getByText('已加入套件：核心回归套件')).toBeVisible()
    await page.getByRole('button', { name: '加入测试套件' }).click()
    await expect(page.getByText('已在套件中')).toBeVisible()
  })

  test('测试套件列表运行真实套件并跳转到运行详情', async ({ page }) => {
    await page.goto('/projects/1/assets/suites', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('核心回归套件')).toBeVisible()
    await page.getByRole('button', { name: '运行' }).click()
    await expect(page.getByText('运行已触发：run-1')).toBeVisible()
    await expect(page).toHaveURL(/\/projects\/1\/runs\/run-1$/)
  })
})
