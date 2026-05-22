import { expect, test } from '@playwright/test'

test.describe('acceptance-center 生产验收中心冒烟', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })
  })

  test('展示验收摘要与报告预览', async ({ page }) => {
    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      if (req.resourceType() === 'document') return route.continue()
      if (path === '/api/projects/22222222-2222-2222-2222-222222222222') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: { id: '22222222-2222-2222-2222-222222222222', name: 'E2E Project' },
          }),
        })
      }
      if (path === '/api/projects/22222222-2222-2222-2222-222222222222/acceptance/summary') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              overallStatus: 'BLOCKED',
              score: 82,
              generatedAt: 1710000000,
              checks: [
                {
                  key: 'realData',
                  label: '真实数据基线',
                  status: 'BLOCKED',
                  detail: '22 个 P0 缺陷和 460 个 OPEN 缺陷未闭环',
                  recommendation: '进入缺陷列表治理阻塞项',
                },
                {
                  key: 'externalSystems',
                  label: '外部系统联调',
                  status: 'READY',
                  detail: '钉钉和 Jenkins 已就绪',
                  recommendation: '保持外部系统 smoke',
                },
                {
                  key: 'opsHealth',
                  label: '运维可观测性',
                  status: 'READY',
                  detail: '运维健康聚合状态：READY',
                  recommendation: '保持健康检查巡检',
                },
              ],
              externalSystems: [
                {
                  provider: 'Jira',
                  status: 'BLOCKED',
                  configured: false,
                  missingFields: ['apiToken'],
                  detail: 'API Token 已过期',
                  recommendation: '更新 Jira Token 后复验',
                },
                {
                  provider: 'CI Pipeline',
                  status: 'WARN',
                  configured: true,
                  missingFields: [],
                  detail: '最近一轮执行超时',
                  recommendation: '补跑失败流水线',
                },
              ],
              metrics: { defects: 460, riskHints: 460, executedCaseRuns: 27 },
              nextActions: ['更新 Jira Token', '补跑失败流水线'],
            },
          }),
        })
      }
      if (path === '/api/projects/22222222-2222-2222-2222-222222222222/acceptance/report') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              markdown:
                '# 生产验收报告\n\n## 默认验收确认口径\n| 分类 | 数量 | 默认确认口径 | 样例 |\n| --- | ---: | --- | --- |\n| 必须修复后再放行 | 28 | 默认不建议豁免 | 黑屏 |\n\n- 当前状态：WARN\n- 建议：处理 Jira 令牌后复验',
            },
          }),
        })
      }
      return route.continue()
    })

    await page.goto('/projects/22222222-2222-2222-2222-222222222222/settings/acceptance', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/projects\/22222222-2222-2222-2222-222222222222\/settings\/acceptance/)

    await expect(page.getByText('生产验收中心')).toBeVisible()
    await expect(page.locator('div').filter({ hasText: /^总体状态\s*阻塞\s*有条件放行评审\s*评分\s*82/ })).toBeVisible()
    await expect(page.getByRole('link', { name: '查看未关闭缺陷' })).toHaveAttribute(
      'href',
      '/projects/22222222-2222-2222-2222-222222222222/defects?status=OPEN'
    )
    await expect(page.getByRole('link', { name: '进入试运行治理' })).toHaveAttribute(
      'href',
      '/projects/22222222-2222-2222-2222-222222222222/trial-operation'
    )
    await expect(page.getByText('阻塞治理概览')).toBeVisible()
    await expect(page.getByText('未关闭缺陷', { exact: true })).toBeVisible()
    await expect(page.getByText('460').first()).toBeVisible()
    await expect(page.getByRole('cell', { name: 'Jira' })).toBeVisible()
    await expect(page.getByText('API Token 已过期')).toBeVisible()
    await expect(page.getByText('生产验收报告')).toBeVisible()
    await expect(page.getByRole('button', { name: '复制报告' })).toBeVisible()
    await expect(page.getByRole('button', { name: '复制汇报口径' })).toBeVisible()
    await expect(page.getByRole('button', { name: '下载报告' })).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: '下载报告' }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/^production-acceptance-report-.*\.md$/)
  })
})
