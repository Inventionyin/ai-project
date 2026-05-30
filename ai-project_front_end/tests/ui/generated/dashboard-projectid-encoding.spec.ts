import { expect, test } from '@playwright/test'

test.describe('Dashboard projectId 编码', () => {
  const rawProjectId = 'team/A&B?Q=1'
  const encodedProjectId = encodeURIComponent(rawProjectId)

  test('特殊 projectId 下壳子和仪表盘请求都使用编码后的路径', async ({ page }) => {
    const requestPaths: string[] = []
    let summaryRequested = false
    let failureTopRequested = false
    let qualityGateRequested = false
    let trendRequested = false
    page.on('request', (request) => {
      requestPaths.push(new URL(request.url()).pathname)
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.route('**/*', async (route) => {
      const req = route.request()
      if (req.resourceType() === 'document') {
        await route.continue()
        return
      }

      const url = new URL(req.url())
      const path = url.pathname

      if (path === `/api/projects/${encodedProjectId}`) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: rawProjectId, name: 'Encoded Dashboard Project' } })
        })
        return
      }

      if (path === `/api/projects/${encodedProjectId}/environments`) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [{ id: 'env-1', name: '测试环境' }] })
        })
        return
      }

      if (path === `/api/projects/${encodedProjectId}/dashboard/summary`) {
        summaryRequested = true
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              date: '2026-05-27',
              totalRuns: 12,
              passedRuns: 10,
              failedRuns: 1,
              runningRuns: 1,
              canceledRuns: 0,
              passRate: 83.3
            }
          })
        })
        return
      }

      if (path === `/api/projects/${encodedProjectId}/dashboard/failure-top`) {
        failureTopRequested = true
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              dimension: 'testcase',
              items: [{ id: 'tc-1', name: '登录失败', failCount: 2, totalRuns: 5, suiteNames: ['核心回归'] }]
            }
          })
        })
        return
      }

      if (path === `/api/projects/${encodedProjectId}/dashboard/quality-gate`) {
        qualityGateRequested = true
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              overall: 'PASSED',
              gates: [{ name: 'P0 通过率', threshold: '100%', current: '100%', passed: true }]
            }
          })
        })
        return
      }

      if (path === `/api/projects/${encodedProjectId}/dashboard/trend`) {
        trendRequested = true
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              days: 7,
              items: [{ date: '05-27', passRate: 83.3, failCount: 1, totalRuns: 12 }]
            }
          })
        })
        return
      }

      if (path === '/api/suites') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              page: 1,
              pageSize: 200,
              total: 1,
              items: [{ id: 'suite-1', name: '核心回归', defaultEnvId: 'env-1', config: { timeoutSec: 600, concurrency: 4, retryCount: 1 }, updatedAt: 1710000000 }]
            }
          })
        })
        return
      }

      if (path === '/api/runs') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              page: 1,
              pageSize: 5,
              total: 1,
              items: [
                {
                  id: 'run-1',
                  suiteId: 'suite-1',
                  envId: 'env-1',
                  status: 'PASSED',
                  triggerType: 'MANUAL',
                  metrics: { total: 10, passed: 10, done: 10 },
                  progress: { total: 10, done: 10 },
                  startAt: 1710000000
                }
              ]
            }
          })
        })
        return
      }

      await route.continue()
    })

    await page.goto(`/projects/${encodedProjectId}/dashboard`, { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('button', { name: '切换项目' })).toContainText('Encoded Dashboard Project')
    await page.waitForTimeout(1200)
    expect(requestPaths).toContain(`/api/projects/${encodedProjectId}`)
    expect(summaryRequested).toBeTruthy()
    expect(failureTopRequested).toBeTruthy()
    expect(qualityGateRequested).toBeTruthy()
    expect(trendRequested).toBeTruthy()
  })
})
