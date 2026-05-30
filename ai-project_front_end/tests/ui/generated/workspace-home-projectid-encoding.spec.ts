import { expect, test } from '@playwright/test'

test.describe('workspace section home projectId 编码', () => {
  const rawProjectId = 'team/A&B?Q=1'
  const encodedProjectId = encodeURIComponent(rawProjectId)

  test.beforeEach(async ({ page }) => {
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

      if (path.startsWith('/api/projects/') && req.method() === 'GET' && !path.includes('/workspace/summary')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: rawProjectId, name: 'Encoded Project' } })
        })
        return
      }

      if (path === `/api/projects/${encodedProjectId}/workspace/summary`) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              assets: { requirementDocs: 1, testcases: 2, formalCases: 1, testPoints: 3, apiCollections: 1, apiRequests: 4, suites: 1 },
              automation: { runs: 1, executedCaseRuns: 1, passRate: 100, latestRunAt: 1710000000 },
              risks: { defects: 0, p0Open: 0, riskHints: 0 },
              capabilities: { role: 'admin', assets: true, ai: true, automation: true, settings: true, ops: true }
            }
          })
        })
        return
      }

      if (path === '/api/auth/me') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { userId: 'u1', username: 'qa' } })
        })
        return
      }

      await route.continue()
    })
  })

  test('四个 section 的入口链接都使用编码后的 projectId', async ({ page }) => {
    await page.goto(`/projects/${encodedProjectId}/assets`, { waitUntil: 'domcontentloaded' })
    await expect(page.locator(`a[href="/projects/${encodedProjectId}/requirements/docs"]`).first()).toBeVisible()
    await expect(page.locator(`a[href="/projects/${encodedProjectId}/assets/testcases"]`).first()).toBeVisible()

    await page.goto(`/projects/${encodedProjectId}/ai`, { waitUntil: 'domcontentloaded' })
    await expect(page.locator(`a[href="/projects/${encodedProjectId}/ai/generate-cases"]`).first()).toBeVisible()
    await expect(page.locator(`a[href="/projects/${encodedProjectId}/ai/requirements"]`).first()).toBeVisible()

    await page.goto(`/projects/${encodedProjectId}/automation`, { waitUntil: 'domcontentloaded' })
    await expect(page.locator(`a[href="/projects/${encodedProjectId}/automation/ui"]`).first()).toBeVisible()
    await expect(page.locator(`a[href="/projects/${encodedProjectId}/runs"]`).first()).toBeVisible()

    await page.goto(`/projects/${encodedProjectId}/settings`, { waitUntil: 'domcontentloaded' })
    await expect(page.locator(`a[href="/projects/${encodedProjectId}/settings/rbac"]`).first()).toBeVisible()
    await expect(page.locator(`a[href="/projects/${encodedProjectId}/settings/environments"]`).first()).toBeVisible()
  })
})
