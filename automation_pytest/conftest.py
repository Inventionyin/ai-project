import os
import socket
from urllib.parse import urlparse

import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.getenv("UI_BASE_URL", "http://localhost:5173/")


def _can_connect(url: str, timeout_s: float = 1.5) -> bool:
    parsed = urlparse(url)
    if not parsed.hostname:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((parsed.hostname, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def pytest_runtest_setup(item: pytest.Item) -> None:
    if not item.get_closest_marker("ui"):
        return
    url = os.getenv("UI_BASE_URL", " http://localhost:5173/")
    if not _can_connect(url):
        pytest.fail(
            f"UI 服务不可访问: {url}。请先启动前端（例如运行 start-dev.bat 或 npm run dev），"
            f"或设置环境变量 UI_BASE_URL 指向已启动的地址。"
        )


@pytest.fixture
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        pg = context.new_page()
        yield pg
        context.close()
        browser.close()
