import { expect, test } from '@playwright/test'

test.describe('doc-parse-jobs 管理页冒烟', () => {
  test('页面标题与空状态可见', async ({ page }) => {
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
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } })
        })
        return
      }
      if (path.startsWith('/api/projects/1/doc-parse-jobs')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 20, total: 0, items: [] } })
        })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/doc-parse-jobs', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/projects\/1\/settings\/doc-parse-jobs/)
    await expect(page.getByText('文档异步解析任务')).toBeVisible()
    await expect(page.getByText('暂无解析任务')).toBeVisible()
    await expect(page.getByRole('button', { name: '刷新' })).toBeVisible()
  })

  test('mock 数据表格与重试按钮', async ({ page }) => {
    const mockJobs = [
      {
        id: 'job-001',
        projectId: '1',
        docId: 'doc-aaa',
        docVersionId: 'ver-111',
        status: 'SUCCESS',
        attempts: 1,
        maxRetries: 3,
        errorMessage: null,
        result: { textLength: 4200 },
        createdBy: 'user-1',
        createdAt: 1700000000,
        updatedAt: 1700000100
      },
      {
        id: 'job-002',
        projectId: '1',
        docId: 'doc-bbb',
        docVersionId: 'ver-222',
        status: 'FAILED',
        attempts: 3,
        maxRetries: 3,
        errorMessage: 'Source file not found',
        result: null,
        createdBy: 'user-1',
        createdAt: 1700001000,
        updatedAt: 1700001200
      }
    ]

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
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } })
        })
        return
      }
      if (path.startsWith('/api/projects/1/doc-parse-jobs')) {
        if (path.includes('/retry')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ code: 0, data: { ...mockJobs[1], status: 'PENDING', attempts: 0 } })
          })
          return
        }
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 20, total: 2, items: mockJobs } })
        })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/doc-parse-jobs', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('文档异步解析任务')).toBeVisible()
    await expect(page.getByText('job-001')).toBeVisible()
    await expect(page.getByText('job-002')).toBeVisible()
    await expect(page.getByRole('table').getByText('成功')).toBeVisible()
    await expect(page.getByRole('table').getByText('失败')).toBeVisible()
    await expect(page.getByText('Source file not found')).toBeVisible()
    await expect(page.getByRole('button', { name: '重试' })).toBeVisible()
    await expect(page.getByRole('button', { name: '刷新' })).toBeVisible()
  })
})
