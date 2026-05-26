import { expect, test } from '@playwright/test'

test.describe('reports single failure expansion', () => {
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
      return route.continue()
    })
  })

  test('查看全部失败用例会展开并支持收起', async ({ page }) => {
    await page.goto('/projects/1/reports?tab=single', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('失败用例（11）')).toBeVisible()
    await expect(page.getByText('支付-微信支付回调验签')).toBeVisible()
    await expect(page.getByText('优惠券叠加-互斥规则')).not.toBeVisible()

    await page.getByRole('button', { name: '查看全部 11 条失败' }).click()
    await expect(page.getByText('优惠券叠加-互斥规则')).toBeVisible()
    await expect(page.getByText('收起失败用例')).toBeVisible()

    await page.getByRole('button', { name: '收起失败用例' }).click()
    await expect(page.getByText('优惠券叠加-互斥规则')).not.toBeVisible()
    await expect(page.getByRole('button', { name: '查看全部 11 条失败' })).toBeVisible()
  })
})
