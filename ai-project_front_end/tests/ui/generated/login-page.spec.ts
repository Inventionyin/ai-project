import { existsSync } from 'fs'
import { expect, test } from '@playwright/test'

test.describe('login-page P1 验证', () => {
  test('页面关键元素校验', async ({ page }, testInfo) => {
    await page.goto('/login')

    await expect(page).toHaveURL(/\/login(?:\?.*)?$/)

    await page.addStyleTag({
      content: '*{animation-duration:0s!important;transition-duration:0s!important;}'
    })
    const masks = [page.locator('.toast'), page.locator('.captcha'), page.locator('.error-msg')]

    const header = page.getByTestId('auth-header')
    await expect(header).toBeVisible()
    const headerSnapshotName = 'login-page/v1/header__1-2578__v1.png'
    const headerSnapshotPath = testInfo.snapshotPath(headerSnapshotName)
    if (!existsSync(headerSnapshotPath)) {
      testInfo.annotations.push({ type: 'missing-baseline', description: headerSnapshotName })
    } else {
      await expect(header).toHaveScreenshot(headerSnapshotName, { maxDiffPixelRatio: 0.01, mask: masks })
    }

    const main = page.getByTestId('auth-main')
    await expect(main).toBeVisible()
    const mainSnapshotName = 'login-page/v1/main__1-2578__v1.png'
    const mainSnapshotPath = testInfo.snapshotPath(mainSnapshotName)
    if (!existsSync(mainSnapshotPath)) {
      testInfo.annotations.push({ type: 'missing-baseline', description: mainSnapshotName })
    } else {
      await expect(main).toHaveScreenshot(mainSnapshotName, { maxDiffPixelRatio: 0.01, mask: masks })
    }

    const login_formPreferred = page.getByTestId('login-form')
    const login_formFallback = page.locator('.login-form')
    const login_form = (await login_formPreferred.count()) ? login_formPreferred : login_formFallback
    await expect(login_form).toBeVisible()
    const login_formSnapshotName = 'login-page/v1/login-form.png'
    const login_formSnapshotPath = testInfo.snapshotPath(login_formSnapshotName)
    if (!existsSync(login_formSnapshotPath)) {
      testInfo.annotations.push({ type: 'missing-baseline', description: login_formSnapshotName })
    } else {
      await expect(login_form).toHaveScreenshot(login_formSnapshotName, { maxDiffPixelRatio: 0.003, mask: masks })
    }
  })
})
