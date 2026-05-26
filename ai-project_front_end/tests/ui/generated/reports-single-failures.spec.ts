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

  test('报告中心关键操作不是静态按钮', async ({ page }) => {
    await page.goto('/projects/1/reports?tab=single', { waitUntil: 'domcontentloaded' })

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: '导出报告' }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toContain('R-002')

    await page.getByRole('button', { name: '查看详情' }).click()
    await expect(page.getByText('已定位到 R-002 测试报告详情')).toBeVisible()

    await page.getByRole('button', { name: '分享链接' }).click()
    await expect(page.getByText('分享链接已复制')).toBeVisible()

    await page.getByRole('button', { name: '创建缺陷' }).first().click()
    await expect(page).toHaveURL(/\/projects\/1\/defects\?/)
    await expect(page.getByPlaceholder('缺陷标题（必填）')).toHaveValue('失败用例缺陷：支付-微信支付回调验签')
    await expect(page.getByPlaceholder('错误信息（可选）')).toHaveValue('statusCode expected 200 but got 500')
  })
})
