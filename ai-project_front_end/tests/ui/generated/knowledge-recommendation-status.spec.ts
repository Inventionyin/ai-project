import { expect, test } from '@playwright/test'

test.describe('knowledge recommendation status smoke', () => {
  test('登录页与推荐建议模块可见', async ({ page }) => {
    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      const isApiLike = req.resourceType() !== 'document'

      if (!isApiLike) {
        await route.continue()
        return
      }

      if (path === '/api/projects/1' || path === '/projects/1') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { id: '1', name: 'P1', ownerId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' }
          })
        })
        return
      }

      if (path === '/api/projects/1/knowledge/retrospectives' || path === '/projects/1/knowledge/retrospectives') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [{ id: 'r1', projectId: '1', title: 'retrospective-1', sourceType: 'OTHER', status: 'DRAFT' }],
              total: 1,
              page: 1,
              pageSize: 20
            }
          })
        })
        return
      }

      if (path === '/api/projects/1/knowledge/retrospectives/r1' || path === '/projects/1/knowledge/retrospectives/r1') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: 'r1',
              projectId: '1',
              title: 'retrospective-1',
              sourceType: 'OTHER',
              status: 'DRAFT',
              problemSummary: 'p',
              rootCause: 'r',
              decision: 'd',
              actionItems: 'a'
            }
          })
        })
        return
      }

      if (path === '/api/projects/1/knowledge/recommendations/evaluate' || path === '/projects/1/knowledge/recommendations/evaluate') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              targetType: 'RETROSPECTIVE',
              targetId: 'r1',
              recommendations: []
            }
          })
        })
        return
      }

      await route.continue()
    })
    await page.goto('/login')

    await expect(page.getByRole('heading', { name: 'WeiTesting' })).toBeVisible()
    await page.evaluate(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/knowledge/retrospectives')

    await expect(page.getByText('复盘中心').first()).toBeVisible()
    await expect(page.getByText('推荐建议').first()).toBeVisible()
  })
})
