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
      if (path.endsWith('/integrations/diagnostics')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              generatedAt: '2026-05-25T10:00:00Z',
              summary: { status: 'WARN', totalChecks: 4, blocking: 0, warnings: 2, ready: 2 },
              checks: [
                {
                  id: 'external.jenkins.1',
                  category: 'devops',
                  provider: 'JENKINS',
                  status: 'WARN',
                  title: 'JENKINS 联调状态',
                  detail: '流水线已配置，尚需真实构建回执。',
                  recommendation: '补齐配置后触发一次真实构建并确认回执。',
                  configured: true,
                  missingFields: []
                },
                {
                  id: 'issues.linked-providers',
                  category: 'issue',
                  provider: 'ISSUE_TRACKING',
                  status: 'READY',
                  title: 'Issue 关联记录',
                  detail: '已关联 2 条外部 Issue。',
                  recommendation: '保持 Jira/禅道缺陷创建与回链的抽样检查。'
                }
              ],
              issueLinks: [{ provider: 'JIRA', total: 2 }],
              nextActions: ['补齐 Jenkins 触发配置后再跑真实流水线 smoke']
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
    await expect(page.getByText('统一联调总览')).toBeVisible()
    await expect(page.getByText('总项: 4')).toBeVisible()
    await expect(page.getByText('JENKINS 联调状态')).toBeVisible()
    await expect(page.getByText('JIRA: 2')).toBeVisible()
    await expect(page.getByText('补齐 Jenkins 触发配置后再跑真实流水线 smoke')).toBeVisible()
  })

  test('联调诊断接口失败时展示错误信息', async ({ page }) => {
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
          body: JSON.stringify({ code: 0, data: [] })
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
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 1, message: 'diagnostics service unavailable' })
        })
        return
      }
      if (path.endsWith('/integrations/diagnostics')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              summary: { status: 'READY', totalChecks: 0, blocking: 0, warnings: 0, ready: 0 },
              checks: [],
              issueLinks: [],
              nextActions: []
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
    await expect(page.getByText('diagnostics service unavailable')).toBeVisible()
  })

  test('联调诊断空态展示 checks/provider/failures 占位文案', async ({ page }) => {
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
          body: JSON.stringify({ code: 0, data: [] })
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
              summary: { status: 'READY', total: 0, blocking: 0, warnings: 0, ready: 0, failedDeliveries: 0 },
              checks: [],
              providerReadiness: [],
              recentFailures: []
            }
          })
        })
        return
      }
      if (path.endsWith('/integrations/diagnostics')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              summary: { status: 'READY', totalChecks: 0, blocking: 0, warnings: 0, ready: 0 },
              checks: [],
              issueLinks: [],
              nextActions: []
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
    await expect(page.getByText('暂无诊断检查项')).toBeVisible()
    await expect(page.getByText('暂无 provider 就绪信息')).toBeVisible()
    await expect(page.getByText('暂无最近失败记录')).toBeVisible()
  })
})
