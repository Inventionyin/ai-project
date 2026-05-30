import { expect, test } from '@playwright/test'

test.describe('用例详情路由与接口编码', () => {
  const rawProjectId = 'team/A&B?Q=1'
  const encodedProjectId = encodeURIComponent(rawProjectId)
  const rawCaseId = 'case/01?# smoke'
  const encodedCaseId = encodeURIComponent(rawCaseId)

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

      if (path === `/api/projects/${encodedProjectId}`) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: rawProjectId, name: 'Encoded Project' } })
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

      if (path === '/api/testcases/owners') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [{ id: 'u1', username: 'qa' }] })
        })
        return
      }

      if (path === '/api/testcases' && url.searchParams.get('projectId') === rawProjectId) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              page: 1,
              pageSize: 20,
              total: 1,
              items: [
                {
                  id: rawCaseId,
                  testCaseId: 'TC-ENC-001',
                  title: '编码详情用例',
                  version: 'v1',
                  type: '接口',
                  priority: 'P0',
                  status: 'REVIEWED',
                  lastRun: 'PASSED',
                  updatedAt: 1710000000,
                  tags: ['编码'],
                  feature: '详情页',
                  apiMethod: 'POST',
                  apiUrl: '/api/encoded',
                  expectedResult: '成功返回',
                  ownerId: 'u1'
                }
              ]
            }
          })
        })
        return
      }

      if (path === `/api/testcases/${encodedCaseId}`) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: rawCaseId,
              projectId: rawProjectId,
              testCaseId: 'TC-ENC-001',
              title: '编码详情用例',
              version: 'v1.0',
              type: 'API',
              priority: 'P0',
              status: 'REVIEWED',
              tags: ['编码'],
              ownerId: 'u1',
              ownerName: 'qa',
              contentMd: '## detail',
              feature: '详情页',
              apiMethod: 'POST',
              apiUrl: '/api/encoded',
              apiParams: {},
              apiHeaders: {},
              expectedResult: '成功返回'
            }
          })
        })
        return
      }

      if (path === `/api/testcases/${encodedCaseId}/bindings`) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([])
        })
        return
      }

      await route.continue()
    })
  })

  test('列表进入详情页时前端路由与详情接口都使用编码后的 ID', async ({ page }) => {
    const requestPaths: string[] = []
    page.on('request', (request) => {
      requestPaths.push(new URL(request.url()).pathname)
    })

    await page.goto(`/projects/${encodedProjectId}/assets/testcases`, { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('编码详情用例')).toBeVisible()

    await page.getByRole('button', { name: '编码详情用例' }).click()
    await expect(page).toHaveURL(new RegExp(`/projects/${encodedProjectId}/assets/testcases/${encodedCaseId}\\?tab=basic$`))
    await expect(page.getByLabel('测试用例ID')).toHaveValue('TC-ENC-001')
    expect(requestPaths).toContain(`/api/testcases/${encodedCaseId}`)
    expect(requestPaths).toContain(`/api/testcases/${encodedCaseId}/bindings`)
  })
})
