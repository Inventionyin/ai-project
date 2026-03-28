from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional, cast
from urllib.parse import urljoin

from playwright.sync_api import Locator, Page


WaitUntil = Literal["commit", "domcontentloaded", "load", "networkidle"]
LocatorStrategy = Literal[
    "css",
    "testid",
    "text",
    "placeholder",
    "label",
    "role",
]


@dataclass(frozen=True)
class LocatorSpec:
    strategy: LocatorStrategy
    value: str
    role_name: Optional[str] = None


class PlaywrightBasicPage:
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url.strip().rstrip("/") + "/"

    def build_url(self, path: str = "") -> str:
        return urljoin(self.base_url, path.lstrip("/"))

    def open(self, path: str = "", wait_until: WaitUntil = "networkidle") -> None:
        self.page.goto(self.build_url(path), wait_until=wait_until)

    def goto(self, url: str, wait_until: WaitUntil = "networkidle") -> None:
        self.page.goto(url, wait_until=wait_until)

    def by_test_id(self, test_id: str) -> Locator:
        return self.page.get_by_test_id(test_id)

    def by_text(self, text: str) -> Locator:
        return self.page.get_by_text(text)

    def by_placeholder(self, placeholder: str) -> Locator:
        return self.page.get_by_placeholder(placeholder)

    def by_label(self, label: str) -> Locator:
        return self.page.get_by_label(label)

    def by_css(self, css: str) -> Locator:
        return self.page.locator(css)

    def by_role(self, role: str, name: Optional[str] = None) -> Locator:
        if name is None:
            return self.page.get_by_role(cast(Any, role))
        return self.page.get_by_role(cast(Any, role), name=name)

    def locate(self, spec: LocatorSpec) -> Locator:
        if spec.strategy == "testid":
            return self.by_test_id(spec.value)
        if spec.strategy == "css":
            return self.by_css(spec.value)
        if spec.strategy == "text":
            return self.by_text(spec.value)
        if spec.strategy == "placeholder":
            return self.by_placeholder(spec.value)
        if spec.strategy == "label":
            return self.by_label(spec.value)
        if spec.strategy == "role":
            return self.by_role(spec.value, name=spec.role_name)
        raise ValueError(f"Unsupported locator strategy: {spec.strategy}")

    def click(self, locator: Locator) -> None:
        locator.click()

    def fill(self, locator: Locator, value: str) -> None:
        locator.fill(value)

    def wait_visible(self, locator: Locator, timeout_ms: int = 10_000) -> None:
        locator.wait_for(state="visible", timeout=timeout_ms)

    def wait_attached(self, locator: Locator, timeout_ms: int = 10_000) -> None:
        locator.wait_for(state="attached", timeout=timeout_ms)

    def wait_hidden(self, locator: Locator, timeout_ms: int = 10_000) -> None:
        locator.wait_for(state="hidden", timeout=timeout_ms)

    def current_url(self) -> str:
        return self.page.url

    def reload(self, wait_until: WaitUntil = "networkidle") -> None:
        self.page.reload(wait_until=wait_until)

    def screenshot_bytes(self, full_page: bool = True) -> bytes:
        return self.page.screenshot(full_page=full_page)
