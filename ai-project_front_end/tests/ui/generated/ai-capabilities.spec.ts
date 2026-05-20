import { expect, test } from '@playwright/test'

test.describe('ai-capabilities AI 能力中心冒烟', () => {
  test('页面标题与三个能力卡片可见', async ({ page }) => {
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
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/ai-capabilities', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/projects\/1\/settings\/ai-capabilities/)
    await expect(page.locator('div').filter({ hasText: /^AI 能力中心$/ })).toBeVisible()
    await expect(page.getByText('需求智能分析')).toBeVisible()
    await expect(page.getByText('AI 用例生成')).toBeVisible()
    await expect(page.getByText('变更影响分析', { exact: true })).toBeVisible()
    await expect(page.getByText('可用').first()).toBeVisible()
  })

  test('能力卡片跳转链接正确', async ({ page }) => {
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
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/ai-capabilities', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('link', { name: '进入需求文档' }).first()).toBeVisible()
    await expect(page.getByRole('link', { name: '进入用例管理' })).toBeVisible()
  })
})
