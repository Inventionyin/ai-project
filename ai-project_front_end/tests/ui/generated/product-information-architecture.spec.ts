import { expect, test } from '@playwright/test'

test.describe('产品信息架构收敛', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })
    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      if (req.resourceType() === 'document') return route.continue()
      if (url.pathname === '/api/projects/1') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'E2E Project' } }),
        })
      }
      if (url.pathname === '/api/projects/1/acceptance/summary') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              overallStatus: 'BLOCKED',
              score: 54,
              generatedAt: 1710000000,
              checks: [
                {
                  key: 'realData',
                  label: '真实数据基线',
                  status: 'BLOCKED',
                  detail: '建议暂缓',
                  recommendation: '治理缺陷后复验',
                },
                {
                  key: 'externalSystems',
                  label: '外部系统联调',
                  status: 'READY',
                  detail: '外部系统已就绪',
                  recommendation: '保持 smoke',
                },
                {
                  key: 'opsHealth',
                  label: '运维可观测性',
                  status: 'READY',
                  detail: '运维健康聚合状态：READY',
                  recommendation: '保持巡检',
                },
              ],
              externalSystems: [],
              metrics: {
                requirementDocs: 31,
                testcases: 5899,
                defects: 460,
                defectClusters: 242,
                riskHints: 460,
                executedCaseRuns: 27,
              },
              nextActions: ['关闭阻塞缺陷后复验'],
            },
          }),
        })
      }
      if (url.pathname === '/api/projects/1/acceptance/report') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { markdown: '# 生产验收报告' } }),
        })
      }
      if (url.pathname === '/api/projects/1/workspace/summary') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              assets: {
                requirementDocs: 31,
                testcases: 5899,
                formalCases: 27,
                testPoints: 5872,
                apiCollections: 3,
                apiRequests: 128,
                suites: 12,
              },
              automation: {
                runs: 27,
                executedCaseRuns: 27,
                passRate: 81.5,
                latestRunAt: 1710000000,
              },
              risks: {
                defects: 460,
                p0Open: 22,
                riskHints: 460,
              },
              capabilities: {
                role: 'admin',
                assets: true,
                ai: true,
                automation: true,
                settings: true,
                ops: true,
              },
            },
          }),
        })
      }
      if (url.pathname === '/api/projects/1/dashboard/summary') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              date: '2026-05-25',
              totalRuns: 18,
              passedRuns: 15,
              failedRuns: 2,
              runningRuns: 1,
              canceledRuns: 0,
              passRate: 83.3,
            },
          }),
        })
      }
      if (url.pathname === '/api/projects/1/dashboard/failure-top') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { dimension: 'testcase', items: [] } }),
        })
      }
      if (url.pathname === '/api/projects/1/dashboard/quality-gate') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { overall: 'PASSED', gates: [] } }),
        })
      }
      if (url.pathname === '/api/projects/1/dashboard/trend') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              days: 7,
              items: [
                { date: '05-19', passRate: 80, failCount: 2, totalRuns: 10 },
                { date: '05-20', passRate: 90, failCount: 1, totalRuns: 10 },
              ],
            },
          }),
        })
      }
      if (url.pathname === '/api/runs') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 5, total: 0, items: [] } }),
        })
      }
      if (url.pathname === '/api/suites') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 200, total: 0, items: [] } }),
        })
      }
      if (url.pathname === '/api/projects/1/environments') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [] }),
        })
      }
      return route.continue()
    })
  })

  test('侧边栏按当前模块收起非当前分组', async ({ page }) => {
    await page.goto('/projects/1/settings/acceptance', { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('button', { name: /^仪表盘$/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /资产中心/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /AI能力/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /自动化执行/ })).toBeVisible()
    await expect(page.getByRole('button', { name: '设置', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: /设置总览/ })).toBeVisible()

    await expect(page.getByRole('button', { name: /资产总览/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /需求管理/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /用例管理/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /接口管理/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /测试套件/ })).not.toBeVisible()

    await expect(page.getByRole('button', { name: /AI总览/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /自动生成测试用例/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /执行总览/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /UI自动化/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /接口自动化/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /性能自动化/ })).not.toBeVisible()

    await page.getByRole('button', { name: /资产中心/ }).click()
    await expect(page.getByRole('button', { name: /资产总览/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /设置总览/ })).not.toBeVisible()

    await expect(page.getByRole('button', { name: /AI 助手/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /接口集合/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /执行中心/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /Worker 管理/ })).not.toBeVisible()
  })

  test('验收中心不再重复展示资产总量指标卡', async ({ page }) => {
    await page.goto('/projects/1/settings/acceptance', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('生产验收中心')).toBeVisible()
    await expect(page.getByText('阻塞治理概览')).toBeVisible()
    await expect(page.getByText('未关闭缺陷', { exact: true })).toBeVisible()
    await expect(page.getByText('风险提示', { exact: true })).toBeVisible()
    await expect(page.getByText('已执行用例', { exact: true })).toBeVisible()

    await expect(page.getByText('需求文档', { exact: true })).not.toBeVisible()
    await expect(page.getByText('测试用例', { exact: true })).not.toBeVisible()
    await expect(page.getByText('缺陷聚类', { exact: true })).not.toBeVisible()
  })

  test('四个一级工作台首页显示聚合指标和操作入口', async ({ page }) => {
    await page.goto('/projects/1/assets', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: '资产中心' })).toBeVisible()
    await expect(page.getByText('测试用例', { exact: true })).toBeVisible()
    await expect(page.getByText('5899', { exact: true })).toBeVisible()
    await expect(page.getByLabel('选择资产类型')).toBeVisible()
    await expect(page.getByText('统一资产操作')).toBeVisible()
    await expect(page.getByLabel('选择资产操作')).toBeVisible()
    await page.getByLabel('选择资产操作').selectOption('批量编辑')
    await expect(page.getByText('批量编辑字段、标签、模块和关联关系')).toBeVisible()
    await page.getByLabel('选择资产类型').selectOption('接口管理')
    await expect(page.getByRole('link', { name: /进入接口/ })).toHaveAttribute('href', '/projects/1/assets/apis')

    await page.goto('/projects/1/ai', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: 'AI能力' })).toBeVisible()
    await expect(page.getByText('AI 不直接改正式资产')).toBeVisible()
    await expect(page.getByLabel('选择AI任务')).toBeVisible()
    await page.getByLabel('选择AI任务').selectOption('用例治理')
    await expect(page.getByRole('link', { name: /进入治理/ })).toHaveAttribute('href', '/projects/1/ai/case-governance')
    await expect(page.getByRole('link', { name: '自动生成测试用例' })).toHaveAttribute('href', '/projects/1/ai/generate-cases')

    await page.goto('/projects/1/automation', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: '自动化执行' })).toBeVisible()
    await expect(page.getByText('81.5%')).toBeVisible()
    await expect(page.getByLabel('选择执行类型')).toBeVisible()
    await page.getByLabel('选择执行类型').selectOption('性能自动化')
    await expect(page.getByRole('link', { name: /查看性能报告/ })).toHaveAttribute('href', '/projects/1/automation/performance')
    await expect(page.getByRole('link', { name: '运行记录' })).toHaveAttribute('href', '/projects/1/runs')

    await page.goto('/projects/1/settings', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: '设置' })).toBeVisible()
    await expect(page.getByText('admin', { exact: true })).toBeVisible()
    await expect(page.getByLabel('选择配置项')).toBeVisible()
    await page.getByLabel('选择配置项').selectOption('集成配置')
    await expect(page.getByRole('link', { name: /进入集成/ })).toHaveAttribute('href', '/projects/1/settings/integrations')
    await expect(page.getByRole('link', { name: 'API Token / CI Token' })).toHaveAttribute('href', '/projects/1/settings/ci-token-governance')
  })

  test('仪表盘支持自定义模块显示并持久保存', async ({ page }) => {
    await page.goto('/projects/1/dashboard', { waitUntil: 'domcontentloaded' })

    await expect(page.getByRole('heading', { name: '近 7 天趋势' })).toBeVisible()
    await expect(page.getByText('质量门禁')).toBeVisible()
    await expect(page.getByLabel('时间范围')).toBeVisible()
    await expect(page.getByLabel('统计维度')).toBeVisible()
    await page.getByLabel('时间范围').selectOption('14')
    await page.getByLabel('统计维度').selectOption('module')
    await expect(page.getByText('当前筛选：近 14 天 · 按模块')).toBeVisible()

    await page.getByRole('button', { name: /自定义/ }).click()
    await page.getByRole('checkbox', { name: '近 7 天趋势' }).uncheck()
    await page.getByRole('button', { name: /保存布局/ }).click()

    await expect(page.getByRole('heading', { name: '近 7 天趋势' })).not.toBeVisible()
    await expect(page.getByText('布局已保存')).toBeVisible()

    await page.reload({ waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: '近 7 天趋势' })).not.toBeVisible()
    await expect(page.getByText('质量门禁')).toBeVisible()
  })

  test('AI生成页用下拉选择智能体类型', async ({ page }) => {
    await page.goto('/projects/1/ai/generate-cases', { waitUntil: 'domcontentloaded' })

    await expect(page.getByLabel('智能体类型')).toBeVisible()
    await expect(page.getByText(/^1\s*文档检查$/)).toBeVisible()
    await expect(page.getByText(/^2\s*候选用例$/)).toBeVisible()
    await expect(page.getByText(/^3\s*人工确认$/)).toBeVisible()
    await expect(page.getByText(/^4\s*正式入库$/)).toBeVisible()
    await expect(page.getByText('生成结果', { exact: true })).toBeVisible()
    await expect(page.getByText('Generation Result')).not.toBeVisible()
    await expect(page.getByText('Cloud Sync')).not.toBeVisible()
    await expect(page.getByText('生成并导入到用例列表')).not.toBeVisible()
    await expect(page.getByText('生成候选用例，确认后入库')).toBeVisible()
    await expect(page.locator('div').filter({ hasText: /^测试用例生成$/ })).toBeVisible()
    await page.getByLabel('智能体类型').selectOption('PERF')
    await expect(page.locator('div').filter({ hasText: /^性能脚本生成$/ })).toBeVisible()
    await expect(page.getByText('性能参数')).toBeVisible()
  })
})
