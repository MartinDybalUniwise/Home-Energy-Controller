"""Browser smoke tests against the isolated, hardware-free preview."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
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
    # Reload/navigation must wait for persistence, including response errors.
    with page.expect_response(
        lambda response: response.url.endswith("/api/config")
        and response.request.method == "PUT"
    ) as saved:
        page.locator("#settings-form button[type='submit']").click()
    assert saved.value.ok, saved.value.text()
    assert saved.value.json()["saved"] is True


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


def test_settings_can_verify_sdg_path_without_saving(page: Page):
    import re

    from playwright.sync_api import expect

    page.goto("/")
    if page.viewport_size and page.viewport_size["width"] <= 1023:
        page.locator("#menu-toggle").click()
    page.locator("#more-toggle").click()
    page.locator('#utility-nav a[data-page="settings"]').click()
    page.locator("details.technical-settings").click()
    button = page.locator('[data-verify-target="sdg"]')
    expect(button).to_be_visible()
    button.click()
    expect(button.locator("xpath=following-sibling::span[contains(@class, 'field-verify-result')]")).to_have_text(re.compile(r".+"))


def test_settings_goodwe_authorization_flow_renders_and_enables_after_verify(page: Page):
    from playwright.sync_api import expect

    current_host = ""

    def route_api(route):
        url = route.request.url
        if url.endswith("/api/goodwe/authorization"):
            route.fulfill(status=200, content_type="application/json", body=(
                '{"authorization":{"status":"NOT_AUTHORIZED"},"verification":null}'
            ))
            return
        if url.endswith("/api/goodwe/authorization/verify"):
            route.fulfill(status=200, content_type="application/json", body=(
                f'{{"status":"SUCCESS","verified":true,"host":"{current_host}",'
                '"model":"FAKE-ET","firmware":"1.2.3","evidence_id":"e2e-evidence",'
                '"verified_at":"2026-09-15T20:00:00+02:00","message_key":"settings.goodwe_verify_ok"}'
            ))
            return
        if url.endswith("/api/goodwe/authorization/approve"):
            route.fulfill(status=200, content_type="application/json", body=(
                f'{{"authorization":{{"status":"APPROVED","device_host":"{current_host}",'
                '"evidence_id":"e2e-evidence","approved_by":"config-ui",'
                '"approved_at":"2026-09-15T20:01:00+02:00"},'
                f'"verification":{{"status":"SUCCESS","verified":true,"host":"{current_host}",'
                '"model":"FAKE-ET","firmware":"1.2.3","evidence_id":"e2e-evidence",'
                '"message_key":"settings.goodwe_verify_ok"}}'
            ))
            return
        route.continue_()

    page.route("**/api/goodwe/authorization**", route_api)
    page.goto("/#/settings")
    page.locator("details.technical-settings").click()

    panel = page.locator("[data-goodwe-authorization]")
    expect(panel).to_be_visible()
    expect(page.locator("[data-goodwe-approve]")).to_be_disabled()
    current_host = page.locator('[data-path="goodwe.host"]').input_value()

    page.locator("[data-goodwe-verify]").click()
    expect(page.locator("[data-goodwe-approve]")).to_be_enabled()
    expect(panel).to_contain_text("FAKE-ET")

    page.locator("[data-goodwe-approve]").click()
    expect(panel).to_contain_text("APPROVED")


def test_history_renders_sdg_history_source(page: Page):
    from playwright.sync_api import expect

    def route_api(route):
        if route.request.url.endswith("/api/sources"):
            route.fulfill(status=200, content_type="application/json",
                          body='{"sources":["sdg_history"]}')
            return
        if "/api/history?" in route.request.url:
            route.fulfill(status=200, content_type="application/json", body=(
                '{"source":"sdg_history","from":"2026-09-14T10:00:00+02:00",'
                '"to":"2026-09-14T10:05:00+02:00","bucket_seconds":0,'
                '"fields":["total__w"],"count":1,"raw_count":1,'
                '"rows":[{"timestamp":"2026-09-14T10:05:00+02:00","total__w":123}]}'
            ))
            return
        route.continue_()

    page.route("**/api/**", route_api)
    page.goto("/#/history")
    expect(page.locator("#source")).to_have_value("sdg_history")
    page.locator("#toggle-view").click()
    expect(page.locator("#table")).to_contain_text("123")


def test_prediction_renders_forecast_without_application_error(page: Page):
    from playwright.sync_api import expect

    def route_api(route):
        if route.request.url.endswith("/api/prediction"):
            route.fulfill(status=200, content_type="application/json", body=(
                '{"available":true,"generated_at":"2026-09-15T18:37:40+02:00",'
                '"days":[{"date":"2026-09-16","pv_kwh":99.7,"pv_kwh_low":79.8,'
                '"pv_kwh_high":119.6,"irradiation_kwh_m2":4.257,"confidence":"medium",'
                '"consumption_kwh":16.87,"cost_czk":120,"best_appliance_window":"12:30–14:30",'
                '"best_dhw_window":"12:30–14:30"},{"date":"2026-09-17",'
                '"pv_kwh":70.5,"pv_kwh_low":56.4,"pv_kwh_high":84.6,'
                '"irradiation_kwh_m2":3.1,"confidence":"medium","consumption_kwh":16.87,'
                '"cost_czk":130}]}'
            ))
            return
        route.continue_()

    page.route("**/api/**", route_api)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("/#/prediction")
    expect(page.locator(".forecast-day-card").first).to_be_visible()
    expect(page.locator(".notice.error")).to_have_count(0)
    assert not any("formatCurrency" in error for error in errors)


def delay_status_without_blocking_other_requests(page: Page):
    # Sleeping in a sync route handler freezes dispatch of unrelated requests too.
    # Isolate this latency regression from unrelated loopback/API variance.
    # Real backend integration remains covered by the other browser tests.
    catalog = json.loads((Path(__file__).parents[2] / "locales" / "cs.json").read_text(encoding="utf-8"))
    page.add_init_script("""(() => {
      const originalFetch = window.fetch.bind(window);
      const fastResponses = {
        '/api/session': {required: false, authorised: true},
        '/api/i18n/cs': {lang: 'cs', available: ['cs', 'en'], catalog: __CS_CATALOG__},
        '/api/current': {sources: {}, readers: {}},
        '/api/weather': {},
        '/api/prices': {},
        '/api/prediction': {
          available: true, generated_at: '2026-09-15T18:37:40+02:00',
          days: [{date: '2026-09-16', pv_kwh: 99.7, pv_kwh_low: 79.8,
            pv_kwh_high: 119.6, irradiation_kwh_m2: 4.257,
            confidence: 'medium', consumption_kwh: 16.87, cost_czk: 120}]
        }
      };
      const response = payload => new Response(JSON.stringify(payload),
        {status: 200, headers: {'Content-Type': 'application/json'}});
      window.fetch = (input, options) => {
        const target = input instanceof Request ? input.url : String(input);
        const url = new URL(target, window.location.href);
        if (url.origin === window.location.origin && url.pathname === '/api/status') {
          return new Promise(resolve => setTimeout(() => resolve(response(
            {ui: {language: 'cs', animations: 'reduced', theme: 'dark'}}
          )), 2000));
        }
        if (url.origin === window.location.origin && url.pathname in fastResponses) {
          return Promise.resolve(response(fastResponses[url.pathname]));
        }
        return originalFetch(input, options);
      };
    })();""".replace("__CS_CATALOG__", json.dumps(catalog)))


def test_prediction_renders_when_status_is_slow(page: Page):
    from playwright.sync_api import expect

    delay_status_without_blocking_other_requests(page)
    page.goto("/#/prediction")
    expect(page.locator(".forecast-day-card").first).to_be_visible()


def test_today_renders_when_status_is_slow(page: Page):
    from playwright.sync_api import expect

    delay_status_without_blocking_other_requests(page)
    page.goto("/")
    expect(page.locator(".today-screen")).to_be_visible()


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


def test_control_plan_read_only_monitor(page: Page):
    import re

    from playwright.sync_api import expect

    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto("/")
    set_language_in_settings(page, "cs")
    page.goto("/#/control-plan")
    expect(page.locator(".control-plan-page")).to_be_visible()
    expect(page.locator(".control-plan-status")).to_be_visible()
    expect(page.locator(".control-plan-devices")).to_be_visible()
    expect(page.locator(".control-plan-lower")).to_be_visible()
    expect(page.locator(".control-plan-status")).to_contain_text(re.compile("Zápis|Writing"))
    expect(page.locator(".control-plan-page")).to_contain_text(re.compile("Topení|Heating"))
    expect(page.locator(".control-plan-page")).to_contain_text(re.compile("Baterie|Battery"))
    expect(page.locator(".control-plan-page")).to_contain_text(re.compile("Dnes|Today"))
    expect(page.locator(".control-plan-page")).to_contain_text(re.compile("Zítra|Tomorrow"))
    expect(page.locator(".control-plan-daily-energy")).to_be_visible()
    expect(page.locator(".control-plan-mode")).to_have_count(2)
    expect(page.locator(".notice.error")).to_have_count(0)


def test_control_plan_english_catalog(page: Page):
    from playwright.sync_api import expect

    page.goto("/")
    set_language_in_settings(page, "en")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    page.reload()
    expect(page.locator("html")).to_have_attribute("lang", "en")
    page.goto("/#/control-plan")
    expect(page.locator(".control-plan-page")).to_contain_text("Control & Plan")
    expect(page.locator(".control-plan-page")).to_contain_text("Heating")
    expect(page.locator(".notice.error")).to_have_count(0)


def test_control_plan_groups_decisions_and_opens_detail(page: Page):
    from playwright.sync_api import expect

    timestamp = datetime.now(UTC).isoformat()
    decision = {
        "timestamp": timestamp,
        "rule": "goodwe_charge_cheap",
        "action": "start_battery_charge",
        "value": 50,
        "applied": False,
        "reason_key": "reason.goodwe_charge_cheap",
        "reason_params": {"price": 0.5},
    }

    def route_api(route):
        if "/api/decisions?" in route.request.url:
            route.fulfill(status=200, content_type="application/json", body=(
                json.dumps({"decisions": [decision, decision], "state": {}})
            ))
            return
        route.continue_()

    page.route("**/api/**", route_api)
    page.goto("/#/control-plan")
    expect(page.locator(".control-plan-activity tbody tr")).to_have_count(1)
    expect(page.locator(".control-plan-activity__count")).to_contain_text("2")
    expect(page.locator(".control-plan-status .pill[title]").first).to_be_visible()
    expect(page.locator(".control-plan-mode[title]").first).to_be_visible()
    page.locator(".control-plan-activity tbody tr").click()
    expect(page.locator("#control-plan-decision-dialog")).to_be_visible()
    expect(page.locator("#control-plan-decision-dialog")).to_contain_text("start_battery_charge")
    page.keyboard.press("Escape")
    expect(page.locator("#control-plan-decision-dialog")).to_be_hidden()
    page.locator(".control-plan-activity tbody tr").click()
    page.locator("#control-plan-decision-dialog [data-control-plan-close]").last.click()
    expect(page.locator("#control-plan-decision-dialog")).to_be_hidden()


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


def test_today_readable_full_hd_uses_natural_vertical_scroll(page: Page):
    from playwright.sync_api import expect

    page.set_viewport_size({'width':1920,'height':1080})
    page.goto('/')
    expect(page.locator('.today-screen')).to_be_visible()
    # Step33 deliberately replaces the old fit-everything-in-1080px requirement.
    assert page.locator('.today-header').evaluate('e=>e.getBoundingClientRect().height') >= 150
    assert page.locator('.kpi-value').first.evaluate('e=>parseFloat(getComputedStyle(e).fontSize)') >= 30
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
    assert page.evaluate('document.documentElement.scrollHeight > innerHeight')
    page.locator('.forecast-chart-card').scroll_into_view_if_needed()
    expect(page.locator('.forecast-chart-card')).to_be_visible()


@pytest.mark.parametrize("viewport", [(1920, 1080), (1440, 900), (1280, 800), (1024, 768)])
def test_today_desktop_panels_use_full_content_width(page: Page, viewport: tuple[int, int]):
        from playwright.sync_api import expect

        page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
        page.goto("/")
        # Geometry is measured after data rendering; startup latency has separate tests.
        page.locator(".today-screen").wait_for()
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
                lowerUsed: Math.abs(appliances.top-chart.top)<2 ? appliances.width + chart.width + Math.max(0, chart.left-appliances.right) : Math.max(appliances.width,chart.width),
            };
        }""")

        assert abs(widths["rhythm"] - widths["cockpit"]) <= 1
        assert abs(widths["workspace"] - widths["cockpit"]) <= 1
        assert abs(widths["lowerUsed"] - widths["workspace"]) <= 1


