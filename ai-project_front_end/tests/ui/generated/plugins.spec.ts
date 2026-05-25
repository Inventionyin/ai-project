import { expect, test } from '@playwright/test'

test.describe('plugins 管理页冒烟', () => {
  test('页面标题与插件市场 Tab 可见', async ({ page }) => {
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
      if (path.startsWith('/api/plugins')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 20, total: 0, items: [] } })
        })
        return
      }
      if (path.startsWith('/api/projects/1/plugins')) {
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

    await page.goto('/projects/1/settings/plugins', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/projects\/1\/settings\/plugins/)
    await expect(page.getByRole('navigation').getByRole('button', { name: '插件市场' })).toBeVisible()
    await expect(page.getByRole('button', { name: '已安装' })).toBeVisible()
    await expect(page.getByText('暂无可用插件')).toBeVisible()
  })

  test('mock 插件列表与安装按钮', async ({ page }) => {
    const mockPlugins = [
      {
        id: 'plugin-001',
        name: 'JMeter 插件',
        slug: 'jmeter-plugin',
        description: 'JMeter 性能测试插件',
        version: '1.0.0',
        author: 'WeiTesting',
        pluginType: 'executor',
        configSchema: null,
        entryPoint: null,
        minPlatformVersion: null,
        iconUrl: null,
        enabled: true,
        status: 'AVAILABLE',
        downloadCount: 42,
        createdAt: 1700000000,
        updatedAt: 1700000000
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
      if (path.startsWith('/api/plugins')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 20, total: 1, items: mockPlugins } })
        })
        return
      }
      if (path.startsWith('/api/projects/1/plugins')) {
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

    await page.goto('/projects/1/settings/plugins', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('JMeter 插件', { exact: true })).toBeVisible()
    await expect(page.getByText('JMeter 性能测试插件', { exact: true })).toBeVisible()
    await expect(page.getByText('v1.0.0').last()).toBeVisible()
    await expect(page.getByText('下载: 42', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: '安装到项目' })).toBeVisible()
  })

  test('已安装 Tab 与空状态', async ({ page }) => {
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
      if (path.startsWith('/api/plugins')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 20, total: 0, items: [] } })
        })
        return
      }
      if (path.startsWith('/api/projects/1/plugins')) {
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

    await page.goto('/projects/1/settings/plugins', { waitUntil: 'domcontentloaded' })
    await page.getByRole('button', { name: '已安装' }).click()
    await expect(page.getByText('暂未安装插件')).toBeVisible()
  })

  test('已安装插件 invoke 调用与成功反馈', async ({ page }) => {
    const mockInstallations = [
      {
        id: 'inst-001',
        projectId: '1',
        pluginId: 'plugin-001',
        pluginName: 'JMeter 插件',
        pluginSlug: 'jmeter-plugin',
        status: 'INSTALLED',
        config: null,
        installedVersion: '1.0.0',
        errorMessage: null,
        installedBy: 'user-1',
        createdAt: 1700000000,
        updatedAt: 1700000000
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
      if (path.startsWith('/api/plugins')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 20, total: 0, items: [] } }) })
        return
      }
      if (path.endsWith('/invoke')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { installationId: 'inst-001', pluginId: 'plugin-001', pluginSlug: 'jmeter-plugin', status: 'SUCCESS' } })
        })
        return
      }
      if (path.endsWith('/invocations')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 20, total: 1, items: [{ id: 'inv-001', installationId: 'inst-001', pluginId: 'plugin-001', pluginSlug: 'jmeter-plugin', invokedBy: 'user-1', status: 'SUCCESS', createdAt: 1700000000 }] } })
        })
        return
      }
      if (path.startsWith('/api/projects/1/plugins')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 20, total: 1, items: mockInstallations } }) })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/plugins', { waitUntil: 'domcontentloaded' })
    await page.getByRole('button', { name: '已安装' }).click()
    await expect(page.getByText('JMeter 插件', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: '调用' })).toBeVisible()
    await page.getByRole('button', { name: '调用' }).click()
    await expect(page.getByText('调用成功')).toBeVisible()
    await expect(page.getByText('调用记录')).toBeVisible()
    await expect(page.getByText('inv-001')).toBeVisible()
    await expect(page.getByText('user-1')).toBeVisible()
  })

  test('插件列表接口异常时页面保持可操作并回落空状态', async ({ page }) => {
    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      if (req.resourceType() === 'document') {
        await route.continue()
        return
      }
      if (path === '/api/auth/me' || path === '/auth/me') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: 'u1', username: 'qa', roles: ['Admin'] } })
        })
        return
      }
      if (path.startsWith('/api/plugins')) {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 1, message: 'plugins unavailable' })
        })
        return
      }
      if (path.startsWith('/api/projects/1/plugins')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 20, total: 0, items: [] } })
        })
        return
      }
      if (path.startsWith('/api/') || path.startsWith('/auth/')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: {} }) })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/plugins', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('navigation').getByRole('button', { name: '插件市场' })).toBeVisible()
    await expect(page.getByRole('button', { name: '已安装' })).toBeVisible()
    await expect(page.getByText('暂无可用插件')).toBeVisible()
  })
})
