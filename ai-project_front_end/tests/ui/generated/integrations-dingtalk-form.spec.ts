import { expect, test } from '@playwright/test'

test.describe('integrations dingtalk form', () => {
  test('展示 DINGTALK 字段并提交正确 payload', async ({ page }) => {
    let createPayload: Record<string, unknown> | null = null
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
        if (req.method() === 'POST') {
          createPayload = (req.postDataJSON() || null) as Record<string, unknown> | null
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              code: 0,
              data: {
                id: 'rule-ding-1',
                projectId: '1',
                channel: 'IM',
                target: 'qa-dingtalk',
                enabled: true,
                rule: (createPayload?.rule as Record<string, unknown>) || {}
              }
            })
          })
          return
        }
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
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/integrations', { waitUntil: 'domcontentloaded' })
    await page.locator('label:has-text("target") input').first().fill('qa-dingtalk')
    await page.locator('label:has-text("provider") select').first().selectOption('DINGTALK')
    await expect(page.locator('label:has-text("webhookUrl") input').first()).toBeVisible()
    await expect(page.locator('label:has-text("keyword") input').first()).toBeVisible()
    await page.locator('label:has-text("webhookUrl") input').first().fill('https://oapi.dingtalk.com/robot/send?access_token=test-token')
    await page.locator('label:has-text("keyword") input').first().fill('告警')
    await page.locator('label:has-text("timeoutSec") input').first().fill('8')
    await page.locator('label:has-text("maxRetries") input').first().fill('2')
    await page.locator('label:has-text("template") textarea').first().fill('DingTalk alert: {{message}}')
    await page.getByLabel('RUN_FAILED', { exact: true }).check()
    await page.getByRole('button', { name: '创建规则' }).click()

    await expect(page.getByText('规则创建成功')).toBeVisible()
    expect(createPayload).toBeTruthy()
    expect(createPayload?.channel).toBe('IM')
    expect(createPayload?.target).toBe('qa-dingtalk')
    const rule = (createPayload?.rule || {}) as Record<string, unknown>
    expect(rule.provider).toBe('DINGTALK')
    expect(rule.webhookUrl).toBe('https://oapi.dingtalk.com/robot/send?access_token=test-token')
    expect(rule.keyword).toBe('告警')
    expect(rule.timeoutSec).toBe(8)
    expect(rule.maxRetries).toBe(2)
    expect(rule.events).toEqual(['RUN_FAILED'])
  })
})
