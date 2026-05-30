import { expect, test } from '@playwright/test'

test.describe('资产中心操作闭环入口', () => {
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

      if (url.pathname === '/api/auth/me') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { userId: 'u1', username: 'qa' } }),
        })
      }

      if (url.pathname === '/api/testcases/owners') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [{ id: 'u1', username: 'qa' }] }),
        })
      }

      if (url.pathname === '/api/testcases') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              page: 1,
              pageSize: 20,
              total: 2,
              items: [
                {
                  id: 'tc-1',
                  testCaseId: 'TC-001',
                  title: '登录成功',
                  version: 'v1',
                  type: '接口',
                  priority: 'P0',
                  status: 'REVIEWED',
                  lastRun: 'PASSED',
                  updatedAt: 1710000000,
                  tags: ['登录'],
                  feature: '登录模块',
                  apiMethod: 'POST',
                  apiUrl: '/api/login',
                  expectedResult: '返回 token',
                  ownerId: 'u1',
                },
                {
                  id: 'tc-2',
                  testCaseId: 'TC-002',
                  title: '支付失败提示',
                  version: 'v1',
                  type: 'API',
                  priority: 'P1',
                  status: 'DRAFT',
                  lastRun: 'FAILED',
                  updatedAt: 1710000300,
                  tags: ['支付'],
                  feature: '支付模块',
                  apiMethod: 'POST',
                  apiUrl: '/api/pay',
                  expectedResult: '返回错误码',
                  ownerId: 'u1',
                },
              ],
            },
          }),
        })
      }

      if (url.pathname === '/api/projects/1/environments') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [{ id: 'env-1', name: '测试环境', baseUrl: 'https://api.example.test' }] }),
        })
      }

      if (url.pathname === '/api/suites') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { page: 1, pageSize: 200, total: 0, items: [] } }),
        })
      }

      if (url.pathname === '/api/projects/1/requirements/docs') {
        if (req.method() === 'GET') {
          const status = url.searchParams.get('status') || ''
          const rows = [
            {
              id: 'doc-1',
              projectId: '1',
              title: '登录需求',
              status: 'DRAFT',
              sourceType: 'PRD',
              tags: ['登录'],
              updatedAt: '2026-05-25 10:00',
            },
            {
              id: 'doc-2',
              projectId: '1',
              title: '支付评审需求',
              status: 'REVIEWING',
              sourceType: 'SPEC',
              tags: ['支付'],
              updatedAt: '2026-05-25 11:00',
            },
            {
              id: 'doc-3',
              projectId: '1',
              title: '订单发布需求',
              status: 'PUBLISHED',
              sourceType: 'PROTOTYPE',
              tags: ['订单'],
              updatedAt: '2026-05-25 12:00',
            },
          ].filter((item) => !status || item.status === status)
          return route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              code: 0,
              data: {
                page: 1,
                pageSize: 50,
                total: rows.length,
                items: rows,
              },
            }),
          })
        }
      }

      if (url.pathname === '/api/projects/1/requirements/docs/doc-1') {
        if (req.method() === 'PUT') {
          return route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              code: 0,
              data: {
                id: 'doc-1',
                projectId: '1',
                title: '登录需求-已编辑',
                status: 'REVIEWING',
                sourceType: 'PRD',
                tags: ['登录', '核心'],
                updatedAt: '2026-05-25 10:01',
              },
            }),
          })
        }
        if (req.method() === 'DELETE') {
          return route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ code: 0, data: {} }),
          })
        }
      }

      if (url.pathname === '/api/collections') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: [{ id: 'col-1', projectId: '1', name: '登录接口集合', requestCount: 1, updatedAt: 1710000000 }],
          }),
        })
      }

      if (url.pathname === '/api/collections/col-1') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              id: 'col-1',
              projectId: '1',
              name: '登录接口集合',
              groups: [
                {
                  id: 'grp-1',
                  collectionId: 'col-1',
                  name: '认证',
                  order: 1,
                  requests: [
                    { id: 'req-1', collectionId: 'col-1', groupId: 'grp-1', name: '登录', method: 'POST', url: '/api/login' },
                    { id: 'req-2', collectionId: 'col-1', groupId: 'grp-1', name: '登录状态', method: 'GET', url: '/api/session' },
                  ],
                },
              ],
              requests: [],
              updatedAt: 1710000000,
            },
          }),
        })
      }

      if (url.pathname === '/api/projects/1/collections/col-1/bindings') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: [] }),
        })
      }

      return route.continue()
    })
  })

  test('用例管理支持导出当前列表', async ({ page }) => {
    await page.goto('/projects/1/assets/testcases', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('登录成功')).toBeVisible()
    await expect(page.getByRole('button', { name: '导出当前视图' })).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: '导出当前视图' }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/testcases.*\.csv$/)
  })

  test('用例管理展示数据总览并支持快速视图筛选', async ({ page }) => {
    await page.goto('/projects/1/assets/testcases', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('当前视图', { exact: true })).toBeVisible()
    await expect(page.getByText('P0 高优先级')).toBeVisible()
    await expect(page.getByText('失败待复核')).toBeVisible()
    await expect(page.getByText('评审完成率')).toBeVisible()

    await expect(page.getByText('登录成功')).toBeVisible()
    await expect(page.getByText('支付失败提示')).toBeVisible()

    await page.getByRole('button', { name: '最近失败' }).click()
    await expect(page.getByText('当前条件')).toBeVisible()
    await expect(page.getByText('支付失败提示')).toBeVisible()
    await expect(page.getByText('登录成功')).toBeHidden()

    await page.getByRole('button', { name: '清空筛选' }).click()
    await expect(page.getByText('登录成功')).toBeVisible()
    await expect(page.getByText('支付失败提示')).toBeVisible()
  })

  test('用例管理表单校验使用页面提示而不是原生弹窗', async ({ page }) => {
    const dialogs: string[] = []
    page.on('dialog', (dialog) => {
      dialogs.push(dialog.message())
      void dialog.dismiss()
    })

    await page.goto('/projects/1/assets/testcases', { waitUntil: 'domcontentloaded' })

    await page.getByRole('button', { name: '新建用例' }).click()
    await page.getByRole('button', { name: '保存' }).click()
    await expect(page.getByText('请输入功能模块')).toBeVisible()

    await page.getByRole('button', { name: '取消' }).click()
    await page.getByRole('button', { name: '导入文件' }).click()
    await page.getByRole('button', { name: '确定' }).click()
    await expect(page.getByText('请选择 CSV/XLSX 文件')).toBeVisible()

    expect(dialogs).toHaveLength(0)
  })

  test('需求列表支持行级编辑和删除入口', async ({ page }) => {
    const dialogs: string[] = []
    page.on('dialog', (dialog) => {
      dialogs.push(dialog.message())
      void dialog.dismiss()
    })

    await page.goto('/projects/1/requirements/docs', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('登录需求')).toBeVisible()
    await page.getByRole('button', { name: '编辑 登录需求' }).click()
    await expect(page.getByLabel('编辑标题')).toBeVisible()
    await page.getByLabel('编辑标题').fill('登录需求-已编辑')
    await page.getByRole('button', { name: '保存 登录需求' }).click()
    await expect(page.getByText('更新成功：登录需求-已编辑')).toBeVisible()

    await page.getByRole('button', { name: '删除 登录需求' }).click()
    await expect(page.getByText('确定删除需求文档？')).toBeVisible()
    await page.getByRole('button', { name: '确认' }).click()
    await expect(page.getByText('删除成功：登录需求')).toBeVisible()
    expect(dialogs).toHaveLength(0)
  })

  test('需求中心展示总览并支持快捷筛选', async ({ page }) => {
    await page.goto('/projects/1/requirements/docs', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('需求资产总览')).toBeVisible()
    await expect(page.getByText('当前列表')).toBeVisible()
    await expect(page.getByText('评审中', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('已发布', { exact: true }).first()).toBeVisible()

    await expect(page.getByText('登录需求')).toBeVisible()
    await expect(page.getByText('支付评审需求')).toBeVisible()

    await page.getByRole('button', { name: '只看评审中' }).click()
    await expect(page.getByText('当前条件')).toBeVisible()
    await expect(page.getByText('评审中', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('支付评审需求')).toBeVisible()
    await expect(page.getByText('登录需求')).toBeHidden()

    await page.getByRole('button', { name: '清空筛选' }).click()
    await expect(page.getByText('登录需求')).toBeVisible()
  })

  test('接口集合导入入口提供调试闭环引导', async ({ page }) => {
    await page.goto('/projects/1/assets/apis', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('登录接口集合').first()).toBeVisible()
    await page.getByRole('button', { name: '导入接口集合' }).click()
    await expect(page.getByText('Postman / Swagger / OpenAPI')).toBeVisible()
    await expect(page.getByText('导入后进入集合详情页进行单请求运行、保存、导出和绑定用例')).toBeVisible()
    await expect(page.getByRole('button', { name: '去当前集合调试' })).toBeVisible()
  })

  test('接口管理展示总览并支持接口搜索与调试入口', async ({ page }) => {
    await page.goto('/projects/1/assets/apis', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('接口资产总览')).toBeVisible()
    await expect(page.getByText('集合数')).toBeVisible()
    await expect(page.getByText('请求数')).toBeVisible()
    await expect(page.getByText('当前集合', { exact: true })).toBeVisible()

    await page.getByPlaceholder('搜索集合 / 文件夹 / 接口').fill('状态')
    await expect(page.getByText('匹配 1 个请求')).toBeVisible()
    await expect(page.getByText('登录状态')).toBeVisible()
    await expect(page.getByText('登录', { exact: true })).toBeHidden()

    await page.getByPlaceholder('搜索集合 / 文件夹 / 接口').fill('不存在')
    await expect(page.getByText('没有匹配的接口：不存在')).toBeVisible()

    await page.getByRole('button', { name: '清空搜索' }).click()
    await expect(page.getByText('登录', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: '调试当前集合' }).click()
    await expect(page).toHaveURL(/\/projects\/1\/assets\/apis\/col-1/)
  })

  test('接口管理支持记录现场业务反馈', async ({ page }) => {
    await page.goto('/projects/1/assets/apis', { waitUntil: 'domcontentloaded' })

    await page.getByRole('button', { name: '记录反馈' }).click()
    await expect(page.getByText('现场反馈')).toBeVisible()
    await page.getByLabel('反馈类型').selectOption('USABILITY')
    await page.getByPlaceholder('记录业务现场反馈').fill('搜索结果不够明显，需要显示命中数量')
    await page.getByRole('button', { name: '保存反馈' }).click()

    await expect(page.getByText('已记录反馈')).toBeVisible()
    await expect(page.getByText('搜索结果不够明显，需要显示命中数量')).toBeVisible()
  })
})
