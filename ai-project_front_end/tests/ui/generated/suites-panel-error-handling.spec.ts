import { expect, test } from '@playwright/test'

test.describe('SuitesPanel 请求失败处理', () => {
  test('套件加载失败时展示错误提示且不出现原生弹窗', async ({ page }) => {
    const dialogs: string[] = []
    page.on('dialog', (dialog) => {
      dialogs.push(dialog.message())
      void dialog.dismiss()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.route('**/*', async (route) => {
      const req = route.request()
      if (req.resourceType() === 'document') {
        await route.continue()
        return
      }

      const url = new URL(req.url())
      const path = url.pathname

      if (path === '/api/projects/1') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } })
        })
        return
      }

      if (path === '/api/suites') {
        await route.abort('failed')
        return
      }

      await route.continue()
    })

    await page.goto('/projects/1/assets/suites', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('获取测试套件失败，请检查网络后重试')).toBeVisible()

    await page.getByRole('button', { name: '重试' }).click()
    await expect(page.getByText('获取测试套件失败，请检查网络后重试')).toBeVisible()
    expect(dialogs).toHaveLength(0)
  })
})
