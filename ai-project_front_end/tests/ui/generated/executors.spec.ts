import { expect, test } from '@playwright/test'

test.describe('executors 管理页冒烟', () => {
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
      if (path.startsWith('/api/projects/1/executors')) {
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

    await page.goto('/projects/1/settings/executors', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/projects\/1\/settings\/executors/)
    await expect(page.locator('div').filter({ hasText: /^测试执行器$/ })).toBeVisible()
    await expect(page.getByText('暂无执行器')).toBeVisible()
    await expect(page.getByRole('button', { name: '新建执行器' })).toBeVisible()
  })

  test('mock 执行器卡片列表与操作按钮', async ({ page }) => {
    const mockExecutors = [
      {
        id: 'exec-001',
        projectId: '1',
        name: 'JMeter Runner',
        executorType: 'JMETER',
        description: 'JMeter 性能测试执行器',
        config: null,
        enabled: true,
        version: '5.6',
        createdBy: 'user-1',
        createdAt: 1700000000,
        updatedAt: 1700000000
      },
      {
        id: 'exec-002',
        projectId: '1',
        name: 'Postman Runner',
        executorType: 'POSTMAN',
        description: 'Postman 集合执行器',
        config: null,
        enabled: false,
        version: '1.0',
        createdBy: 'user-1',
        createdAt: 1700001000,
        updatedAt: 1700001000
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
      if (path.startsWith('/api/projects/1/executors')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 20, total: 2, items: mockExecutors } })
        })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/executors', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('JMeter Runner')).toBeVisible()
    await expect(page.getByText('Postman Runner')).toBeVisible()
    await expect(page.getByText('JMETER', { exact: true })).toBeVisible()
    await expect(page.getByText('POSTMAN', { exact: true })).toBeVisible()
    await expect(page.getByText('已启用', { exact: true })).toBeVisible()
    await expect(page.getByText('已禁用', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: '禁用' })).toBeVisible()
    await expect(page.getByRole('button', { name: '启用' })).toBeVisible()
    await expect(page.getByRole('button', { name: '删除' }).first()).toBeVisible()
  })

  test('新建执行器表单展开', async ({ page }) => {
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
      if (path.startsWith('/api/projects/1/executors')) {
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

    await page.goto('/projects/1/settings/executors', { waitUntil: 'domcontentloaded' })
    await page.getByRole('button', { name: '新建执行器' }).click()
    await expect(page.getByPlaceholder('执行器名称')).toBeVisible()
    await expect(page.getByPlaceholder('描述（可选）')).toBeVisible()
    await expect(page.getByPlaceholder('版本（可选）')).toBeVisible()
    await expect(page.getByRole('button', { name: '创建' })).toBeVisible()
  })
})
