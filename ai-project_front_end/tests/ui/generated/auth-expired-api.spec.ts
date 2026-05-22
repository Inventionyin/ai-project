import { expect, test } from '@playwright/test'

test.describe('expired api token handling', () => {
  test('clears stale token and redirects to login when api returns 40101', async ({ page }) => {
    await page.route('**/*', async (route) => {
      const path = new URL(route.request().url()).pathname
      if (!path.startsWith('/api/')) {
        await route.continue()
        return
      }
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 40101,
          message: 'Invalid token',
          data: null,
          requestId: 'e2e-expired-token'
        })
      })
    })

    await page.goto('/login', { waitUntil: 'domcontentloaded' })
    await page.evaluate(() => {
      localStorage.setItem('accessToken', 'stale-e2e-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
      localStorage.setItem('loginUsername', 'stale-user')
    })

    await page.goto('/projects/1/trial-operation', { waitUntil: 'domcontentloaded' })

    await expect(page).toHaveURL(/\/login\?redirect=%2Fprojects%2F1%2Ftrial-operation/)
    await expect.poll(() => page.evaluate(() => localStorage.getItem('accessToken'))).toBeNull()
    await expect.poll(() => page.evaluate(() => localStorage.getItem('accessTokenExpiresAt'))).toBeNull()
    await expect.poll(() => page.evaluate(() => localStorage.getItem('loginUsername'))).toBeNull()
  })
})
