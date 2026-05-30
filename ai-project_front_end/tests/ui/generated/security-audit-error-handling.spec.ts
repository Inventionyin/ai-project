import { expect, test } from '@playwright/test'

test.describe('security-audit 请求失败处理', () => {
  test('请求失败时展示错误提示且不出现未处理异常', async ({ page }) => {
    const pageErrors: Error[] = []
    page.on('pageerror', (error) => {
      pageErrors.push(error)
    })

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
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } }),
        })
        return
      }

      if (path.startsWith('/api/projects/1/security/audit-logs')) {
        await route.abort('failed')
        return
      }

      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/security-audit', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('审计日志加载失败，请检查网络后重试')).toBeVisible()

    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByText('审计日志加载失败，请检查网络后重试')).toBeVisible()
    expect(pageErrors).toHaveLength(0)
  })
})
