import { expect, test } from '@playwright/test'

test.describe('acceptance-center 生产验收中心冒烟', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })
  })

  test('展示验收摘要与报告预览', async ({ page }) => {
    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      if (req.resourceType() === 'document') return route.continue()
      if (path === '/api/projects/22222222-2222-2222-2222-222222222222') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { id: '22222222-2222-2222-2222-222222222222', name: 'E2E Project' },
          }),
        })
      }
      if (path === '/api/projects/22222222-2222-2222-2222-222222222222/acceptance/summary') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              overallStatus: 'WARN',
              score: 82,
              generatedAt: 1710000000,
              checks: [{ key: 'schema', label: 'Schema 校验', status: 'READY', detail: '全部通过' }],
              externalSystems: [
                {
                  provider: 'Jira',
                  status: 'BLOCKED',
                  configured: false,
                  missingFields: ['apiToken'],
                  detail: 'API Token 已过期',
                  recommendation: '更新 Jira Token 后复验',
                },
                {
                  provider: 'CI Pipeline',
                  status: 'WARN',
                  configured: true,
                  missingFields: [],
                  detail: '最近一轮执行超时',
                  recommendation: '补跑失败流水线',
                },
              ],
              metrics: { passedCases: 124, failedCases: 3, blockers: 1 },
              nextActions: ['更新 Jira Token', '补跑失败流水线'],
            },
          }),
        })
      }
      if (path === '/api/projects/22222222-2222-2222-2222-222222222222/acceptance/report') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              markdown: '# 生产验收报告\n\n- 当前状态：WARN\n- 建议：处理 Jira 令牌后复验',
            },
          }),
        })
      }
      return route.continue()
    })

    await page.goto('/projects/22222222-2222-2222-2222-222222222222/settings/acceptance', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/projects\/22222222-2222-2222-2222-222222222222\/settings\/acceptance/)

    await expect(page.getByText('生产验收中心')).toBeVisible()
    await expect(page.locator('div').filter({ hasText: /^总体状态\s*预警\s*评分\s*82/ })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'Jira' })).toBeVisible()
    await expect(page.getByText('API Token 已过期')).toBeVisible()
    await expect(page.getByText('生产验收报告')).toBeVisible()
    await expect(page.getByRole('button', { name: '复制报告' })).toBeVisible()
  })
})
