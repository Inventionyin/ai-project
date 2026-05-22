import { expect, test } from '@playwright/test'

test.describe('risk-matrix 风险矩阵可视化冒烟', () => {
  test('分析详情页展示风险矩阵', async ({ page }) => {
    const mockAnalysis = {
      id: 'ana-001',
      docId: 'doc-001',
      docVersionId: 'ver-001',
      projectId: '1',
      status: 'GENERATED',
      summary: 'PRD v2 需求分析',
      riskLevel: 'HIGH',
      coverageScore: 85,
      analysis: {
        featurePoints: [{ title: '用户登录' }],
        businessRules: [{ title: '密码策略' }],
        testPoints: [{ title: '登录成功', status: 'DRAFT' }],
        riskPoints: [
          { title: '支付安全风险', level: 'CRITICAL', description: '支付流程未加密' },
          { title: '数据泄露风险', level: 'HIGH', description: '用户数据未脱敏' },
          { title: '性能瓶颈', level: 'MEDIUM', description: '并发超过 100 时响应慢' },
          { title: '兼容性问题', level: 'LOW', description: '旧版浏览器不支持' }
        ],
        boundaryCases: [],
        coverageSuggestions: []
      },
      createdAt: 1700000000,
      updatedAt: 1700000000
    }

    const routeApi = async (route) => {
      const url = new URL(route.request().url())
      const path = url.pathname
      if (!['fetch', 'xhr'].includes(route.request().resourceType())) {
        await route.continue()
        return
      }
      if (path === '/api/projects/1') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } }) })
        return
      }
      if (path.includes('/analyses/ana-001/revisions')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if (path.includes('/analyses/ana-001/sync-test-points')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if (path.includes('/analyses/ana-001/test-points')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if (path.includes('/analyses/ana-001/case-drafts')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if (path.includes('/analyses/ana-001/case-links')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if (path.includes('/analyses/ana-001')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: mockAnalysis }) })
        return
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: null }) })
    }
    await page.route('**/api/**', routeApi)
    await page.route('**/projects/**', routeApi)

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/requirements/analyses/ana-001', { waitUntil: 'networkidle' })
    await expect(page.getByText('风险矩阵')).toBeVisible()
    await expect(page.getByText('共 4 个风险点')).toBeVisible()
    await expect(page.getByText('支付安全风险')).toBeVisible()
    await expect(page.getByText('数据泄露风险')).toBeVisible()
    await expect(page.getByText('严重影响')).toBeVisible()
    await expect(page.getByText('高影响')).toBeVisible()
    await expect(page.getByText('CRITICAL')).toBeVisible()
    await expect(page.getByText('HIGH')).toBeVisible()
  })

  test('空风险点展示占位', async ({ page }) => {
    const mockAnalysis = {
      id: 'ana-002',
      docId: 'doc-002',
      docVersionId: 'ver-002',
      projectId: '1',
      status: 'GENERATED',
      summary: '空分析',
      riskLevel: 'LOW',
      coverageScore: 0,
      analysis: { featurePoints: [], businessRules: [], testPoints: [], riskPoints: [], boundaryCases: [], coverageSuggestions: [] },
      createdAt: 1700000000,
      updatedAt: 1700000000
    }

    const routeApi = async (route) => {
      const url = new URL(route.request().url())
      const path = url.pathname
      if (!['fetch', 'xhr'].includes(route.request().resourceType())) {
        await route.continue()
        return
      }
      if (path === '/api/projects/1') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } }) })
        return
      }
      if (path.includes('/analyses/ana-002/revisions')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if (path.includes('/analyses/ana-002/sync-test-points')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if (path.includes('/analyses/ana-002/test-points')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if (path.includes('/analyses/ana-002/case-drafts')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if (path.includes('/analyses/ana-002/case-links')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
        return
      }
      if (path.includes('/analyses/ana-002')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: mockAnalysis }) })
        return
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: null }) })
    }
    await page.route('**/api/**', routeApi)
    await page.route('**/projects/**', routeApi)

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/requirements/analyses/ana-002', { waitUntil: 'networkidle' })
    await expect(page.getByText('风险矩阵')).toBeVisible()
    await expect(page.getByText('暂无风险点')).toBeVisible()
  })
})
