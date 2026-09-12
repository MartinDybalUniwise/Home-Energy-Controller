"""Browser smoke tests against the isolated, hardware-free preview."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page

pytestmark = pytest.mark.e2e


def set_language_in_settings(page: Page, language: str) -> None:
    if page.viewport_size and page.viewport_size["width"] <= 1023:
        page.locator("#menu-toggle").click()
    page.locator("#more-toggle").click()
    page.locator('#utility-nav a[data-page="settings"]').click()
    page.locator("#f_ui_language").select_option(language)
    page.locator("#settings-form button[type='submit']").click()


@pytest.mark.parametrize("viewport", [(1920, 1080), (1280, 800), (1024, 768), (390, 844)])
def test_shell_dashboard_and_settings_navigation(page: Page, viewport: tuple[int, int]):
    from playwright.sync_api import expect

    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    page.goto("/")
    expect(page.locator("#site-name")).to_be_visible()
    expect(page.locator("#view")).to_be_visible()
    expect(page.locator(".notice.error")).to_have_count(0)

    if viewport[0] <= 1023:
        page.locator("#menu-toggle").click()
    page.locator("#more-toggle").click()
    page.locator('#utility-nav a[data-page="settings"]').click()
    expect(page.locator("#settings-form")).to_be_visible()
    page.locator("details.technical-settings").click()
    expect(page.locator("#settings-form input[data-path='controller.enabled']")).to_be_visible()
    expect(page.locator(".notice.error")).to_have_count(0)


def test_czech_navigation_catalog(page: Page):
    from playwright.sync_api import expect

    page.goto("/")
    set_language_in_settings(page, "cs")
    expect(page.locator("html")).to_have_attribute("lang", "cs")
    expect(page.locator('#nav a[data-page="overview"]')).to_contain_text("Dnes")


def test_english_navigation_catalog(page: Page):
    from playwright.sync_api import expect

    page.goto("/")
    set_language_in_settings(page, "en")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.locator('#nav a[data-page="overview"]')).to_contain_text("Today")


@pytest.mark.parametrize("viewport", [(1920, 1080), (1440, 900), (1280, 800), (1024, 768), (390, 844)])
def test_today_screen_touchscreen_redesign(page: Page, viewport: tuple[int, int]):
    from playwright.sync_api import expect

    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    page.goto("/")
    expect(page.locator(".today-screen")).to_be_visible()
    expect(page.locator(".hero-primary-card")).to_be_visible()
    expect(page.locator(".today-kpi-strip")).to_be_visible()
    expect(page.locator(".rhythm-section")).to_be_visible()
    expect(page.locator(".today-workspace-grid")).to_be_visible()
    expect(page.locator(".today-bottom-action-bar")).to_be_visible()
    expect(page.locator(".notice.error")).to_have_count(0)


def test_why_now_dialog_modal(page: Page):
    from playwright.sync_api import expect

    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto("/")
    set_language_in_settings(page, "cs")
    page.goto("/")
    expect(page.locator("#btn-why-now")).to_be_visible()
    page.locator("#btn-why-now").click()
    expect(page.locator("#why-now-dialog")).to_be_visible()
    expect(page.locator("#why-now-dialog h2")).to_contain_text("Proč právě teď")
    page.locator("#why-now-ok").click()
    expect(page.locator("#why-now-dialog")).not_to_be_visible()


def test_energy_flow_screen_rendering(page: Page):
    from playwright.sync_api import expect

    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto("/#/flow")
    expect(page.locator(".flow-hero")).to_be_visible()
    expect(page.locator(".flow-stage")).to_be_visible()
    expect(page.locator(".flow-details")).to_be_visible()
    expect(page.locator(".notice.error")).to_have_count(0)

