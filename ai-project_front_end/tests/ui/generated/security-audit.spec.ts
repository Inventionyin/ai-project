import { expect, test } from '@playwright/test'

test.describe('security-audit 审计日志页冒烟', () => {
  test('页面标题与空状态可见', async ({ page }) => {
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
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } })
        })
        return
      }
      if (path.startsWith('/api/projects/1/security/audit-logs')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 20, total: 0, items: [] } })
        })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/security-audit', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/projects\/1\/settings\/security-audit/)
    await expect(page.getByText('安全审计日志')).toBeVisible()
    await expect(page.getByText('暂无审计记录')).toBeVisible()
    await expect(page.getByPlaceholder('模块筛选')).toBeVisible()
    await expect(page.getByPlaceholder('操作筛选')).toBeVisible()
    await expect(page.getByRole('button', { name: '查询' })).toBeVisible()
  })

  test('mock 审计日志表格数据', async ({ page }) => {
    const mockLogs = [
      {
        id: 'audit-001',
        projectId: '1',
        userId: 'user-aaa',
        module: 'requirements',
        action: 'PARSE_VERSION',
        resourceType: 'requirement_doc_version',
        resourceId: 'ver-111',
        summary: '解析需求文档版本: PRD-v2.pdf',
        detail: { docId: 'doc-001', textLength: 5200 },
        createdAt: 1700000000
      },
      {
        id: 'audit-002',
        projectId: '1',
        userId: 'user-bbb',
        module: 'devops',
        action: 'TRIGGER_DEVOPS_PIPELINE',
        resourceType: 'devops_run',
        resourceId: 'run-222',
        summary: '触发 DevOps 流水线: CI Pipeline',
        detail: {},
        createdAt: 1700001000
      }
    ]

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
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } })
        })
        return
      }
      if (path.startsWith('/api/projects/1/security/audit-logs')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 20, total: 2, items: mockLogs } })
        })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/security-audit', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('安全审计日志')).toBeVisible()
    await expect(page.getByText('PARSE_VERSION')).toBeVisible()
    await expect(page.getByText('TRIGGER_DEVOPS_PIPELINE')).toBeVisible()
    await expect(page.getByText('解析需求文档版本: PRD-v2.pdf')).toBeVisible()
    await expect(page.getByText('触发 DevOps 流水线: CI Pipeline')).toBeVisible()
    await expect(page.getByRole('cell', { name: 'requirements', exact: true })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'devops', exact: true })).toBeVisible()
  })

  test('筛选器交互', async ({ page }) => {
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
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } })
        })
        return
      }
      if (path.startsWith('/api/projects/1/security/audit-logs')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 20, total: 0, items: [] } })
        })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/security-audit', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('安全审计日志')).toBeVisible()

    await page.getByPlaceholder('模块筛选').fill('devops')
    await page.getByPlaceholder('操作筛选').fill('TRIGGER')
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByText('暂无审计记录')).toBeVisible()
  })
})
