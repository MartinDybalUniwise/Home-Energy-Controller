"""Focused Step 32 browser evidence for the GoodWe History chart."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page

pytestmark = pytest.mark.e2e

FIELDS = [
    "house_w", "grid_import_w", "grid_export_w", "battery_soc", "pv_w",
    "battery_temp_c", "battery_v", "battery_a", "e_day_kwh",
    "grid_frequency_hz", "vendor_signal",
]
ROWS = [
    {"timestamp": "2026-09-20T10:00:00+02:00", "house_w": 1000, "grid_import_w": 500,
     "grid_export_w": 0, "battery_soc": 20, "pv_w": 500, "battery_temp_c": 20,
     "battery_v": 400, "battery_a": 1, "e_day_kwh": 5, "grid_frequency_hz": 50,
     "vendor_signal": 10},
    {"timestamp": "2026-09-20T10:15:00+02:00", "house_w": 2000, "grid_import_w": 0,
     "grid_export_w": 250, "battery_soc": 40, "pv_w": 1500, "battery_temp_c": None,
     "battery_v": 400, "battery_a": 2, "e_day_kwh": 6, "grid_frequency_hz": 50,
     "vendor_signal": 20},
    {"timestamp": "2026-09-20T10:30:00+02:00", "house_w": 3000, "grid_import_w": 0,
     "grid_export_w": 750, "battery_soc": 60, "pv_w": 2500, "battery_temp_c": 30,
     "battery_v": 400, "battery_a": 3, "e_day_kwh": 7, "grid_frequency_hz": 50,
     "vendor_signal": 30},
    {"timestamp": "2026-09-20T10:45:00+02:00", "house_w": 4000, "grid_import_w": 0,
     "grid_export_w": 1250, "battery_soc": 80, "pv_w": 3500, "battery_temp_c": 40,
     "battery_v": 400, "battery_a": 4, "e_day_kwh": 8, "grid_frequency_hz": 50,
     "vendor_signal": 40},
]
MULTI_DAY_TIMES = [
    (17, 7), (17, 8), (17, 13), (17, 19),
    *((day, hour) for day in (18, 19, 20) for hour in (0, 7, 13, 19)),
]
MULTI_DAY_ROWS = [
    {**ROWS[index % len(ROWS)], "timestamp": f"2026-09-{day:02d}T{hour:02d}:17:00+02:00"}
    for index, (day, hour) in enumerate(MULTI_DAY_TIMES)
]


def install_goodwe_routes(page: Page, language: str = "cs") -> None:
    def route_api(route):
        url = route.request.url
        if url.endswith("/api/status") or "/api/status?" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps({
                "site_name": "HEC Test", "ui": {"language": language, "theme": "dark", "animations": "off"},
                "controller": {"enabled": False, "safe_mode": False}, "stale_sources": [],
            }))
            return
        if url.endswith("/api/sources"):
            route.fulfill(status=200, content_type="application/json", body='{"sources":["goodwe"]}')
            return
        if "/api/history?" in url:
            query = parse_qs(urlparse(url).query)
            rows = MULTI_DAY_ROWS if query.get("from", [""])[0] in {"-7d", "-30d"} else ROWS
            payload = {
                "source": "goodwe", "from": rows[0]["timestamp"], "to": rows[-1]["timestamp"],
                "bucket_seconds": 0, "fields": FIELDS, "count": len(rows), "raw_count": len(rows),
                "rows": rows,
            }
            route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))
            return
        route.continue_()

    page.route("**/api/**", route_api)


def checkbox(page: Page, field: str):
    return page.locator(f'[data-goodwe-field="{field}"]')


@pytest.mark.parametrize("viewport,language", [((1920, 1080), "cs"), ((390, 844), "en")])
def test_goodwe_history_defaults_complete_legend_axes_and_layout(
        page: Page, viewport: tuple[int, int], language: str):
    from playwright.sync_api import expect

    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    install_goodwe_routes(page, language)
    page.goto("/#/history")

    expect(page.locator(".goodwe-history-chart")).to_have_count(1)
    expect(page.locator('[data-chart="battery-soc"]')).to_have_count(0)
    expect(page.locator(".goodwe-metric")).to_have_count(len(FIELDS))
    assert page.locator("#chart").evaluate(
        "chart => Boolean(chart.compareDocumentPosition(document.querySelector('#goodwe-history-legend')) "
        "& Node.DOCUMENT_POSITION_FOLLOWING)"
    )
    assert len(set(page.locator(".goodwe-metric").evaluate_all("nodes => nodes.map(node => node.dataset.field)"))) == len(FIELDS)
    defaults = ("house_w", "grid_import_w", "grid_export_w", "battery_soc", "pv_w")
    assert page.locator(".goodwe-metric").evaluate_all(
        "nodes => nodes.slice(0, 5).map(node => node.dataset.field)") == list(defaults)
    for field in defaults:
        expect(checkbox(page, field)).to_be_checked()
        expect(page.locator(f'.series-line[data-field="{field}"]')).to_have_count(1)
    expect(page.locator('.series-line[data-field="pv_w"]')).to_have_attribute("stroke", "var(--series-pv)")
    for field in set(FIELDS) - set(defaults):
        expect(checkbox(page, field)).not_to_be_checked()

    expect(page.locator('[data-axis-unit="left"]')).to_have_text("kW")
    expect(page.locator('[data-axis-unit="right"]')).to_have_text("%")
    expect(page.locator('input[name="goodwe-history-mode"][value="actual"]')).to_be_checked()
    expect(page.locator(".goodwe-mode-note")).to_be_visible()
    legend = page.locator(".goodwe-metric-list")
    legend_box = legend.bounding_box()
    assert legend_box is not None
    assert legend_box["height"] <= (178 if viewport[0] == 390 else 186)
    assert page.locator(".goodwe-metric-check").evaluate_all(
        "nodes => nodes.every(node => node.getBoundingClientRect().height >= 44)")
    assert page.locator(".metric-info-button").evaluate_all(
        "nodes => nodes.every(node => node.getBoundingClientRect().height >= 44 && node.getBoundingClientRect().width >= 44)")
    if viewport[0] == 390:
        assert legend.evaluate("node => node.scrollHeight > node.clientHeight")
    overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert overflow <= 1
    assert not errors


def test_goodwe_history_long_ranges_use_unique_local_day_and_quarter_markers(page: Page):
    from playwright.sync_api import expect

    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    install_goodwe_routes(page)
    page.goto("/#/history")

    expect(page.locator(".x-time-label")).to_have_count(4)
    for selected_range in ("-7d", "-30d"):
        page.locator(f'[data-range="{selected_range}"]').click()
        expect(page.locator(".goodwe-history-chart")).to_have_attribute("data-range", selected_range)
        expect(page.locator(".x-marker--major")).to_have_count(4)
        expect(page.locator(".x-day-label")).to_have_count(4)
        expect(page.locator(".x-marker--minor")).to_have_count(12)
        marker_indexes = page.locator(".x-marker").evaluate_all(
            "nodes => nodes.map(node => node.dataset.sampleIndex)")
        assert len(marker_indexes) == len(set(marker_indexes))
        assert page.locator(".x-marker--major").evaluate_all(
            "nodes => nodes.map(node => node.dataset.day)") == page.locator(".x-day-label").evaluate_all(
                "nodes => nodes.map(node => node.dataset.day)")
        assert set(page.locator(".x-marker--minor").evaluate_all(
            "nodes => nodes.map(node => node.dataset.localTime)")) == {"06:00", "12:00", "18:00"}
        for complete_day in ("2026-09-18", "2026-09-19", "2026-09-20"):
            expect(page.locator(f'.x-marker--minor[data-day="{complete_day}"]')).to_have_count(3)
        assert page.locator(".x-marker--major").evaluate_all(
            "nodes => nodes.every(node => node.getAttribute('y1') === '22' && node.getAttribute('y2') === '292')")
        assert page.locator(".x-marker--minor").evaluate_all(
            "nodes => nodes.every(node => Number(node.getAttribute('y1')) > 250 && node.getAttribute('y2') === '292')")
        assert page.locator(".x-marker--major").first.evaluate(
            "major => parseFloat(getComputedStyle(major).strokeWidth)") > page.locator(
                ".x-marker--minor").first.evaluate(
                    "minor => parseFloat(getComputedStyle(minor).strokeWidth)")
        assert page.locator(".x-time-label").count() == 0

    page.locator('[data-range="today"]').click()
    expect(page.locator(".goodwe-history-chart")).to_have_attribute("data-range", "today")
    expect(page.locator(".x-time-label")).to_have_count(4)
    expect(page.locator(".x-marker")).to_have_count(0)

    page.locator('[data-range="-24h"]').click()
    expect(page.locator(".goodwe-history-chart")).to_have_attribute("data-range", "-24h")
    expect(page.locator(".x-time-label")).to_have_count(4)
    expect(page.locator(".x-marker")).to_have_count(0)

    assert not errors



@pytest.mark.parametrize("viewport", [(1280, 800), (390, 844)])
def test_goodwe_history_guards_trends_popups_tooltip_table_and_state(
        page: Page, viewport: tuple[int, int]):
    from playwright.sync_api import expect

    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    install_goodwe_routes(page)
    page.goto("/#/history")

    temperature = checkbox(page, "battery_temp_c")
    temperature.click()
    expect(temperature).not_to_be_checked()
    expect(page.locator(".goodwe-history-message")).not_to_be_empty()

    info = page.locator('[data-field="house_w"] .metric-info-button')
    house_checkbox = checkbox(page, "house_w")
    info.hover()
    expect(page.locator('[data-field="house_w"] [role="tooltip"]')).to_be_visible()
    info.focus()
    info.click()
    expect(house_checkbox).to_be_checked()
    page.keyboard.press("Escape")
    expect(page.locator('[data-field="house_w"] [role="tooltip"]')).to_be_hidden()
    unknown_info = page.locator('[data-field="vendor_signal"] .metric-info-button')
    unknown_info.click()
    expect(page.locator('[data-field="vendor_signal"] [role="tooltip"]')).to_contain_text("vendor_signal")
    page.locator(".goodwe-mode-note").click()
    expect(page.locator('[data-field="vendor_signal"] [role="tooltip"]')).to_be_hidden()
    unknown_info.click()
    page.locator("#toggle-view").click()
    expect(page.locator('[data-field="vendor_signal"] [role="tooltip"]')).to_be_hidden()
    page.locator("#toggle-view").click()

    trend = page.locator('input[name="goodwe-history-mode"][value="trend"]')
    trend.check()
    for field in ("battery_temp_c", "battery_v", "battery_a", "pv_w"):
        checkbox(page, field).check()
    expect(page.locator(".goodwe-history-chart")).to_have_attribute("data-mode", "trend")
    expect(page.locator('[data-axis-unit="left"]')).to_have_text("Relativní trend 0–100")
    assert page.locator('[data-field="house_w"].series-line').get_attribute("data-values") == "0.0000,33.3333,66.6667,100.0000"
    assert page.locator('[data-field="battery_v"].series-line').get_attribute("data-values") == "50.0000,50.0000,50.0000,50.0000"
    temperature_path = page.locator('[data-field="battery_temp_c"].series-line')
    assert temperature_path.get_attribute("data-values") == "0.0000,gap,50.0000,100.0000"
    assert (temperature_path.get_attribute("d") or "").count("M") == 2

    page.locator(".goodwe-history-chart").hover(position={"x": 200, "y": 60})
    expect(page.locator('.tooltip-row[data-field="battery_v"]')).to_contain_text("400,00 V")
    expect(page.locator('.tooltip-row[data-field="battery_temp_c"]')).to_contain_text("°C")

    actual = page.locator('input[name="goodwe-history-mode"][value="actual"]')
    actual.click()
    expect(trend).to_be_checked()
    for field in ("battery_temp_c", "battery_v", "battery_a", "pv_w"):
        expect(checkbox(page, field)).to_be_checked()
    expect(page.locator(".goodwe-history-message")).not_to_be_empty()

    page.locator("#toggle-view").click()
    expect(page.locator("#table")).to_contain_text("[V]")
    expect(page.locator("#table")).to_contain_text("[°C]")
    expect(page.locator("#table")).to_contain_text("400,00")
    page.locator("#toggle-view").click()

    for field in ("battery_temp_c", "battery_v", "battery_a"):
        checkbox(page, field).uncheck()
    actual.check()
    expect(actual).to_be_checked()
    expect(checkbox(page, "pv_w")).to_be_checked()
    checkbox(page, "pv_w").focus()
    checkbox(page, "pv_w").press("Space")
    expect(checkbox(page, "pv_w")).not_to_be_checked()
    checkbox(page, "pv_w").press("Space")
    page.locator('[data-range="-7d"]').click()
    expect(checkbox(page, "pv_w")).to_be_checked()
    expect(page.locator('[data-axis-unit="left"]')).to_have_text("kW")
    expect(page.locator('[data-axis-unit="right"]')).to_have_text("%")

    overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert overflow <= 1
    assert not errors
