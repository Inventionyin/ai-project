import { expect, test } from '@playwright/test'

const runRealE2E = process.env.WEITESTING_REAL_E2E === '1'
const apiBaseUrl = process.env.WEITESTING_API_BASE_URL || 'http://127.0.0.1:8000'

test.describe('real backend auth and project flow', () => {
  test.skip(!runRealE2E, 'Set WEITESTING_REAL_E2E=1 and start the backend to run real integration E2E.')

  test('registers, logs in, creates a project, and opens its dashboard', async ({ page, request }) => {
    const health = await request.get(`${apiBaseUrl}/health`)
    expect(health.ok(), `Backend health check failed at ${apiBaseUrl}/health`).toBeTruthy()

    const suffix = `${Date.now()}${Math.floor(Math.random() * 1000)}`.slice(-10)
    const username = `real_e2e_${suffix}`
    const phone = `13${suffix.slice(0, 9)}`
    const password = 'RealE2e123'
    const projectName = `真实联调项目 ${suffix}`

    await page.goto('/login?tab=register')
    await page.getByPlaceholder('请输入用户名').fill(username)
    await page.getByPlaceholder('请输入手机号').fill(phone)
    await page.getByPlaceholder('请输入验证码').fill('123456')
    await page.getByPlaceholder('请设置密码（至少 8 位，含字母和数字）').fill(password)
    await page.getByPlaceholder('请再次输入密码').fill(password)
    await page.getByRole('button', { name: '注 册' }).click()

    await expect(page.getByRole('button', { name: '登 录' })).toBeVisible()
    await page.getByPlaceholder('请输入用户名').fill(username)
    await page.getByPlaceholder('请输入密码').fill(password)
    await page.getByRole('button', { name: '登 录' }).click()

    await expect(page).toHaveURL(/\/projects/)
    await expect(page.getByText('WeiTesting')).toBeVisible()

    await page.getByRole('button', { name: /新建项目/ }).first().click()
    await page.getByPlaceholder('2-50个字符').fill(projectName)
    await page.getByPlaceholder('可选，0-200个字符').fill('真实后端联调 E2E 创建')
    await page.getByRole('button', { name: /^创建$|创建项目/ }).click()

    await expect(page.getByText(projectName)).toBeVisible()
    await page.getByText(projectName).click()
    await expect(page).toHaveURL(/\/projects\/[^/]+\/dashboard/)
    await expect(page.getByText('仪表盘')).toBeVisible()
  })
})
