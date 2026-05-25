import { expect, test } from '@playwright/test'

test.describe('侧边栏折叠交互', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })
    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      if (req.resourceType() === 'document') return route.continue()
      if (url.pathname === '/api/auth/me' || url.pathname === '/auth/me') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: 'u1', username: 'e2e', roles: ['Admin'] } }),
        })
      }
      if (url.pathname === '/api/projects/1') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } }),
        })
      }
      if (url.pathname.startsWith('/api/testcases')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 20, total: 0, items: [] } }),
        })
      }
      if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/auth/')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: {} }),
        })
      }
      return route.continue()
    })
  })

  test('资产中心、自动化执行、设置区域在各自模块内可以收起', async ({ page }) => {
    await page.goto('/projects/1/assets/testcases', { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('button', { name: /资产中心/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /用例管理/ })).toBeVisible()
    await page.getByRole('button', { name: /资产中心/ }).click()
    await expect(page.getByRole('button', { name: /用例管理/ })).not.toBeVisible()
    await page.getByRole('button', { name: /资产中心/ }).click()
    await expect(page.getByRole('button', { name: /用例管理/ })).toBeVisible()

    await page.goto('/projects/1/automation', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('button', { name: /自动化执行/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /运行记录/ })).toBeVisible()
    await page.getByRole('button', { name: /自动化执行/ }).click()
    await expect(page.getByRole('button', { name: /运行记录/ })).not.toBeVisible()

    await page.goto('/projects/1/settings', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('button', { name: '设置', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: /API Token \/ CI Token/ })).toBeVisible()
    await page.getByRole('button', { name: '设置', exact: true }).click()
    await expect(page.getByRole('button', { name: /API Token \/ CI Token/ })).not.toBeVisible()
  })

  test('桌面侧边栏整体可以收起', async ({ page }) => {
    await page.goto('/projects/1/assets/testcases', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('WeiTesting')).toBeVisible()
    await page.getByRole('button', { name: '收起侧边栏' }).click()
    await expect(page.getByText('WeiTesting')).not.toBeVisible()
    await expect(page.getByRole('button', { name: '展开侧边栏' })).toBeVisible()
  })
})
