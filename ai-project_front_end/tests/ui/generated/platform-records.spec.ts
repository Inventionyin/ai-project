import { expect, test } from '@playwright/test'

test.describe('platform-records 平台记录页冒烟', () => {
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
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } }) })
        return
      }
      if (path.includes('/platform/ai-jobs')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if (path.includes('/platform/audit-logs')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/platform-records', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/projects\/1\/settings\/platform-records/)
    await expect(page.locator('h1').filter({ hasText: /^平台记录$/ })).toBeVisible()
    await expect(page.getByRole('button', { name: '刷新' })).toBeVisible()
    await expect(page.getByText('AI 任务')).toBeVisible()
    await expect(page.getByRole('heading', { name: '审计日志' })).toBeVisible()
    await expect(page.getByText('暂无记录').first()).toBeVisible()
  })

  test('mock AI 任务与审计日志表格数据', async ({ page }) => {
    const mockJobs = [
      {
        id: 'job-001',
        projectId: '1',
        jobType: 'REQUIREMENT_ANALYSIS',
        status: 'SUCCESS',
        triggerSource: 'MANUAL',
        summary: '分析需求文档 PRD-v2',
        createdBy: 'user-1',
        createdAt: 1700000000
      },
      {
        id: 'job-002',
        projectId: '1',
        jobType: 'CHANGE_ANALYSIS',
        status: 'FAILED',
        triggerSource: 'AUTO',
        summary: '变更分析失败: 版本不存在',
        createdBy: 'user-1',
        createdAt: 1700001000
      }
    ]

    const mockLogs = [
      {
        id: 'log-001',
        projectId: '1',
        module: 'requirements',
        action: 'CREATE',
        resourceType: 'requirement_doc',
        resourceId: 'doc-001',
        summary: '创建需求文档: PRD-v2',
        detail: {},
        userId: 'user-1',
        createdAt: 1700000000
      },
      {
        id: 'log-002',
        projectId: '1',
        module: 'testcases',
        action: 'UPDATE',
        resourceType: 'test_case',
        resourceId: 'case-001',
        summary: '更新测试用例: 登录流程',
        detail: {},
        userId: 'user-2',
        createdAt: 1700001000
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
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } }) })
        return
      }
      if (path.includes('/platform/ai-jobs')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: mockJobs }) })
        return
      }
      if (path.includes('/platform/audit-logs')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: mockLogs }) })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/platform-records', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('REQUIREMENT_ANALYSIS')).toBeVisible()
    await expect(page.getByText('CHANGE_ANALYSIS')).toBeVisible()
    await expect(page.getByText('分析需求文档 PRD-v2')).toBeVisible()
    await expect(page.getByRole('cell', { name: 'requirements', exact: true })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'testcases', exact: true })).toBeVisible()
    await expect(page.getByText('创建需求文档: PRD-v2')).toBeVisible()
  })
})