@pytest.mark.parametrize("viewport", [(1440, 900), (1280, 800)])
def test_today_scaled_desktop_preserves_readability_and_reflow(page: Page, viewport: tuple[int, int]):
    from playwright.sync_api import expect

    page.set_viewport_size({'width':viewport[0],'height':viewport[1]})
    page.goto('/')
    expect(page.locator('.today-screen')).to_be_visible()
    for zoom in [100,200]:
        page.add_style_tag(content=f'html {{font-size:{zoom}% !important}}')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        for selector in ['.today-header','.hero-primary-card','.today-kpi-strip','.forecast-chart-card']:
            assert page.locator(selector).evaluate('e=>e.scrollWidth<=e.clientWidth+1 && e.scrollHeight<=e.clientHeight+1'),selector


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
    # Approved redesign uses unscaled HTML appliance readings and no fabricated heat outputs.
    expect(page.locator(".flow-main-readings .flow-reading")).to_have_count(4)
    expect(page.locator(".flow-device-row")).to_have_count(6)
    expect(page.locator(".flow-device-row[data-device='heatpump']")).to_have_count(1)
    expect(page.locator(".flow .appliance-node--service")).to_have_count(0)
    if viewport[0] < 768:
        expect(page.locator(".flow-main-readings")).to_be_visible()
        expect(page.locator(".flow-desktop")).to_be_hidden()
    else:
        expect(page.locator(".flow-desktop")).to_be_visible()
    expect(page.locator(".flow-details")).to_be_visible()
    expect(page.locator(".notice.error")).to_have_count(0)

