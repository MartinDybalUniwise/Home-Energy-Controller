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

    if viewport[0] >= 1100:
        sidebar_box = page.locator("#sidebar").bounding_box()
        view_box = page.locator("#view").bounding_box()
        assert sidebar_box is not None
        assert view_box is not None
        assert abs(view_box["x"] - sidebar_box["x"] - sidebar_box["width"]) <= 1

    if viewport[0] <= 1023:
        page.locator("#menu-toggle").click()
    page.locator("#more-toggle").click()
    page.locator('#utility-nav a[data-page="settings"]').click()
    expect(page.locator("#settings-form")).to_be_visible()
    page.locator("details.technical-settings").click()
    expect(page.locator("#settings-form input[data-path='controller.enabled']")).to_be_visible()
    expect(page.locator(".notice.error")).to_have_count(0)


def test_sidebar_service_menu_toggle(page: Page):
    from playwright.sync_api import expect

    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto("/")
    toggle = page.locator("#more-toggle")
    utility = page.locator("#utility-nav")

    expect(utility).to_be_hidden()
    expect(toggle).to_have_attribute("aria-expanded", "false")
    toggle.click()
    expect(utility).to_be_visible()
    expect(toggle).to_have_attribute("aria-expanded", "true")
    toggle.click()
    expect(utility).to_be_hidden()
    expect(toggle).to_have_attribute("aria-expanded", "false")


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
    expect(page.locator(".today-recommendation-panel")).to_be_visible()
    expect(page.locator(".today-kpi-strip")).to_be_visible()
    expect(page.locator(".rhythm-section")).to_be_visible()
    expect(page.locator(".today-workspace-grid")).to_be_visible()
    expect(page.locator(".recommendation-status")).to_have_count(3)
    expect(page.locator(".next-window-card")).to_have_count(0)
    expect(page.locator(".today-bottom-action-bar")).to_have_count(0)
    expect(page.locator(".notice.error")).to_have_count(0)


def test_today_cockpit_fits_full_hd_without_page_scroll(page: Page):
        from playwright.sync_api import expect

        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto("/")
        expect(page.locator(".today-screen")).to_be_visible()

        geometry = page.evaluate("""() => {
            const root = document.documentElement;
            const box = (selector) => document.querySelector(selector).getBoundingClientRect();
            const selectors = [
                '.today-header',
                '.today-recommendation-panel',
                '.today-kpi-strip',
                '.rhythm-section',
                '.today-workspace-grid',
                '.appliances-card',
                '.forecast-chart-card',
            ];
            const sidebar = box('#sidebar');
            const cockpit = box('.today-screen');
            const sections = selectors.slice(0, 5).map(box);
            return {
                viewportHeight: window.innerHeight,
                pageHeight: root.scrollHeight,
                pageWidth: root.scrollWidth,
                viewportWidth: window.innerWidth,
                cockpitBottom: cockpit.bottom,
                sidebarWidth: sidebar.width,
                headerHeight: box('.today-header').height,
                recommendationHeight: box('.today-recommendation-panel').height,
                kpiHeight: box('.today-kpi-strip').height,
                rhythmHeight: box('.rhythm-section').height,
                workspaceHeight: box('.today-workspace-grid').height,
                clipped: selectors.filter((selector) => {
                    const element = document.querySelector(selector);
                    return element.scrollHeight > element.clientHeight + 1 || element.scrollWidth > element.clientWidth + 1;
                }),
                clipDetails: selectors.map((selector) => {
                    const element = document.querySelector(selector);
                    return {
                        selector,
                        clientWidth: element.clientWidth,
                        scrollWidth: element.scrollWidth,
                        clientHeight: element.clientHeight,
                        scrollHeight: element.scrollHeight,
                    };
                }),
                recommendationDimensions: (() => {
                    const element = document.querySelector('.today-recommendation-panel');
                    return {
                        clientWidth: element.clientWidth,
                        scrollWidth: element.scrollWidth,
                        clientHeight: element.clientHeight,
                        scrollHeight: element.scrollHeight,
                    };
                })(),
                overlap: sections.some((section, index) => index > 0 && section.top < sections[index - 1].bottom),
            };
        }""")

        assert 190 <= geometry["sidebarWidth"] <= 210
        assert geometry["pageHeight"] <= geometry["viewportHeight"]
        assert geometry["pageWidth"] <= geometry["viewportWidth"]
        assert geometry["cockpitBottom"] <= geometry["viewportHeight"]
        assert 100 <= geometry["headerHeight"] <= 120
        assert 90 <= geometry["recommendationHeight"] <= 110
        assert 90 <= geometry["kpiHeight"] <= 105
        assert 260 <= geometry["rhythmHeight"] <= 290
        assert 300 <= geometry["workspaceHeight"] <= 330
        assert geometry["clipped"] == [], geometry["recommendationDimensions"]
        assert geometry["overlap"] is False


