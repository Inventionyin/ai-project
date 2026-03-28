from playwright.sync_api import Page

class ProjectsV1Page:
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url.rstrip('/')

    def open(self, path: str = '') -> None:
        target = f"{self.base_url}/{path.lstrip('/')}" if path else self.base_url
        self.page.goto(target, wait_until='networkidle')

    def assert_loaded(self) -> None:
        self.page.get_by_test_id('auth-header').wait_for()
