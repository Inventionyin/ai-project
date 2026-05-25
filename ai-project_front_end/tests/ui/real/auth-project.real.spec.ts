import { expect, test } from '@playwright/test'

const runRealE2E = process.env.WEITESTING_REAL_E2E === '1'
const apiBaseUrl = process.env.WEITESTING_API_BASE_URL || 'http://127.0.0.1:8000'

type ApiEnvelope<T> = {
  code?: number
  message?: string
  data?: T
}

test.describe('real backend auth and project flow', () => {
  test.skip(!runRealE2E, 'Set WEITESTING_REAL_E2E=1 and start the backend to run real integration E2E.')

  test('creates an internal account, logs in, creates a project, and opens its dashboard', async ({ page, request }) => {
    const health = await request.get(`${apiBaseUrl}/health`)
    expect(health.ok(), `Backend health check failed at ${apiBaseUrl}/health`).toBeTruthy()

    const suffix = `${Date.now()}${Math.floor(Math.random() * 1000)}`.slice(-10)
    const username = `ui_auth_${suffix}`
    const phone = `13${suffix.slice(0, 9)}`
    const password = 'RealE2e123'
    const projectName = `真实联调项目 ${suffix}`

    const registerResponse = await request.post(`${apiBaseUrl}/api/auth/register`, {
      data: { phone, username, password, confirmPassword: password, captcha: '123456' }
    })
    const registerPayload = (await registerResponse.json().catch(() => ({}))) as ApiEnvelope<{ userId: string }>
    expect(registerResponse.ok(), `register HTTP failed: ${registerResponse.status()} ${JSON.stringify(registerPayload)}`).toBeTruthy()
    expect(registerPayload.code, `register business failed: ${JSON.stringify(registerPayload)}`).toBe(0)

    await page.goto('/login')
    await expect(page.getByRole('button', { name: '注册账号' })).toHaveCount(0)
    await page.getByPlaceholder('请输入邮箱').fill(username)
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