@pytest.mark.parametrize("viewport", [(1920, 1080), (1440, 900), (1280, 800), (1024, 768)])
def test_today_desktop_panels_use_full_content_width(page: Page, viewport: tuple[int, int]):
        from playwright.sync_api import expect

        page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
        page.goto("/")
        expect(page.locator(".today-recommendation-panel")).to_be_visible()

        widths = page.evaluate("""() => {
            const box = (selector) => document.querySelector(selector).getBoundingClientRect();
            const cockpit = box('.today-screen');
            const rhythm = box('.rhythm-section');
            const workspace = box('.today-workspace-grid');
            const appliances = box('.appliances-card');
            const chart = box('.forecast-chart-card');
            return {
                cockpit: cockpit.width,
                rhythm: rhythm.width,
                workspace: workspace.width,
                lowerUsed: appliances.width + chart.width + Math.max(0, chart.left - appliances.right),
            };
        }""")

        assert abs(widths["rhythm"] - widths["cockpit"]) <= 1
        assert abs(widths["workspace"] - widths["cockpit"]) <= 1
        assert abs(widths["lowerUsed"] - widths["workspace"]) <= 1


@pytest.mark.parametrize("viewport", [(1440, 900), (1280, 800)])
def test_today_cockpit_fits_scaled_desktop_display(page: Page, viewport: tuple[int, int]):
        from playwright.sync_api import expect

        page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
        page.goto("/")
        expect(page.locator(".today-recommendation-panel")).to_be_visible()

        geometry = page.evaluate("""() => {
            const selectors = [
                '.today-header',
                '.today-recommendation-panel',
                '.today-kpi-strip',
                '.rhythm-section',
                '.today-workspace-grid',
                '.appliances-card',
                '.forecast-chart-card',
            ];
            const sections = selectors.slice(0, 5).map((selector) => document.querySelector(selector).getBoundingClientRect());
            return {
                viewportHeight: window.innerHeight,
                pageHeight: document.documentElement.scrollHeight,
                cockpitBottom: document.querySelector('.today-screen').getBoundingClientRect().bottom,
                clipped: selectors.filter((selector) => {
                    const element = document.querySelector(selector);
                    return element.scrollHeight > element.clientHeight + 1 || element.scrollWidth > element.clientWidth + 1;
                }),
                clipDetails: selectors.map((selector) => {
                    const element = document.querySelector(selector);
                    return {
                        selector,
                        clientWidth: element.clientWidth,
                        scrollWidth: element.scrollWidth,
                        clientHeight: element.clientHeight,
                        scrollHeight: element.scrollHeight,
                    };
                }),
                recommendationDimensions: (() => {
                    const element = document.querySelector('.today-recommendation-panel');
                    return {
                        clientWidth: element.clientWidth,
                        scrollWidth: element.scrollWidth,
                        clientHeight: element.clientHeight,
                        scrollHeight: element.scrollHeight,
                    };
                })(),
                overlap: sections.some((section, index) => index > 0 && section.top < sections[index - 1].bottom),
            };
        }""")

        assert geometry["pageHeight"] <= geometry["viewportHeight"]
        assert geometry["cockpitBottom"] <= geometry["viewportHeight"]
        assert geometry["clipped"] == [], geometry["recommendationDimensions"]
        assert geometry["overlap"] is False


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


@pytest.mark.parametrize("viewport", [(1920, 1080), (1024, 768), (390, 844)])
def test_energy_flow_screen_rendering(page: Page, viewport: tuple[int, int]):
    from playwright.sync_api import expect

    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    page.goto("/#/flow")
    expect(page.locator(".flow-hero")).to_be_visible()
    expect(page.locator(".flow-stage")).to_be_visible()
    expect(page.locator(".flow .main-node")).to_have_count(4)
    expect(page.locator(".flow .appliance-node")).to_have_count(6)
    expect(page.locator(".flow .appliance-node__icon")).to_have_count(6)
    expect(page.locator(".flow .wire")).to_have_count(8)
    expect(page.locator(".flow-details")).to_be_visible()
    expect(page.locator(".notice.error")).to_have_count(0)

