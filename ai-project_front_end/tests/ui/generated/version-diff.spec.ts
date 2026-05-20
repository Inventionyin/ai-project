import { expect, test } from '@playwright/test'

test.describe('version-diff 版本差异概览冒烟', () => {
  test('变更集详情页展示版本差异概览', async ({ page }) => {
    const mockChangeSet = {
      id: 'cs-001',
      docId: 'doc-001',
      projectId: '1',
      baselineVersionId: 'ver-v1',
      targetVersionId: 'ver-v2',
      status: 'COMPLETED',
      summary: 'PRD v1 → v2 变更分析',
      createdAt: 1700000000,
      items: [
        { id: 'ci-001', changeType: 'ADDED', impactLevel: 'HIGH', title: '新增用户登录功能', description: '支持手机号验证码登录', sourcePath: '3.1 登录模块' },
        { id: 'ci-002', changeType: 'REMOVED', impactLevel: 'MEDIUM', title: '移除旧版注册流程', description: '不再支持邮箱注册', sourcePath: '3.2 注册模块' },
        { id: 'ci-003', changeType: 'UPDATED', impactLevel: 'LOW', title: '修改密码策略', description: '密码最小长度从 6 位改为 8 位', sourcePath: '3.3 安全策略' }
      ]
    }

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
      if (path.includes('/change-sets/cs-001')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: mockChangeSet }) })
        return
      }
      if (path.includes('/change-sets') && !path.includes('/cs-001')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if (path.includes('/regression-sets')) {
        await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ code: 1, message: 'not found' }) })
        return
      }
      if (path.includes('/knowledge/recommendations')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { targetType: 'CHANGE_SET', targetId: 'cs-001', recommendations: [] } }) })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/requirements/change-sets/cs-001', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('版本差异概览')).toBeVisible()
    await expect(page.getByText('+1 新增')).toBeVisible()
    await expect(page.getByText('-1 移除')).toBeVisible()
    await expect(page.getByText('~1 修改')).toBeVisible()
    await expect(page.getByText('新增用户登录功能').first()).toBeVisible()
    await expect(page.getByText('移除旧版注册流程').first()).toBeVisible()
    await expect(page.getByText('修改密码策略').first()).toBeVisible()
  })

  test('影响级别分布条可见', async ({ page }) => {
    const mockChangeSet = {
      id: 'cs-002',
      docId: 'doc-001',
      projectId: '1',
      baselineVersionId: 'ver-v1',
      targetVersionId: 'ver-v3',
      status: 'COMPLETED',
      summary: '高影响变更',
      createdAt: 1700000000,
      items: [
        { id: 'ci-004', changeType: 'ADDED', impactLevel: 'CRITICAL', title: '支付模块', description: '新增支付功能' },
        { id: 'ci-005', changeType: 'UPDATED', impactLevel: 'HIGH', title: '订单流程', description: '修改订单状态机' }
      ]
    }

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
      if (path.includes('/change-sets/cs-002')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: mockChangeSet }) })
        return
      }
      if (path.includes('/change-sets') && !path.includes('/cs-002')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if (path.includes('/regression-sets')) {
        await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ code: 1, message: 'not found' }) })
        return
      }
      if (path.includes('/knowledge/recommendations')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { targetType: 'CHANGE_SET', targetId: 'cs-002', recommendations: [] } }) })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/requirements/change-sets/cs-002', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('影响级别分布')).toBeVisible()
    await expect(page.getByText('CRITICAL 1')).toBeVisible()
    await expect(page.getByText('HIGH 1')).toBeVisible()
  })
})
