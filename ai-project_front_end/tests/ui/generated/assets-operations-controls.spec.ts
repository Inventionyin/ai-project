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
              total: 1,
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
              ],
            },
          }),
        })
      }

      if (url.pathname === '/api/projects/1/requirements/docs') {
        if (req.method() === 'GET') {
          return route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              code: 0,
              data: {
                page: 1,
                pageSize: 50,
                total: 1,
                items: [
                  {
                    id: 'doc-1',
                    projectId: '1',
                    title: '登录需求',
                    status: 'DRAFT',
                    sourceType: 'PRD',
                    tags: ['登录'],
                    updatedAt: '2026-05-25 10:00',
                  },
                ],
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
                  requests: [{ id: 'req-1', collectionId: 'col-1', groupId: 'grp-1', name: '登录', method: 'POST', url: '/api/login' }],
                },
              ],
              requests: [],
              updatedAt: 1710000000,
            },
          }),
        })
      }

      return route.continue()
    })
  })

  test('用例管理支持导出当前列表', async ({ page }) => {
    await page.goto('/projects/1/assets/testcases', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('登录成功')).toBeVisible()
    await expect(page.getByRole('button', { name: '导出CSV' })).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: '导出CSV' }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/testcases.*\.csv$/)
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
    await page.getByRole('button', { name: '上传用例' }).click()
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

  test('接口集合导入入口提供调试闭环引导', async ({ page }) => {
    await page.goto('/projects/1/assets/apis', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('登录接口集合')).toBeVisible()
    await page.getByRole('button', { name: '导入接口集合' }).click()
    await expect(page.getByText('Postman / Swagger / OpenAPI')).toBeVisible()
    await expect(page.getByText('导入后进入集合详情页进行单请求运行、保存、导出和绑定用例')).toBeVisible()
    await expect(page.getByRole('button', { name: '去当前集合调试' })).toBeVisible()
  })
})
