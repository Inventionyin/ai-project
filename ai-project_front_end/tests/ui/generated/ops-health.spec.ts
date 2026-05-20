import { expect, test } from '@playwright/test'

test.describe('ops-health 运维健康页冒烟', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })
  })

  test('展示总体状态和检查项', async ({ page }) => {
    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      if (req.resourceType() === 'document') {
        await route.continue()
        return
      }
      if (path === '/api/projects/1') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } }),
        })
        return
      }
      if (path === '/api/ops/health/summary') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              overallStatus: 'warn',
              generatedAt: 1710000000,
              checks: [
                {
                  key: 'db_connectivity',
                  name: 'DB 连接',
                  status: 'ready',
                  metric: 'latencyP95=23ms',
                  detail: '主库连接稳定',
                  recommendation: '保持当前连接池上限',
                },
                {
                  key: 'outbox_backlog',
                  name: 'Outbox 队列',
                  status: 'blocked',
                  metric: 'pending=128',
                  detail: '待发送事件积压',
                  recommendation: '提升消费者并发并排查失败重试',
                },
              ],
            },
          }),
        })
        return
      }
      await route.continue()
    })

    await page.goto('/projects/1/settings/ops-health', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/projects\/1\/settings\/ops-health/)
    await expect(page.locator('div').filter({ hasText: /^运维健康$/ })).toBeVisible()
    await expect(page.getByText('总体状态')).toBeVisible()
    await expect(page.getByText('警告', { exact: true })).toBeVisible()
    await expect(page.getByText('DB 连接')).toBeVisible()
    await expect(page.getByText('pending=128')).toBeVisible()
    await expect(page.getByText('提升消费者并发并排查失败重试')).toBeVisible()
    await expect(page.getByRole('button', { name: '刷新' })).toBeVisible()
  })
})
