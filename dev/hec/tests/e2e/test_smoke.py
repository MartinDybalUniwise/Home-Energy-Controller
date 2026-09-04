"""Browser smoke tests against the isolated, hardware-free preview."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("viewport", [(1280, 800), (1920, 1080), (390, 844)])
def test_shell_dashboard_and_settings_navigation(page: Page, viewport: tuple[int, int]):
    from playwright.sync_api import expect

    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    page.goto("/")
    expect(page.locator("#site-name")).to_be_visible()
    expect(page.locator("#view")).to_be_visible()
    expect(page.locator(".notice.error")).to_have_count(0)

    page.locator("#more-toggle").click()
    page.locator('#utility-nav a[data-page="settings"]').click()
    expect(page.locator("#settings-form")).to_be_visible()
    page.locator("details.technical-settings").click()
    expect(page.locator("#settings-form input[data-path='controller.enabled']")).to_be_visible()
    expect(page.locator(".notice.error")).to_have_count(0)


def test_czech_and_english_navigation_catalogs(page: Page):
    from playwright.sync_api import expect

    page.goto("/")
    expect(page.locator("html")).to_have_attribute("lang", "cs")
    expect(page.locator('nav a[data-page="overview"]')).to_have_text("Dnes")

    page.evaluate("localStorage.setItem('hec_lang', 'en')")
    page.reload()
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.locator('nav a[data-page="overview"]')).to_have_text("Today")
