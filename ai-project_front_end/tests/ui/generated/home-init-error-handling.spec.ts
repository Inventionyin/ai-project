import { expect, test } from '@playwright/test'

test.describe('Home 初始化失败处理', () => {
  test('首屏接口失败时展示页面级错误提示且不弹原生对话框', async ({ page }) => {
    const dialogs: string[] = []
    page.on('dialog', (dialog) => {
      dialogs.push(dialog.message())
      void dialog.dismiss()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.route('**/*', async (route) => {
      const req = route.request()
      if (req.resourceType() === 'document') {
        await route.continue()
        return
      }

      const url = new URL(req.url())
      if (url.pathname === '/api/auth/me') {
        await route.abort('failed')
        return
      }

      await route.continue()
    })

    await page.goto('/projects', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('获取首页数据失败，请检查网络后重试')).toBeVisible()

    await page.getByRole('button', { name: '重试' }).click()
    await expect(page.getByText('获取首页数据失败，请检查网络后重试')).toBeVisible()
    expect(dialogs).toHaveLength(0)
  })

  test('首屏接口返回非 JSON 时展示友好错误而不是解析异常', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.route('**/*', async (route) => {
      const req = route.request()
      if (req.resourceType() === 'document') {
        await route.continue()
        return
      }

      const url = new URL(req.url())
      if (url.pathname === '/api/auth/me') {
        await route.fulfill({
          status: 502,
          contentType: 'text/plain',
          body: ''
        })
        return
      }

      await route.continue()
    })

    await page.goto('/projects', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('获取首页数据失败，请检查网络后重试')).toBeVisible()
    await expect(page.getByText(/Unexpected end of JSON input/)).toHaveCount(0)
  })

  test('创建项目失败时展示 toast 且不弹原生对话框', async ({ page }) => {
    const dialogs: string[] = []
    page.on('dialog', (dialog) => {
      dialogs.push(dialog.message())
      void dialog.dismiss()
    })

    await page.addInitScript(() => {
      localStorage.setItem('accessToken', 'e2e-smoke-token')
      localStorage.setItem('accessTokenExpiresAt', String(Date.now() + 60 * 60 * 1000))
    })

    await page.route('**/*', async (route) => {
      const req = route.request()
      if (req.resourceType() === 'document') {
        await route.continue()
        return
      }

      const url = new URL(req.url())
      if (url.pathname === '/api/auth/me') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { userId: 'user-1', username: 'qa' } })
        })
        return
      }
      if (url.pathname === '/api/projects' && req.method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 200, total: 0, items: [] } })
        })
        return
      }
      if (url.pathname === '/api/projects/home-stats') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { projectTotal: 0, testcaseTotal: 0, todayRunTotal: 0, todayPassRate: 0 } })
        })
        return
      }
      if (url.pathname === '/api/projects' && req.method() === 'POST') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 1, message: 'create project unavailable' })
        })
        return
      }

      await route.continue()
    })

    await page.goto('/projects', { waitUntil: 'domcontentloaded' })
    await page.getByRole('button', { name: '新建项目' }).first().click()
    await page.getByPlaceholder('2-50个字符').fill('接口调试项目')
    await page.getByRole('button', { name: '创建' }).click()

    await expect(page.getByText('create project unavailable')).toBeVisible()
    expect(dialogs).toHaveLength(0)
  })
})
