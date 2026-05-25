import { expect, test } from '@playwright/test'

test.describe('trial operation defect import preview', () => {
  test('filters markdown report metadata from defect rows', async ({ page }) => {
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
      if (path.includes('/dashboard/trial-operation/case-governance')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { totalCases: 0, uniqueCaseIds: 0, emptyCaseIds: 0, emptyTitles: 0, p0Cases: 0, p0Density: 0, typeDistribution: {}, priorityDistribution: {}, moduleDistribution: {}, duplicateTitleCandidates: [], lowValueCandidates: [], moduleP0Density: [] } })
        })
        return
      }
      if (path.includes('/dashboard/trial-operation/governance/history')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { generatedBatches: 0, appliedBatches: 0, appliedSuggestions: 0, updatedCases: 0, items: [] } }) })
        return
      }
      if (path.includes('/dashboard/trial-operation/report/snapshots')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 5, total: 0, items: [] } }) })
        return
      }
      if (path.includes('/platform/trial-operation/import-records')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 6, total: 0, items: [] } }) })
        return
      }
      if (path.includes('/dashboard/trial-operation')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              metrics: {},
              testcasePriorityDistribution: {},
              testcaseStatusDistribution: {},
              testcaseTypeDistribution: {},
              testcaseFeatureDistribution: {},
              defectSeverityDistribution: {},
              defectStatusDistribution: {},
              topDefectClusters: [],
              topRiskHints: [],
              sampleTestcases: []
            }
          })
        })
        return
      }
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/trial-operation', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('button', { name: '演示概览' })).toBeVisible()
    await expect(page.getByRole('button', { name: '数据导入' })).toBeVisible()
    await expect(page.getByText('验收汇报稿', { exact: true })).toBeVisible()
    await expect(page.getByText('用例库治理')).not.toBeVisible()
    await expect(page.getByLabel('选择导入类型')).not.toBeVisible()

    await page.getByRole('button', { name: '数据导入' }).click()
    await expect(page.getByLabel('选择导入类型')).toBeVisible()
    await page.getByLabel('选择导入类型').selectOption('defects')
    await expect(page.getByRole('button', { name: '更多' })).toBeVisible()
    await page.getByRole('button', { name: '更多' }).click()
    await expect(page.getByRole('button', { name: '重置本次导入' })).toBeVisible()
    await expect(page.getByRole('button', { name: /确认导入/ })).toBeVisible()

    const markdown = [
      '# Teambition 缺陷分析',
      '',
      '**分析目标**: Teambition 阶段下的全部 Bug',
      '**缺陷总计**: 2 个',
      '',
      '### 执行者: QA',
      '',
      '| 优先级 | 状态 | 缺陷标题 |',
      '| --- | --- | --- |',
      '| P0 | 未完成 | android google登陆 crash |',
      '| P1 | 未完成 | 【直播间】点击关注的时候文案效果过长 |',
      '',
      '---'
    ].join('\n')

    await page.locator('input[type="file"]').first().setInputFiles({
      name: 'Bug分析_客户端1.2.15_按执行者拆分.md',
      mimeType: 'text/markdown',
      buffer: Buffer.from(markdown)
    })

    await expect(page.getByText('Bug分析_客户端1.2.15_按执行者拆分.md · 识别 2 行')).toBeVisible()
    await expect(page.getByText('android google登陆 crash')).toBeVisible()
    await expect(page.getByText('【直播间】点击关注的时候文案效果过长')).toBeVisible()
    await expect(page.getByText(/分析目标/)).toHaveCount(0)
    await expect(page.getByText(/缺陷总计/)).toHaveCount(0)
  })
})
