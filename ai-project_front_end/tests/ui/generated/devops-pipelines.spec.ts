import { expect, test } from '@playwright/test'

test.describe('devops-pipelines 管理页冒烟', () => {
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
      if (path.startsWith('/api/projects/1/devops')) {
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

    await page.goto('/projects/1/settings/devops', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/projects\/1\/settings\/devops/)
    await expect(page.locator('div').filter({ hasText: /^DevOps 流水线$/ })).toBeVisible()
    await expect(page.getByText('暂无流水线')).toBeVisible()
    await expect(page.getByText('执行记录', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: '新建流水线' })).toBeVisible()
  })

  test('mock 流水线列表与触发按钮', async ({ page }) => {
    const mockPipelines = [
      {
        id: 'pipe-001',
        projectId: '1',
        name: 'CI Pipeline',
        provider: 'github_actions',
        repoFullName: 'org/repo',
        workflowFile: 'ci.yml',
        config: null,
        enabled: true,
        status: 'IDLE',
        createdBy: 'user-1',
        createdAt: 1700000000,
        updatedAt: 1700000000
      },
      {
        id: 'pipe-002',
        projectId: '1',
        name: 'Release Pipeline',
        provider: 'jenkins',
        repoFullName: 'org/repo',
        workflowFile: '',
        config: { jobName: 'backend-release' },
        enabled: true,
        status: 'IDLE',
        createdBy: 'user-1',
        createdAt: 1700000200,
        updatedAt: 1700000200
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
      if (path.startsWith('/api/projects/1/devops/pipelines')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 20, total: 2, items: mockPipelines } })
        })
        return
      }
      if (path.startsWith('/api/projects/1/devops/runs')) {
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

    await page.goto('/projects/1/settings/devops', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('CI Pipeline')).toBeVisible()
    await expect(page.getByText('Release Pipeline')).toBeVisible()
    await expect(page.getByText('github_actions')).toBeVisible()
    await expect(page.getByText('jenkins')).toBeVisible()
    await expect(page.getByText('已启用').first()).toBeVisible()
    await expect(page.getByRole('button', { name: '触发' }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: '删除' }).first()).toBeVisible()
  })

  test('新建流水线表单展开与收起', async ({ page }) => {
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
      if (path.startsWith('/api/projects/1/devops')) {
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

    await page.goto('/projects/1/settings/devops', { waitUntil: 'domcontentloaded' })
    await expect(page.locator('div').filter({ hasText: /^DevOps 流水线$/ })).toBeVisible()

    await page.getByRole('button', { name: '新建流水线' }).click()
    await expect(page.getByPlaceholder('流水线名称')).toBeVisible()
    await expect(page.getByPlaceholder('仓库全名 (owner/repo)')).toBeVisible()
    await expect(page.getByPlaceholder('工作流文件名 (.github/workflows/ci.yml)')).toBeVisible()

    await page.getByRole('button', { name: '取消' }).click()
    await expect(page.getByPlaceholder('流水线名称')).not.toBeVisible()
  })

  test('创建 GitHub Actions 流水线 payload 正确', async ({ page }) => {
    let createPayload: Record<string, unknown> | null = null

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
      if (path === '/api/projects/1/devops/pipelines' && req.method() === 'POST') {
        createPayload = JSON.parse(req.postData() || '{}')
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: 'pipe-new',
              projectId: '1',
              name: (createPayload as any).name,
              provider: (createPayload as any).provider,
              repoFullName: (createPayload as any).repoFullName ?? null,
              workflowFile: (createPayload as any).workflowFile ?? null,
              config: (createPayload as any).config ?? null,
              enabled: true,
              status: 'IDLE',
              createdBy: 'user-1',
              createdAt: 1700000000,
              updatedAt: 1700000000
            }
          })
        })
        return
      }
      if (path.startsWith('/api/projects/1/devops/pipelines') || path.startsWith('/api/projects/1/devops/runs')) {
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

    await page.goto('/projects/1/settings/devops', { waitUntil: 'domcontentloaded' })
    await page.getByRole('button', { name: '新建流水线' }).click()
    await page.getByPlaceholder('流水线名称').fill('GH Pipeline')
    await page.getByPlaceholder('仓库全名 (owner/repo)').fill('org/repo')
    await page.getByPlaceholder('工作流文件名 (.github/workflows/ci.yml)').fill('.github/workflows/ci.yml')
    await page.getByPlaceholder('GitHub Token (仅用于触发)').fill('ghp_fake_token')
    await page.getByPlaceholder('默认分支 (main)').fill('main')
    await page.getByRole('button', { name: '创建' }).click()

    await expect.poll(() => createPayload).not.toBeNull()
    expect(createPayload).toEqual({
      name: 'GH Pipeline',
      provider: 'github_actions',
      repoFullName: 'org/repo',
      workflowFile: '.github/workflows/ci.yml',
      config: {
        githubToken: 'ghp_fake_token',
        defaultBranch: 'main'
      }
    })
  })

  test('创建 Jenkins 流水线 payload 正确，且缺必填不提交', async ({ page }) => {
    let createPayload: Record<string, unknown> | null = null
    let postCount = 0

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
      if (path === '/api/projects/1/devops/pipelines' && req.method() === 'POST') {
        postCount += 1
        createPayload = JSON.parse(req.postData() || '{}')
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: 'pipe-new',
              projectId: '1',
              name: (createPayload as any).name,
              provider: (createPayload as any).provider,
              repoFullName: null,
              workflowFile: null,
              config: (createPayload as any).config ?? null,
              enabled: true,
              status: 'IDLE',
              createdBy: 'user-1',
              createdAt: 1700000000,
              updatedAt: 1700000000
            }
          })
        })
        return
      }
      if (path.startsWith('/api/projects/1/devops/pipelines') || path.startsWith('/api/projects/1/devops/runs')) {
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

    await page.goto('/projects/1/settings/devops', { waitUntil: 'domcontentloaded' })
    await page.getByRole('button', { name: '新建流水线' }).click()
    await page.locator('select').selectOption('jenkins')
    await page.getByPlaceholder('流水线名称').fill('Jenkins Pipeline')
    await page.getByRole('button', { name: '创建' }).click()
    await expect(page.getByText('Jenkins 请填写 name、baseUrl、jobName、username、apiToken')).toBeVisible()
    expect(postCount).toBe(0)

    await page.getByPlaceholder('Jenkins Base URL (https://jenkins.example.com)').fill('https://jenkins.example.com')
    await page.getByPlaceholder('Job 名称').fill('build-api')
    await page.getByPlaceholder('Jenkins 用户名').fill('jenkins-bot')
    await page.getByPlaceholder('Jenkins API Token').fill('jenkins_fake_token')
    await page.getByPlaceholder('Crumb (可选)').fill('crumb-123')
    await page.getByPlaceholder('Trigger Token (可选)').fill('trigger-123')
    await page.getByRole('button', { name: '创建' }).click()

    await expect.poll(() => postCount).toBe(1)
    expect(createPayload).toEqual({
      name: 'Jenkins Pipeline',
      provider: 'jenkins',
      config: {
        baseUrl: 'https://jenkins.example.com',
        jobName: 'build-api',
        username: 'jenkins-bot',
        apiToken: 'jenkins_fake_token',
        crumb: 'crumb-123',
        triggerToken: 'trigger-123'
      }
    })
  })
})
