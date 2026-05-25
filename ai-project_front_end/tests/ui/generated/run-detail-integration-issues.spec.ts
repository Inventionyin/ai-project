import { expect, test, type Page } from '@playwright/test'

async function seedAuth(page: Page) {
  await page.goto('/login', { waitUntil: 'domcontentloaded' })
  await page.evaluate(() => {
    localStorage.setItem('accessToken', 'e2e-smoke-token')
    localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
  })
}

test.describe('run detail integration issues', () => {
  test('JIRA 与 ZENTAO 创建入口提交正确 payload', async ({ page }) => {
    const issuePayloads: Array<Record<string, unknown>> = []

    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      const isApiLike = req.resourceType() !== 'document'
      if (!isApiLike) {
        await route.continue()
        return
      }
      if (path === '/api/auth/me' || path === '/auth/me') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: 'u1', username: 'qa', roles: ['Admin'] } })
        })
        return
      }

      if (path === '/api/runs/run-1' || path === '/runs/run-1') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: 'run-1',
              status: 'FAILED',
              progress: { done: 10, total: 10 },
              triggerType: 'MANUAL',
              metrics: { total: 10, done: 10, passed: 7, failed: 3, skipped: 0 },
              suiteId: 'suite-1',
              envId: 'env-1',
              startAt: 1710000000
            }
          })
        })
        return
      }
      if (path.startsWith('/api/runs/run-1/case-runs') || path.startsWith('/runs/run-1/case-runs')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0, page: 1, pageSize: 20 } })
        })
        return
      }
      if (path.startsWith('/api/suites') || path.startsWith('/suites')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 200, total: 1, items: [{ id: 'suite-1', name: 'Suite One' }] } })
        })
        return
      }
      if (path === '/api/projects/1/environments' || path === '/projects/1/environments') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [{ id: 'env-1', name: 'Prod', baseUrl: 'https://prod.example.com' }] })
        })
        return
      }
      if (path.startsWith('/api/runs/allure-reports') || path.startsWith('/runs/allure-reports')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if ((path === '/api/projects/1/integrations/issues' || path === '/projects/1/integrations/issues') && req.method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: issuePayloads.map((payload, index) => ({
              id: `issue-${index + 1}`,
              runId: 'run-1',
              provider: String(payload.provider || 'JIRA'),
              issueKey: `${String(payload.provider || 'JIRA')}-${index + 1}`,
              url: String(payload.url || 'https://issue.example.com'),
              createdAt: 1710000000 + index
            }))
          })
        })
        return
      }
      if ((path === '/api/projects/1/integrations/issues' || path === '/projects/1/integrations/issues') && req.method() === 'POST') {
        issuePayloads.push((req.postDataJSON() || {}) as Record<string, unknown>)
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { id: `issue-${issuePayloads.length}`, projectId: '1', provider: String((issuePayloads.at(-1) || {}).provider || 'JIRA') }
          })
        })
        return
      }
      if (path.startsWith('/api/') || path.startsWith('/auth/')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: {} }) })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await seedAuth(page)
    await page.goto('/projects/1/runs/run-1', { waitUntil: 'domcontentloaded' })
    await expect(page.locator('div').filter({ hasText: /^外部 Issue$/ }).first()).toBeVisible()

    await page.locator('label:has-text("title") input').fill('Run failed - Jira issue')
    await page.locator('label:has-text("description") textarea').fill('Need triage for failed run in Jira.')
    await page.locator('label:has-text("projectKey") input').fill('QA')
    await page.locator('label:has-text("issueType") input').fill('Bug')
    await page.locator('label:has-text("jira baseUrl") input').fill('https://jira.example.com')
    await page.locator('label:has-text("jira email") input').fill('qa@example.com')
    await page.locator('label:has-text("jira token") input').fill('jira-token-placeholder')
    await page.getByLabel('真实创建外部缺陷').check()
    await page.getByRole('button', { name: '创建外部 Issue' }).click()
    await expect(page.getByText('Issue 创建请求已提交').first()).toBeVisible()
    await expect(page.getByText('JIRA-1')).toBeVisible()

    await page.locator('label:has-text("provider") select').selectOption('ZENTAO')
    await page.locator('label:has-text("title") input').fill('Run failed - Zentao bug')
    await page.locator('label:has-text("description") textarea').fill('Need triage for failed run in Zentao.')
    await page.locator('label:has-text("projectKey") input').fill('') // Zentao 可空
    await page.locator('label:has-text("issueType") input').fill('') // Zentao 可空
    await page.getByRole('textbox', { name: 'url', exact: true }).fill('https://zentao.example.com')
    await page.locator('label:has-text("zentao baseUrl") input').fill('https://zentao.example.com')
    await page.locator('label:has-text("zentao product") input').fill('MobileApp')
    await page.locator('label:has-text("zentao token") input').fill('zentao-token-placeholder')
    await page.getByRole('button', { name: '创建外部 Issue' }).click()
    await expect(page.getByText('Issue 创建请求已提交').first()).toBeVisible()
    await expect(page.getByText('ZENTAO-2')).toBeVisible()

    expect(issuePayloads).toHaveLength(2)

    expect(issuePayloads[0]).toMatchObject({
      provider: 'JIRA',
      runId: 'run-1',
      title: 'Run failed - Jira issue',
      description: 'Need triage for failed run in Jira.',
      url: 'https://jira.example.com',
      projectKey: 'QA',
      issueType: 'Bug',
      config: {
        baseUrl: 'https://jira.example.com',
        projectKey: 'QA',
        issueType: 'Bug'
      },
      credentials: {
        email: 'qa@example.com',
        token: 'jira-token-placeholder'
      },
      executeRequest: true
    })
    expect((issuePayloads[0].config as Record<string, unknown>).realCreateEnabled).toBe(true)

    expect(issuePayloads[1]).toMatchObject({
      provider: 'ZENTAO',
      runId: 'run-1',
      title: 'Run failed - Zentao bug',
      description: 'Need triage for failed run in Zentao.',
      url: 'https://zentao.example.com',
      config: {
        baseUrl: 'https://zentao.example.com',
        product: 'MobileApp'
      },
      credentials: {
        token: 'zentao-token-placeholder'
      }
    })
  })

  test('JIRA 必填缺失时前端阻止提交并提示错误', async ({ page }) => {
    let issueCreateAttempted = false

    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      const isApiLike = req.resourceType() !== 'document'
      if (!isApiLike) {
        await route.continue()
        return
      }
      if (path === '/api/auth/me' || path === '/auth/me') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: 'u1', username: 'qa', roles: ['Admin'] } })
        })
        return
      }

      if (path === '/api/runs/run-1' || path === '/runs/run-1') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: 'run-1',
              status: 'FAILED',
              progress: { done: 10, total: 10 },
              triggerType: 'MANUAL',
              metrics: { total: 10, done: 10, passed: 7, failed: 3, skipped: 0 },
              suiteId: 'suite-1',
              envId: 'env-1',
              startAt: 1710000000
            }
          })
        })
        return
      }
      if (path.startsWith('/api/runs/run-1/case-runs') || path.startsWith('/runs/run-1/case-runs')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0, page: 1, pageSize: 20 } })
        })
        return
      }
      if (path.startsWith('/api/suites') || path.startsWith('/suites')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 200, total: 1, items: [{ id: 'suite-1', name: 'Suite One' }] } })
        })
        return
      }
      if (path === '/api/projects/1/environments' || path === '/projects/1/environments') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [{ id: 'env-1', name: 'Prod', baseUrl: 'https://prod.example.com' }] })
        })
        return
      }
      if (path.startsWith('/api/runs/allure-reports') || path.startsWith('/runs/allure-reports')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if ((path === '/api/projects/1/integrations/issues' || path === '/projects/1/integrations/issues') && req.method() === 'GET') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if ((path === '/api/projects/1/integrations/issues' || path === '/projects/1/integrations/issues') && req.method() === 'POST') {
        issueCreateAttempted = true
        await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ code: 1, message: 'should not be called' }) })
        return
      }
      if (path.startsWith('/api/') || path.startsWith('/auth/')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: {} }) })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await seedAuth(page)
    await page.goto('/projects/1/runs/run-1', { waitUntil: 'domcontentloaded' })
    await page.locator('label:has-text("title") input').fill('Missing jira fields')
    await page.locator('label:has-text("description") textarea').fill('validation should block submit')
    await page.getByRole('button', { name: '创建外部 Issue' }).click()
    await expect(page.getByText('请完整填写 Jira 的 baseUrl、email、token、projectKey、issueType')).toBeVisible()
    expect(issueCreateAttempted).toBe(false)
  })

  test('创建外部 Issue 后端错误时展示后端错误信息', async ({ page }) => {
    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      const isApiLike = req.resourceType() !== 'document'
      if (!isApiLike) {
        await route.continue()
        return
      }
      if (path === '/api/auth/me' || path === '/auth/me') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: 'u1', username: 'qa', roles: ['Admin'] } })
        })
        return
      }

      if (path === '/api/runs/run-1' || path === '/runs/run-1') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: 'run-1',
              status: 'FAILED',
              progress: { done: 10, total: 10 },
              triggerType: 'MANUAL',
              metrics: { total: 10, done: 10, passed: 7, failed: 3, skipped: 0 },
              suiteId: 'suite-1',
              envId: 'env-1',
              startAt: 1710000000
            }
          })
        })
        return
      }
      if (path.startsWith('/api/runs/run-1/case-runs') || path.startsWith('/runs/run-1/case-runs')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0, page: 1, pageSize: 20 } })
        })
        return
      }
      if (path.startsWith('/api/suites') || path.startsWith('/suites')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 200, total: 1, items: [{ id: 'suite-1', name: 'Suite One' }] } })
        })
        return
      }
      if (path === '/api/projects/1/environments' || path === '/projects/1/environments') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [{ id: 'env-1', name: 'Prod', baseUrl: 'https://prod.example.com' }] })
        })
        return
      }
      if (path.startsWith('/api/runs/allure-reports') || path.startsWith('/runs/allure-reports')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if ((path === '/api/projects/1/integrations/issues' || path === '/projects/1/integrations/issues') && req.method() === 'GET') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if ((path === '/api/projects/1/integrations/issues' || path === '/projects/1/integrations/issues') && req.method() === 'POST') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 1, message: 'integration backend unavailable' })
        })
        return
      }
      if (path.startsWith('/api/') || path.startsWith('/auth/')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: {} }) })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await seedAuth(page)
    await page.goto('/projects/1/runs/run-1', { waitUntil: 'domcontentloaded' })
    await page.locator('label:has-text("title") input').fill('Run failed - Jira issue')
    await page.locator('label:has-text("description") textarea').fill('Need triage for failed run in Jira.')
    await page.locator('label:has-text("projectKey") input').fill('QA')
    await page.locator('label:has-text("issueType") input').fill('Bug')
    await page.locator('label:has-text("jira baseUrl") input').fill('https://jira.example.com')
    await page.locator('label:has-text("jira email") input').fill('qa@example.com')
    await page.locator('label:has-text("jira token") input').fill('jira-token-placeholder')
    await page.getByRole('button', { name: '创建外部 Issue' }).click()
    await expect(page.getByText('integration backend unavailable').first()).toBeVisible()
  })
})
