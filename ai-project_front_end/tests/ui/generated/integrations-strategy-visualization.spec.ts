import { expect, test, type Route } from '@playwright/test'

async function fulfillCommonApi(route: Route, path: string) {
  if (path === '/api/auth/me' || path === '/auth/me') {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 0, data: { id: 'u1', username: 'qa', roles: ['Admin'] } })
    })
    return true
  }
  if (path.startsWith('/api/') || path.startsWith('/auth/')) {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: {} }) })
    return true
  }
  return false
}

test.describe('integrations strategy visualization smoke', () => {
  test('策略中心与策略模拟器可见（含 mock 数据汇总断言）', async ({ page }) => {
    const strategyCenterRows = [
      {
        notificationId: 'n-webhook-1',
        channel: 'WEBHOOK',
        target: 'https://example.test/webhook',
        enabled: true,
        events: ['RUN_FAILED'],
        strategySummary: 'summary-1',
        deliveryStats: { sent: 12, failed: 1, queued: 0, lastDeliveryAt: null, lastStatus: 'SENT' },
        filterReasonStats: { scopeReason: 3, eventFiltered: 1, unsupportedProvider: 0, templateNotFound: 0 },
        simulationStats: {
          sampleCount: 10,
          matchedCount: 8,
          scopeReasonTop: [{ reason: 'EVENT_FILTERED', count: 2 }]
        }
      },
      {
        notificationId: 'n-email-2',
        channel: 'EMAIL',
        target: 'qa@example.test',
        enabled: false,
        events: ['RUN_PASSED'],
        strategySummary: 'summary-2',
        deliveryStats: { sent: 5, failed: 0, queued: 1, lastDeliveryAt: null, lastStatus: 'QUEUED' },
        filterReasonStats: { scopeReason: 4, eventFiltered: 0, unsupportedProvider: 2, templateNotFound: 0 },
        simulationStats: {
          sampleCount: 6,
          matchedCount: 2,
          scopeReasonTop: [{ reason: 'UNSUPPORTED_PROVIDER', count: 3 }]
        }
      }
    ]

    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      const isApiLike = req.resourceType() !== 'document'

      if (!isApiLike) {
        await route.continue()
        return
      }

      if (path === '/api/projects/1' || path === '/projects/1') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'P1', ownerId: 'e2e-owner' } })
        })
        return
      }

      if (path === '/api/projects/1/integrations/notifications' || path === '/projects/1/integrations/notifications') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: [
              {
                id: 'rule-1',
                projectId: '1',
                channel: 'WEBHOOK',
                target: 'https://example.test/webhook',
                enabled: true,
                rule: {}
              }
            ]
          })
        })
        return
      }

      if (path.startsWith('/api/projects/1/integrations/notifications/deliveries') || path.startsWith('/projects/1/integrations/notifications/deliveries')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0, page: 1, pageSize: 20 } })
        })
        return
      }

      if (path.startsWith('/api/projects/1/prompt-templates/governance') || path.startsWith('/projects/1/prompt-templates/governance')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [] } })
        })
        return
      }

      if (path.startsWith('/api/projects/1/prompt-templates') || path.startsWith('/projects/1/prompt-templates')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [] })
        })
        return
      }

      if (
        path === '/api/projects/1/integrations/notifications/strategy-center' ||
        path === '/projects/1/integrations/notifications/strategy-center'
      ) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: strategyCenterRows })
        })
        return
      }

      if (await fulfillCommonApi(route, path)) return
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    const strategyCenterResponse = page.waitForResponse((resp) =>
      /\/api\/projects\/1\/integrations\/notifications\/strategy-center$/.test(new URL(resp.url()).pathname)
    )

    await page.goto('/projects/1/settings/integrations', { waitUntil: 'domcontentloaded' })
    await strategyCenterResponse
    await expect(page).toHaveURL(/\/projects\/1\/settings\/integrations/)

    const strategyCenterSection = page.locator('section').filter({ has: page.getByRole('heading', { name: '策略中心' }) })

    await expect(page.getByRole('heading', { name: '策略中心' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '策略模拟器' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'simulationStats' })).toBeVisible()
    await expect(strategyCenterSection.getByRole('combobox', { name: 'channel' })).toBeVisible()
    await expect(strategyCenterSection.getByRole('combobox', { name: 'topScopeReason' })).toBeVisible()
    await expect(strategyCenterSection.getByRole('textbox', { name: 'keyword（notificationId/target）' })).toBeVisible()

    await expect(page.getByText('n-webhook-1')).toBeVisible()
    await expect(page.getByText('n-email-2')).toBeVisible()
    await expect(page.getByText('总规则数: 2')).toBeVisible()
    await expect(page.getByText('启用数: 1')).toBeVisible()
    await expect(page.getByText('含 simulationStats: 2')).toBeVisible()
  })

  test('策略中心过滤器行为断言', async ({ page }) => {
    const strategyCenterRows = [
      {
        notificationId: 'n-webhook-1',
        channel: 'WEBHOOK',
        target: 'https://example.test/webhook',
        enabled: true,
        events: ['RUN_FAILED'],
        strategySummary: 'summary-1',
        deliveryStats: { sent: 12, failed: 1, queued: 0, lastDeliveryAt: null, lastStatus: 'SENT' },
        filterReasonStats: { scopeReason: 3, eventFiltered: 1, unsupportedProvider: 0, templateNotFound: 0 },
        simulationStats: {
          sampleCount: 10,
          matchedCount: 8,
          scopeReasonTop: [{ reason: 'EVENT_FILTERED', count: 2 }]
        }
      },
      {
        notificationId: 'n-email-2',
        channel: 'EMAIL',
        target: 'qa@example.test',
        enabled: false,
        events: ['RUN_PASSED'],
        strategySummary: 'summary-2',
        deliveryStats: { sent: 5, failed: 0, queued: 1, lastDeliveryAt: null, lastStatus: 'QUEUED' },
        filterReasonStats: { scopeReason: 4, eventFiltered: 0, unsupportedProvider: 2, templateNotFound: 0 },
        simulationStats: {
          sampleCount: 6,
          matchedCount: 2,
          scopeReasonTop: [{ reason: 'UNSUPPORTED_PROVIDER', count: 3 }]
        }
      }
    ]

    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      const isApiLike = req.resourceType() !== 'document'

      if (!isApiLike) {
        await route.continue()
        return
      }

      if (path === '/api/projects/1' || path === '/projects/1') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'P1', ownerId: 'e2e-owner' } })
        })
        return
      }

      if (path === '/api/projects/1/integrations/notifications' || path === '/projects/1/integrations/notifications') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: [
              {
                id: 'rule-1',
                projectId: '1',
                channel: 'WEBHOOK',
                target: 'https://example.test/webhook',
                enabled: true,
                rule: {}
              }
            ]
          })
        })
        return
      }

      if (path.startsWith('/api/projects/1/integrations/notifications/deliveries') || path.startsWith('/projects/1/integrations/notifications/deliveries')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0, page: 1, pageSize: 20 } })
        })
        return
      }

      if (path.startsWith('/api/projects/1/prompt-templates/governance') || path.startsWith('/projects/1/prompt-templates/governance')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [] } })
        })
        return
      }

      if (path.startsWith('/api/projects/1/prompt-templates') || path.startsWith('/projects/1/prompt-templates')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [] })
        })
        return
      }

      if (
        path === '/api/projects/1/integrations/notifications/strategy-center' ||
        path === '/projects/1/integrations/notifications/strategy-center'
      ) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: strategyCenterRows })
        })
        return
      }

      if (await fulfillCommonApi(route, path)) return
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/integrations', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: '策略中心' })).toBeVisible()
    const strategyCenterSection = page.locator('section').filter({ has: page.getByRole('heading', { name: '策略中心' }) })

    await expect(page.getByRole('cell', { name: 'n-webhook-1' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'n-email-2' })).toBeVisible()

    await strategyCenterSection.getByRole('combobox', { name: 'channel' }).selectOption('EMAIL')
    await expect(page.getByRole('cell', { name: 'n-email-2' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'n-webhook-1' })).toHaveCount(0)

    await strategyCenterSection.getByRole('combobox', { name: 'topScopeReason' }).selectOption('UNSUPPORTED_PROVIDER')
    await expect(page.getByRole('cell', { name: 'n-email-2' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'n-webhook-1' })).toHaveCount(0)

    await strategyCenterSection.getByRole('combobox', { name: 'channel' }).selectOption('ALL')
    await strategyCenterSection.getByRole('combobox', { name: 'topScopeReason' }).selectOption('ALL')
    await strategyCenterSection.getByRole('textbox', { name: 'keyword（notificationId/target）' }).fill('https://example.test/webhook')
    await expect(page.getByRole('cell', { name: 'n-webhook-1' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'n-email-2' })).toHaveCount(0)
  })

  test('策略中心排序与导出能力断言', async ({ page }) => {
    const strategyCenterRows = [
      {
        notificationId: 'n-webhook-1',
        channel: 'WEBHOOK',
        target: 'https://example.test/webhook',
        enabled: true,
        events: ['RUN_FAILED'],
        strategySummary: 'summary-1',
        deliveryStats: { sent: 12, failed: 1, queued: 0, lastDeliveryAt: null, lastStatus: 'SENT' },
        filterReasonStats: { scopeReason: 3, eventFiltered: 1, unsupportedProvider: 0, templateNotFound: 0 },
        simulationStats: {
          sampleCount: 10,
          matchedCount: 8,
          scopeReasonTop: [{ reason: 'EVENT_FILTERED', count: 2 }]
        }
      },
      {
        notificationId: 'n-email-2',
        channel: 'EMAIL',
        target: 'qa@example.test',
        enabled: false,
        events: ['RUN_PASSED'],
        strategySummary: 'summary-2',
        deliveryStats: { sent: 5, failed: 0, queued: 1, lastDeliveryAt: null, lastStatus: 'QUEUED' },
        filterReasonStats: { scopeReason: 4, eventFiltered: 0, unsupportedProvider: 2, templateNotFound: 0 },
        simulationStats: {
          sampleCount: 6,
          matchedCount: 2,
          scopeReasonTop: [{ reason: 'UNSUPPORTED_PROVIDER', count: 3 }]
        }
      }
    ]

    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      const isApiLike = req.resourceType() !== 'document'

      if (!isApiLike) {
        await route.continue()
        return
      }

      if (path === '/api/projects/1' || path === '/projects/1') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'P1', ownerId: 'e2e-owner' } })
        })
        return
      }

      if (path === '/api/projects/1/integrations/notifications' || path === '/projects/1/integrations/notifications') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: [
              {
                id: 'rule-1',
                projectId: '1',
                channel: 'WEBHOOK',
                target: 'https://example.test/webhook',
                enabled: true,
                rule: {}
              }
            ]
          })
        })
        return
      }

      if (path.startsWith('/api/projects/1/integrations/notifications/deliveries') || path.startsWith('/projects/1/integrations/notifications/deliveries')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0, page: 1, pageSize: 20 } })
        })
        return
      }

      if (path.startsWith('/api/projects/1/prompt-templates/governance') || path.startsWith('/projects/1/prompt-templates/governance')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [] } })
        })
        return
      }

      if (path.startsWith('/api/projects/1/prompt-templates') || path.startsWith('/projects/1/prompt-templates')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [] })
        })
        return
      }

      if (
        path === '/api/projects/1/integrations/notifications/strategy-center' ||
        path === '/projects/1/integrations/notifications/strategy-center'
      ) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: strategyCenterRows })
        })
        return
      }

      if (await fulfillCommonApi(route, path)) return
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/integrations', { waitUntil: 'domcontentloaded' })
    const strategyCenterSection = page.locator('section').filter({ has: page.getByRole('heading', { name: '策略中心' }) })
    await expect(page.getByRole('heading', { name: '策略中心' })).toBeVisible()

    const sortBy = strategyCenterSection.getByRole('combobox', { name: 'sortBy' })
    await expect(sortBy).toBeVisible()
    await sortBy.selectOption('SAMPLE_COUNT_DESC')
    await expect(page.getByRole('cell', { name: 'n-webhook-1' })).toBeVisible()

    const exportButton = page.getByRole('button', { name: '导出当前筛选 JSON' })
    await expect(exportButton).toBeVisible()
    const downloadPromise = page.waitForEvent('download')
    await exportButton.click()
    await expect(downloadPromise).resolves.toBeTruthy()
  })

  test('策略中心 CSV 导出与筛选快照回填断言', async ({ page }) => {
    const strategyCenterRows = [
      {
        notificationId: 'n-webhook-1',
        channel: 'WEBHOOK',
        target: 'https://example.test/webhook',
        enabled: true,
        events: ['RUN_FAILED'],
        strategySummary: 'summary-1',
        deliveryStats: { sent: 12, failed: 1, queued: 0, lastDeliveryAt: null, lastStatus: 'SENT' },
        filterReasonStats: { scopeReason: 3, eventFiltered: 1, unsupportedProvider: 0, templateNotFound: 0 },
        simulationStats: {
          sampleCount: 10,
          matchedCount: 8,
          scopeReasonTop: [{ reason: 'EVENT_FILTERED', count: 2 }]
        }
      },
      {
        notificationId: 'n-email-2',
        channel: 'EMAIL',
        target: 'qa@example.test',
        enabled: false,
        events: ['RUN_PASSED'],
        strategySummary: 'summary-2',
        deliveryStats: { sent: 5, failed: 0, queued: 1, lastDeliveryAt: null, lastStatus: 'QUEUED' },
        filterReasonStats: { scopeReason: 4, eventFiltered: 0, unsupportedProvider: 2, templateNotFound: 0 },
        simulationStats: {
          sampleCount: 6,
          matchedCount: 2,
          scopeReasonTop: [{ reason: 'UNSUPPORTED_PROVIDER', count: 3 }]
        }
      }
    ]

    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      const isApiLike = req.resourceType() !== 'document'

      if (!isApiLike) {
        await route.continue()
        return
      }

      if (path === '/api/projects/1' || path === '/projects/1') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'P1', ownerId: 'e2e-owner' } })
        })
        return
      }

      if (path === '/api/projects/1/integrations/notifications' || path === '/projects/1/integrations/notifications') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: [
              {
                id: 'rule-1',
                projectId: '1',
                channel: 'WEBHOOK',
                target: 'https://example.test/webhook',
                enabled: true,
                rule: {}
              }
            ]
          })
        })
        return
      }

      if (path.startsWith('/api/projects/1/integrations/notifications/deliveries') || path.startsWith('/projects/1/integrations/notifications/deliveries')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0, page: 1, pageSize: 20 } })
        })
        return
      }

      if (path.startsWith('/api/projects/1/prompt-templates/governance') || path.startsWith('/projects/1/prompt-templates/governance')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [] } })
        })
        return
      }

      if (path.startsWith('/api/projects/1/prompt-templates') || path.startsWith('/projects/1/prompt-templates')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [] })
        })
        return
      }

      if (
        path === '/api/projects/1/integrations/notifications/strategy-center' ||
        path === '/projects/1/integrations/notifications/strategy-center'
      ) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: strategyCenterRows })
        })
        return
      }

      if (await fulfillCommonApi(route, path)) return
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/integrations', { waitUntil: 'domcontentloaded' })
    const strategyCenterSection = page.locator('section').filter({ has: page.getByRole('heading', { name: '策略中心' }) })
    await expect(page.getByRole('heading', { name: '策略中心' })).toBeVisible()

    const exportCsvButton = page.getByRole('button', { name: '导出当前筛选 CSV' })
    await expect(exportCsvButton).toBeVisible()
    const csvDownloadPromise = page.waitForEvent('download')
    await exportCsvButton.click()
    await expect(csvDownloadPromise).resolves.toBeTruthy()

    await strategyCenterSection.getByRole('combobox', { name: 'channel' }).selectOption('EMAIL')
    await strategyCenterSection.getByRole('combobox', { name: 'topScopeReason' }).selectOption('UNSUPPORTED_PROVIDER')
    await strategyCenterSection.getByRole('textbox', { name: 'keyword（notificationId/target）' }).fill('qa@example.test')

    await expect(page.getByRole('cell', { name: 'n-email-2' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'n-webhook-1' })).toHaveCount(0)

    const saveSnapshotButton = page.getByRole('button', { name: '保存快照' })
    await expect(saveSnapshotButton).toBeVisible()
    await saveSnapshotButton.click()

    await page.reload({ waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: '策略中心' })).toBeVisible()

    const restoreSnapshotButton = page.getByRole('button', { name: '回填快照' })
    await expect(restoreSnapshotButton).toBeVisible()
    await restoreSnapshotButton.click()

    await expect(strategyCenterSection.getByRole('combobox', { name: 'channel' })).toHaveValue('EMAIL')
    await expect(strategyCenterSection.getByRole('combobox', { name: 'topScopeReason' })).toHaveValue('UNSUPPORTED_PROVIDER')
    await expect(strategyCenterSection.getByRole('textbox', { name: 'keyword（notificationId/target）' })).toHaveValue('qa@example.test')
    await expect(page.getByRole('cell', { name: 'n-email-2' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'n-webhook-1' })).toHaveCount(0)
  })

  test('策略中心 CSV 列选择、下载、双快照回填与删除断言', async ({ page }) => {
    const strategyCenterRows = [
      {
        notificationId: 'n-webhook-1',
        channel: 'WEBHOOK',
        target: 'https://example.test/webhook',
        enabled: true,
        events: ['RUN_FAILED'],
        strategySummary: 'summary-1',
        deliveryStats: { sent: 12, failed: 1, queued: 0, lastDeliveryAt: null, lastStatus: 'SENT' },
        filterReasonStats: { scopeReason: 3, eventFiltered: 1, unsupportedProvider: 0, templateNotFound: 0 },
        simulationStats: {
          sampleCount: 10,
          matchedCount: 8,
          scopeReasonTop: [{ reason: 'EVENT_FILTERED', count: 2 }]
        }
      },
      {
        notificationId: 'n-email-2',
        channel: 'EMAIL',
        target: 'qa@example.test',
        enabled: false,
        events: ['RUN_PASSED'],
        strategySummary: 'summary-2',
        deliveryStats: { sent: 5, failed: 0, queued: 1, lastDeliveryAt: null, lastStatus: 'QUEUED' },
        filterReasonStats: { scopeReason: 4, eventFiltered: 0, unsupportedProvider: 2, templateNotFound: 0 },
        simulationStats: {
          sampleCount: 6,
          matchedCount: 2,
          scopeReasonTop: [{ reason: 'UNSUPPORTED_PROVIDER', count: 3 }]
        }
      }
    ]

    await page.route('**/*', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname
      const isApiLike = req.resourceType() !== 'document'

      if (!isApiLike) {
        await route.continue()
        return
      }

      if (path === '/api/projects/1' || path === '/projects/1') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: '1', name: 'P1', ownerId: 'e2e-owner' } })
        })
        return
      }

      if (path === '/api/projects/1/integrations/notifications' || path === '/projects/1/integrations/notifications') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: [
              {
                id: 'rule-1',
                projectId: '1',
                channel: 'WEBHOOK',
                target: 'https://example.test/webhook',
                enabled: true,
                rule: {}
              }
            ]
          })
        })
        return
      }

      if (path.startsWith('/api/projects/1/integrations/notifications/deliveries') || path.startsWith('/projects/1/integrations/notifications/deliveries')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0, page: 1, pageSize: 20 } })
        })
        return
      }

      if (path.startsWith('/api/projects/1/prompt-templates/governance') || path.startsWith('/projects/1/prompt-templates/governance')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [] } })
        })
        return
      }

      if (path.startsWith('/api/projects/1/prompt-templates') || path.startsWith('/projects/1/prompt-templates')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [] })
        })
        return
      }

      if (
        path === '/api/projects/1/integrations/notifications/strategy-center' ||
        path === '/projects/1/integrations/notifications/strategy-center'
      ) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: strategyCenterRows })
        })
        return
      }

      if (await fulfillCommonApi(route, path)) return
      await route.continue()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.goto('/projects/1/settings/integrations', { waitUntil: 'domcontentloaded' })
    const strategyCenterSection = page.locator('section').filter({ has: page.getByRole('heading', { name: '策略中心' }) })
    await expect(page.getByRole('heading', { name: '策略中心' })).toBeVisible()

    const csvColumnButton = page.getByRole('button', { name: 'CSV 列选择' })
    await expect(csvColumnButton).toBeVisible()
    await csvColumnButton.click()
    await page.getByRole('menuitemcheckbox', { name: 'notificationId' }).click()
    await page.getByRole('menuitemcheckbox', { name: 'channel' }).click()
    await csvColumnButton.click()

    const exportCsvButton = page.getByRole('button', { name: '导出当前筛选 CSV' })
    await expect(exportCsvButton).toBeVisible()
    const csvDownloadPromise = page.waitForEvent('download')
    await exportCsvButton.click()
    await expect(csvDownloadPromise).resolves.toBeTruthy()

    await strategyCenterSection.getByRole('combobox', { name: 'channel' }).selectOption('EMAIL')
    await strategyCenterSection.getByRole('combobox', { name: 'topScopeReason' }).selectOption('UNSUPPORTED_PROVIDER')
    await strategyCenterSection.getByRole('textbox', { name: 'keyword（notificationId/target）' }).fill('qa@example.test')

    const saveSnapshotButton = page.getByRole('button', { name: '保存快照' })
    await expect(saveSnapshotButton).toBeVisible()
    await saveSnapshotButton.click()

    await strategyCenterSection.getByRole('textbox', { name: 'keyword（notificationId/target）' }).fill('n-email-2')
    await saveSnapshotButton.click()

    const restoreSnapshotButton = page.getByRole('button', { name: '回填快照' })
    await expect(restoreSnapshotButton).toBeVisible()
    await restoreSnapshotButton.click()
    await expect(strategyCenterSection.getByRole('combobox', { name: 'channel' })).toHaveValue('EMAIL')
    await expect(strategyCenterSection.getByRole('combobox', { name: 'topScopeReason' })).toHaveValue('UNSUPPORTED_PROVIDER')
    await expect(strategyCenterSection.getByRole('textbox', { name: 'keyword（notificationId/target）' })).toHaveValue('n-email-2')

    const deleteSnapshotButton = page.getByRole('button', { name: '删除快照' })
    await expect(deleteSnapshotButton).toBeVisible()
    await deleteSnapshotButton.click()
  })
})
