"""Exercise TNG history gaps, table semantics and readable mobile SVG (Step28)."""

import json

import pytest

pytestmark = pytest.mark.e2e

FIELDS = ["outside_temperature", "water_output_temperature", "boiler_temperature", "room_temperature"]
ROWS = [
    {"timestamp": "2026-10-02T15:00:00+02:00", **dict(zip(FIELDS, [-5, 30, 48, 21.7], strict=True))},
    {"timestamp": "2026-10-02T16:00:00+02:00", **dict(zip(FIELDS, [-5, 31, 49, None], strict=True))},
    {"timestamp": "2026-10-02T17:00:00+02:00", **dict(zip(FIELDS, [0, 32, 50, 0], strict=True))},
    {"timestamp": "2026-10-03T15:00:00+02:00", **dict(zip(FIELDS, [-2, 30, 48, 22], strict=True))},
]


@pytest.mark.parametrize("viewport", [(390, 844), (1280, 800)])
@pytest.mark.parametrize("range_value", ["-24h", "-7d", "-30d"])
def test_tng_history_mobile_dates_touch_gaps_and_table(page, viewport, range_value):
    from playwright.sync_api import expect

    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})

    def route_api(route):
        if route.request.url.endswith("/api/sources"):
            route.fulfill(json={"sources": ["tng"]})
        elif "/api/history?" in route.request.url:
            route.fulfill(json={"source": "tng", "fields": FIELDS, "rows": ROWS, "count": 4})
        else:
            route.continue_()

    page.route("**/api/**", route_api)
    page.goto("/#/history")
    page.locator(f'[data-range="{range_value}"]').click()
    chart = page.locator("#chart svg")
    expect(chart).to_be_visible()
    box = chart.bounding_box()
    assert box and box["height"] >= 250
    label_height = chart.locator(".axis-label").first.evaluate("el => el.getBoundingClientRect().height")
    assert label_height >= 10
    # Real sub-zero values remain visible; an impossible input never sets the axis.
    labels = chart.locator(".axis-label").all_text_contents()
    assert any("-" in label or "−" in label for label in labels)
    assert not any("1000" in label or "3000" in label for label in labels)
    # Room series is two separate SVG subpaths across the missing measurement.
    assert chart.locator(".series-line").nth(3).get_attribute("d").count("M") == 2

    # Dispatch a held touch at the second row using the actual viewBox dimensions.
    chart.evaluate("""svg => {
      const bounds = svg.getBoundingClientRect(), width = svg.viewBox.baseVal.width;
      const x = bounds.left + (52 + (width - 68) / 3) / width * bounds.width;
      svg.dispatchEvent(new TouchEvent('touchstart', {bubbles: true,
        touches: [new Touch({identifier: 1, target: svg, clientX: x, clientY: bounds.top + 50})]}));
    }""")
    tooltip = page.locator("#chart .tooltip")
    expect(tooltip).to_be_visible()
    expect(tooltip).to_contain_text("–")
    expect(tooltip.locator("strong")).to_contain_text("16:00")
    if range_value != "-24h":
        expect(tooltip.locator("strong")).to_contain_text("02")
        expect(tooltip.locator("strong")).to_contain_text("10")
    page.locator("#toggle-view").click()
    cells = page.locator("#table tbody tr").nth(1).locator("td")
    expect(cells.nth(4)).to_have_text("–")
    zero = page.locator("#table tbody tr").nth(2).locator("td").nth(4).inner_text()
    assert zero.replace(",", ".") == "0.00"
    assert not errors, json.dumps(errors)
