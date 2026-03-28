import { expect, test } from '@playwright/test'

test.describe('sample-login-page P0 验证', () => {
  test('页面关键元素校验', async ({ page }, testInfo) => {
    await page.goto('/login')

    await expect(page).toHaveURL(/\/login(?:\?.*)?$/)
    await expect(page.getByText('AI 测试平台', { exact: true })).toBeVisible()
    await expect(page.getByText('智能化测试资产管理与执行编排', { exact: true })).toBeVisible()
    await expect(page.getByText('账号登录', { exact: true })).toBeVisible()
    await expect(page.getByText('注册账号', { exact: true })).toBeVisible()
    await expect(page.getByText('用户名', { exact: true })).toBeVisible()
    await expect(page.getByText('密码', { exact: true })).toBeVisible()
    await expect(page.getByText('登 录', { exact: true })).toBeVisible()
  })
})
