from playwright.sync_api import Page

class BaiduPage:
    def __init__(self, page: Page):
        self.page = page
        self.base_url = base_url.rstrip('/')

    def open(self, path: str = '') -> None:
        target = f"{self.base_url}/{path.lstrip('/')}" if path else self.base_url
        self.page.goto(target, wait_until='networkidle')

    def assert_loaded(self) -> None:
        self.page.locator('#s_is_result_css').first.wait_for()
