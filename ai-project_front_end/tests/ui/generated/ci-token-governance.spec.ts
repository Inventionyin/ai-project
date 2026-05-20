import { expect, test } from '@playwright/test'

test.describe('ci-token-governance 设置页冒烟', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })
  })

  test('状态与策略可见', async ({ page }) => {
    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      if (req.resourceType() === 'document') return route.continue()
      if (path === '/api/projects/1') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } }) })
      }
      if (path === '/api/runs/ci-token/status') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              projectId: '1',
              enabled: true,
              state: 'active',
              hint: 'ci_x...abcd',
              rotatedAt: 1710000000,
              lastUsedAt: 1710000300,
              rotatedBy: 'user-1',
              expiresAt: 1893456000,
              revokedAt: null,
              revokedBy: null,
              revokedReason: null,
              leakReportedAt: null,
              leakReportedBy: null,
              leakReportReason: null,
              policy: { allowedRunnerTypes: ['DEFAULT'], allowedTestCaseIds: ['55555555-5555-5555-5555-555555555555'], maxTestCaseCount: 3 }
            }
          })
        })
      }
      return route.continue()
    })

    await page.goto('/projects/1/settings/ci-token-governance', { waitUntil: 'domcontentloaded' })

    await expect(page.locator('div').filter({ hasText: /^CI Token 治理$/ })).toBeVisible()
    await expect(page.getByText('已启用')).toBeVisible()
    await expect(page.getByText('ci_x...abcd')).toBeVisible()
    await expect(page.getByText('过期时间：')).toBeVisible()
    await expect(page.getByPlaceholder('DEFAULT,PYTEST_ALLURE')).toHaveValue('DEFAULT')
    await expect(page.getByPlaceholder('uuid1,uuid2')).toHaveValue('55555555-5555-5555-5555-555555555555')
    await expect(page.getByRole('spinbutton')).toHaveValue('3')
  })

  test('保存策略与轮换 Token', async ({ page }) => {
    let saved = false
    let rotated = false
    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      if (req.resourceType() === 'document') return route.continue()
      if (path === '/api/projects/1') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } }) })
      }
      if (path === '/api/runs/ci-token/status') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { projectId: '1', enabled: true, state: 'active', hint: 'ci_x...abcd', rotatedAt: 1710000000, lastUsedAt: null, rotatedBy: 'user-1', expiresAt: null, revokedAt: null, revokedBy: null, revokedReason: null, leakReportedAt: null, leakReportedBy: null, leakReportReason: null, policy: { allowedRunnerTypes: [], allowedTestCaseIds: [], maxTestCaseCount: null } }
          })
        })
      }
      if (path === '/api/runs/ci-token/policy') {
        saved = true
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { projectId: '1', enabled: true, state: 'active', hint: 'ci_x...abcd', rotatedAt: 1710000000, lastUsedAt: null, rotatedBy: 'user-1', expiresAt: null, revokedAt: null, revokedBy: null, revokedReason: null, leakReportedAt: null, leakReportedBy: null, leakReportReason: null, policy: { allowedRunnerTypes: ['PYTEST_ALLURE'], allowedTestCaseIds: [], maxTestCaseCount: 2 } }
          })
        })
      }
      if (path === '/api/runs/ci-token/rotate') {
        rotated = true
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { projectId: '1', enabled: true, state: 'active', token: 'ci_new_secret', hint: 'ci_n...cret', rotatedAt: 1710000900, lastUsedAt: null, rotatedBy: 'user-1', expiresAt: null, revokedAt: null, revokedBy: null, revokedReason: null, leakReportedAt: null, leakReportedBy: null, leakReportReason: null, policy: { allowedRunnerTypes: ['PYTEST_ALLURE'], allowedTestCaseIds: [], maxTestCaseCount: 2 } }
          })
        })
      }
      return route.continue()
    })

    await page.goto('/projects/1/settings/ci-token-governance', { waitUntil: 'domcontentloaded' })
    await page.getByPlaceholder('DEFAULT,PYTEST_ALLURE').fill('PYTEST_ALLURE')
    await page.getByRole('spinbutton').fill('2')
    await page.getByRole('button', { name: '保存策略' }).click()
    await expect(page.getByText('策略已保存')).toBeVisible()
    expect(saved).toBe(true)

    await page.getByRole('button', { name: '轮换 Token' }).click()
    await expect(page.getByText('Token 已轮换')).toBeVisible()
    await expect(page.getByText('ci_new_secret')).toBeVisible()
    expect(rotated).toBe(true)
  })

  test('吊销与泄露上报显示生命周期状态', async ({ page }) => {
    let revoked = false
    let leaked = false
    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      if (req.resourceType() === 'document') return route.continue()
      if (path === '/api/projects/1') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } }) })
      }
      if (path === '/api/runs/ci-token/status') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { projectId: '1', enabled: true, state: 'active', hint: 'ci_x...abcd', rotatedAt: 1710000000, lastUsedAt: null, rotatedBy: 'user-1', expiresAt: 1893456000, revokedAt: null, revokedBy: null, revokedReason: null, leakReportedAt: null, leakReportedBy: null, leakReportReason: null, policy: { allowedRunnerTypes: [], allowedTestCaseIds: [], maxTestCaseCount: null } }
          })
        })
      }
      if (path === '/api/runs/ci-token' && req.method() === 'DELETE') {
        revoked = true
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { projectId: '1', enabled: false, state: 'revoked', hint: 'ci_x...abcd', rotatedAt: 1710000000, lastUsedAt: null, rotatedBy: 'user-1', expiresAt: 1893456000, revokedAt: 1710001000, revokedBy: 'user-1', revokedReason: '手动吊销', leakReportedAt: null, leakReportedBy: null, leakReportReason: null, policy: { allowedRunnerTypes: [], allowedTestCaseIds: [], maxTestCaseCount: null } }
          })
        })
      }
      if (path === '/api/runs/ci-token/report-leak') {
        leaked = true
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { projectId: '1', enabled: false, state: 'leaked', hint: 'ci_x...abcd', rotatedAt: 1710000000, lastUsedAt: null, rotatedBy: 'user-1', expiresAt: 1893456000, revokedAt: null, revokedBy: null, revokedReason: null, leakReportedAt: 1710002000, leakReportedBy: 'user-1', leakReportReason: 'CI 日志泄露', policy: { allowedRunnerTypes: [], allowedTestCaseIds: [], maxTestCaseCount: null } }
          })
        })
      }
      return route.continue()
    })

    await page.goto('/projects/1/settings/ci-token-governance', { waitUntil: 'domcontentloaded' })
    await page.getByPlaceholder('吊销/泄露原因，可选').fill('手动吊销')
    await page.getByRole('button', { name: '吊销 Token' }).click()
    await expect(page.getByText('Token 已吊销')).toBeVisible()
    await expect(page.getByText('状态：已吊销')).toBeVisible()
    await expect(page.getByText('吊销原因：手动吊销')).toBeVisible()
    expect(revoked).toBe(true)

    await page.getByPlaceholder('吊销/泄露原因，可选').fill('CI 日志泄露')
    await page.getByRole('button', { name: '上报泄露' }).click()
    await expect(page.getByText('泄露已上报')).toBeVisible()
    await expect(page.getByText('状态：已泄露')).toBeVisible()
    await expect(page.getByText('泄露原因：CI 日志泄露')).toBeVisible()
    expect(leaked).toBe(true)
  })
})
