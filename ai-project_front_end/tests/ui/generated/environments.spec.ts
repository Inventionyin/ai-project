import { expect, test } from '@playwright/test'

test.describe('environments 环境管理页冒烟', () => {
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
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } }) })
        return
      }
      if (path.startsWith('/api/projects/1/environments')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/environments', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/projects\/1\/settings\/environments/)
    await expect(page.locator('h2').filter({ hasText: /^环境列表$/ })).toBeVisible()
    await expect(page.getByText('暂无环境，请先创建。')).toBeVisible()
    await expect(page.getByRole('button', { name: '新建环境' })).toBeVisible()
  })

  test('mock 环境列表与操作按钮', async ({ page }) => {
    const mockEnvs = [
      {
        id: 'env-001',
        projectId: '1',
        name: '测试环境',
        baseUrl: 'https://test.example.com',
        variables: { API_KEY: 'test-key' },
        secretKeys: ['DB_PASSWORD'],
        healthCheck: null,
        createdAt: 1700000000,
        updatedAt: 1700000000
      },
      {
        id: 'env-002',
        projectId: '1',
        name: '生产环境',
        baseUrl: 'https://prod.example.com',
        variables: {},
        secretKeys: ['DB_PASSWORD', 'SECRET_KEY'],
        healthCheck: { url: 'https://prod.example.com/health', timeoutMs: 5000, expectedStatus: 200 },
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
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } }) })
        return
      }
      if (path.startsWith('/api/projects/1/environments')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: mockEnvs }) })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/environments', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('测试环境')).toBeVisible()
    await expect(page.getByText('生产环境')).toBeVisible()
    await expect(page.getByText('https://test.example.com')).toBeVisible()
    await expect(page.getByText('DB_PASSWORD').first()).toBeVisible()
    await expect(page.getByRole('button', { name: '删除' }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: '创建环境' })).toBeVisible()
  })

  test('新建环境表单字段可见', async ({ page }) => {
    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      if (req.resourceType() === 'document') {
        await route.continue()
        return
      }
      if (path === '/api/projects/1') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } }) })
        return
      }
      if (path.startsWith('/api/projects/1/environments')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/environments', { waitUntil: 'domcontentloaded' })
    await expect(page.locator('h2').filter({ hasText: /^新建环境$/ })).toBeVisible()
    await expect(page.getByText('名称')).toBeVisible()
    await expect(page.getByText('Base URL')).toBeVisible()
    await expect(page.getByText('Variables (JSON 对象)')).toBeVisible()
    await expect(page.getByText('启用健康检查')).toBeVisible()
    await expect(page.getByRole('button', { name: '创建环境' })).toBeVisible()
  })
})
