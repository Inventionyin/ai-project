import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False,slow_mo=2000)cc
    context = browser.new_context()
    page = context.new_page()
    page.goto("http://localhost:5173/login")
    page.locator("div").nth(1).click()
    page.get_by_role("textbox", name="请输入用户名").click()
    page.get_by_role("textbox", name="请输入用户名").fill("momo")
    page.get_by_role("textbox", name="请输入密码").click()
    page.get_by_role("textbox", name="请输入密码").fill("ab123456")
    page.get_by_role("button", name="登 录").click()
  
    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
