import { expect, test } from '@playwright/test'

const collectionDetail = (id: string, name: string) => ({
  id,
  projectId: '1',
  name,
  variables: { baseUrl: 'https://api.example.com' },
  groups: [
    {
      id: `grp-${id}`,
      collectionId: id,
      name: '认证',
      order: 1,
      requests: [{ id: `req-${id}`, collectionId: id, groupId: `grp-${id}`, name: '登录', method: 'POST', url: '/api/login' }],
    },
  ],
  requests: [],
  updatedAt: 1710000000,
})

test.describe('接口集合详情 Postman-like 调试链路', () => {
  test.beforeEach(async ({ page }) => {
    let bindingCreated = false

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

      if (url.pathname === '/api/projects/1/environments') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [{ id: 'env-1', name: '测试环境' }] }),
        })
      }

      if (url.pathname === '/api/testcases' && url.searchParams.get('projectId') === '1') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 200, total: 1, items: [{ id: 'TC-001', title: '登录用例' }] } }),
        })
      }

      if (url.pathname === '/api/suites' && url.searchParams.get('projectId') === '1') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 200, total: 0, items: [] } }),
        })
      }

      if (url.pathname === '/api/collections/col-1') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: collectionDetail('col-1', '登录接口集合') }),
        })
      }

      if (url.pathname === '/api/collections/col-imported') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: collectionDetail('col-imported', '导入集合') }),
        })
      }

      if ((url.pathname === '/api/collections/col-1/requests/req-col-1' || url.pathname === '/api/collections/col-imported/requests/req-col-imported') && req.method() === 'GET') {
        const collectionId = url.pathname.includes('col-imported') ? 'col-imported' : 'col-1'
        const requestId = collectionId === 'col-imported' ? 'req-col-imported' : 'req-col-1'
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: requestId,
              collectionId,
              groupId: `grp-${collectionId}`,
              name: '登录',
              method: 'POST',
              url: '/api/login',
              headers: { 'Content-Type': 'application/json' },
              auth: {},
              body: { username: 'qa@example.com' },
              asserts: { status: 200 },
              updatedAt: 1710000000,
            },
          }),
        })
      }

      if (url.pathname === '/api/collections/col-1/requests/req-col-1' && req.method() === 'PUT') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: 'req-col-1', collectionId: 'col-1', name: '登录接口已保存', method: 'POST', url: '/api/login' } }),
        })
      }

      if (url.pathname === '/api/collections/col-1/requests/req-col-1/run') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              collectionId: 'col-1',
              requestId: 'req-col-1',
              envId: 'env-1',
              ok: true,
              status: 200,
              elapsedMs: 42,
              response: {
                headers: { 'content-type': 'application/json' },
                body: '{"token":"mock-token"}',
              },
            },
          }),
        })
      }

      if (url.pathname === '/api/collections/col-1/export') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { format: url.searchParams.get('format'), content: '{"info":{"name":"登录接口集合"}}' } }),
        })
      }

      if (url.pathname === '/api/collections/import') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: collectionDetail('col-imported', '导入集合') }),
        })
      }

      if (url.pathname === '/api/projects/1/collections/col-1/bindings' || url.pathname === '/api/projects/1/collections/col-imported/bindings') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
      }

      if (url.pathname === '/api/projects/1/requests/req-col-1/bindings') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: bindingCreated
              ? [{ id: 'bind-1', projectId: '1', testcaseId: 'TC-001', name: '登录绑定', linkType: 'REQUEST', sourceType: 'MANUAL', assertSummary: '状态码 200', lastRunStatus: 'PASSED', updatedAt: 1710000000, version: 1 }]
              : [],
          }),
        })
      }

      if (url.pathname === '/api/projects/1/requests/req-col-imported/bindings') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: [] }) })
      }

      if (url.pathname === '/api/testcases/TC-001/bindings') {
        bindingCreated = true
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { id: 'bind-1', testcaseId: 'TC-001', name: '登录绑定', version: 1 } }),
        })
      }

      return route.continue()
    })
  })

  test('导入集合后跳转到新集合详情', async ({ page }) => {
    await page.goto('/projects/1/assets/apis/col-1', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('集合：登录接口集合')).toBeVisible()
    await page.getByPlaceholder('粘贴导入 JSON 内容').fill('{"info":{"name":"导入集合"}}')
    await page.getByRole('button', { name: '导入集合' }).click()

    await expect(page).toHaveURL(/\/projects\/1\/assets\/apis\/col-imported$/)
    await expect(page.getByText('集合：导入集合')).toBeVisible()
    await expect(page.getByText('导入成功：导入集合')).toBeVisible()
  })

  test('保存、运行、导出和绑定用例形成调试闭环', async ({ page }) => {
    await page.goto('/projects/1/assets/apis/col-1', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('请求详情表单（可编辑）')).toBeVisible()
    await page.getByPlaceholder('请求名称').fill('登录接口已保存')
    await page.getByRole('button', { name: '保存', exact: true }).click()
    await expect(page.getByText('保存成功')).toBeVisible()

    await page.getByLabel('调试环境').selectOption('env-1')
    await page.getByRole('button', { name: '运行请求' }).click()
    await expect(page.getByText('状态码 200')).toBeVisible()
    await expect(page.getByText('耗时 42 ms')).toBeVisible()
    await expect(page.getByText('mock-token')).toBeVisible()

    await page.getByRole('button', { name: '导出 Postman' }).click()
    await expect(page.getByText('导出成功（postman）')).toBeVisible()
    await expect(page.getByText('导出内容')).toBeVisible()

    await page.getByLabel('选择绑定用例').selectOption('TC-001')
    await page.getByPlaceholder('绑定名称').fill('登录绑定')
    await page.getByPlaceholder('断言摘要，可留空').fill('状态码 200')
    await page.getByRole('button', { name: '保存为用例绑定' }).click()
    await expect(page.getByText('绑定已创建')).toBeVisible()
    await expect(page.getByText('TC-001')).toBeVisible()
  })
})
