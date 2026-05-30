import { expect, test } from '@playwright/test'

test.describe('reports export view aware', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      if (req.resourceType() === 'document') return route.continue()
      if (url.pathname === '/api/projects/1') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } })
        })
      }
      if (url.pathname === '/api/doc-ingest/perf-reports') {
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
                  vus: 20
                }
              ]
            }
          })
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
                ioWriteMb: 6.8
              },
              trendPoints: [
                { tps: 120, avgResponseMs: 80 },
                { tps: 128, avgResponseMs: 84 }
              ],
              latencyDistribution: [
                { label: '<100ms', count: 80 },
                { label: '100-200ms', count: 12 }
              ],
              asserts: [{ apiName: 'POST /api/login', passed: 20, failed: 0 }]
            }
          })
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
                  finishedAt: 1710000400
                }
              ]
            }
          })
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
                durationMs: 28500
              },
              failedCases: [
                {
                  title: '登录失败提示',
                  error: 'expect visible',
                  screenshot: 'https://example.com/ui-run-1/failure.png',
                  trace: 'https://example.com/ui-run-1/trace.zip'
                }
              ],
              startedAt: 1710000300,
              finishedAt: 1710000400
            }
          })
        })
      }
      return route.continue()
    })
  })

  test('性能视图导出按钮文案与下载文件保持一致', async ({ page }) => {
    await page.goto('/projects/1/automation/performance', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('Smoke 压测', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: '导出性能报告' })).toBeVisible()
    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: '导出性能报告' }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toContain('performance-report-perf-1')
  })

  test('UI 视图导出按钮文案与下载文件保持一致', async ({ page }) => {
    await page.goto('/projects/1/automation/ui', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('login-page · P0', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: '导出UI报告' })).toBeVisible()
    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: '导出UI报告' }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toContain('ui-test-report-ui-run-1')
  })
})
