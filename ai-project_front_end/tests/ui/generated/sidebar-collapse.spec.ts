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
      return route.continue()
    })
  })

  test('资产中心、执行中心、设置区域可以分别收起', async ({ page }) => {
    await page.goto('/projects/1/assets/testcases', { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('button', { name: /资产中心/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /用例管理/ })).toBeVisible()
    await page.getByRole('button', { name: /资产中心/ }).click()
    await expect(page.getByRole('button', { name: /用例管理/ })).not.toBeVisible()
    await page.getByRole('button', { name: /资产中心/ }).click()
    await expect(page.getByRole('button', { name: /用例管理/ })).toBeVisible()

    await expect(page.getByRole('button', { name: /执行中心/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /运行记录/ })).toBeVisible()
    await page.getByRole('button', { name: /执行中心/ }).click()
    await expect(page.getByRole('button', { name: /运行记录/ })).not.toBeVisible()

    await expect(page.getByRole('button', { name: /设置/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /CI Token 治理/ })).toBeVisible()
    await page.getByRole('button', { name: /设置/ }).click()
    await expect(page.getByRole('button', { name: /CI Token 治理/ })).not.toBeVisible()
  })

  test('桌面侧边栏整体可以收起', async ({ page }) => {
    await page.goto('/projects/1/assets/testcases', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('WeiTesting')).toBeVisible()
    await page.getByRole('button', { name: '收起侧边栏' }).click()
    await expect(page.getByText('WeiTesting')).not.toBeVisible()
    await expect(page.getByRole('button', { name: '展开侧边栏' })).toBeVisible()
  })
})
