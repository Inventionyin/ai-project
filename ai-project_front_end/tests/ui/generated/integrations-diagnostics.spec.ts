import { expect, test } from '@playwright/test'

test.describe('integrations diagnostics smoke', () => {
  test('联调诊断展示诊断摘要、检查项、provider readiness、最近失败', async ({ page }) => {
    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      const isApiLike = req.resourceType() !== 'document'
      if (!isApiLike) {
        await route.continue()
        return
      }

      if (path === '/api/projects/1' || path === '/projects/1') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'P1', ownerId: 'e2e-owner' } })
        })
        return
      }

      if (path === '/api/projects/1/integrations/notifications' || path === '/projects/1/integrations/notifications') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [{ id: 'rule-1', projectId: '1', channel: 'WEBHOOK', target: 'https://example.test', enabled: true, rule: {} }] })
        })
        return
      }

      if (path.startsWith('/api/projects/1/integrations/notifications/deliveries') || path.startsWith('/projects/1/integrations/notifications/deliveries')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0, page: 1, pageSize: 20 } })
        })
        return
      }

      if (path.startsWith('/api/projects/1/prompt-templates/governance') || path.startsWith('/projects/1/prompt-templates/governance')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { items: [] } }) })
        return
      }
      if (path.startsWith('/api/projects/1/prompt-templates') || path.startsWith('/projects/1/prompt-templates')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if (path.endsWith('/integrations/notifications/strategy-center')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if (path.endsWith('/integrations/notifications/diagnostics')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              summary: { status: 'BLOCKED', total: 6, blocking: 2, warnings: 3, ready: 1, failedDeliveries: 4 },
              checks: [
                {
                  id: 'check-1',
                  level: 'BLOCKER',
                  scope: 'notification',
                  title: 'Webhook Secret Missing',
                  detail: 'No secret configured',
                  recommendation: 'Set webhook secret',
                  notificationId: 'rule-1'
                }
              ],
              providerReadiness: [{ provider: 'WEBHOOK', ready: false, reason: 'MISSING_SECRET', notificationCount: 3 }],
              recentFailures: [
                {
                  id: 'f-1',
                  notificationId: 'rule-1',
                  channel: 'WEBHOOK',
                  target: 'https://example.test/hook',
                  provider: 'WEBHOOK',
                  status: 'FAILED',
                  attempts: 2,
                  lastStatusCode: 500,
                  lastError: 'timeout',
                  updatedAt: 1710000000
                }
              ]
            }
          })
        })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/integrations', { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('heading', { name: '联调诊断' })).toBeVisible()
    await expect(page.getByText('阻塞: 2')).toBeVisible()
    await expect(page.getByText('告警: 3')).toBeVisible()
    await expect(page.getByText('就绪: 1')).toBeVisible()
    await expect(page.getByText('Webhook Secret Missing')).toBeVisible()
    await expect(page.getByText('MISSING_SECRET')).toBeVisible()
    await expect(page.getByRole('cell', { name: 'timeout' })).toBeVisible()
  })
})
