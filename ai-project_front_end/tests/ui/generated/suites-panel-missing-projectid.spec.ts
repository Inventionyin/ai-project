import { expect, test } from '@playwright/test'

test.describe('SuitesPanel 缺失 projectId', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.route('**/api/**', async (route) => {
      const path = new URL(route.request().url()).pathname
      if (path === '/api/auth/me') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { userId: 'u1', username: 'qa' } })
        })
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, data: {} })
      })
    })
  })

  test('projectId 为空白时不回退到 project 1', async ({ page }) => {
    await page.goto('/projects/%20/assets/suites', { waitUntil: 'domcontentloaded' })

    await expect(page).toHaveURL(/\/projects\/%20\/assets\/suites$/)
    await page.waitForTimeout(800)
    await expect(page).not.toHaveURL(/\/projects\/1\/assets\/suites/)
  })
})
