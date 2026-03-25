import { expect, test } from '@playwright/test'

test.describe('sample-login-page P0 验证', () => {
  test('登录页固定字段可见', async ({ page }) => {
    await page.goto('/login')

    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByRole('heading', { name: 'AI 测试平台' })).toBeVisible()
    await expect(page.getByText('智能化测试资产管理与执行编排')).toBeVisible()
    await expect(page.getByRole('button', { name: '账号登录' })).toBeVisible()
    await expect(page.getByRole('button', { name: '注册账号' })).toBeVisible()
    await expect(page.getByRole('button', { name: '登 录' })).toBeVisible()
  })
})
