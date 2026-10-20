"""Real-browser regressions for the owner's midnight flow and mobile readability."""

import json
import os
from copy import deepcopy
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e


@pytest.fixture(autouse=True)
def czech_ui(page):
    """Keep diagnostic text assertions independent of other settings tests."""
    def status(route):
        response = route.fetch()
        payload = response.json()
        payload['ui'] = {**payload.get('ui', {}), 'language': 'cs', 'animations': 'off'}
        route.fulfill(response=response, json=payload)

    page.route('**/api/status', status)

SNAPSHOT = {
    'timestamp': '2026-10-21T00:10:00+02:00', 'last_measurement_at': '2026-10-21T00:10:00+02:00',
    'status': {'controller': {'enabled': False, 'safe_mode': True}, 'stale_sources': []},
    'sources': {
        'goodwe': {'pv_w': 0, 'house_w': 514, 'grid_import_w': 657, 'grid_export_w': 0,
                   'battery_soc': 9, 'battery_charge_w': 143, 'battery_discharge_w': 0,
                   'on_grid_soc_limit_pct': 10, 'operation_mode': 'GENERAL'},
        'tng': {'heating_on': True, 'boiler_temperature': 51.5},
        'shelly': {'heatpump_power_w': -8, 'heatpump_quality': 'negative',
                   'devices': {'hp': {'role': 'heatpump_meter', 'power_w': -8, 'l2_v': 0}},
                   'device_status': {'fridge': {'appliance_type': 'fridge', 'quality': 'offline'}}},
    },
}


def intercept(page, snapshot):
    page.route('**/api/current*', lambda route: route.fulfill(json=snapshot))


@pytest.mark.parametrize('width', [360, 390, 430, 1280])
def test_midnight_flow_readable_and_truthful(page, width):
    from playwright.sync_api import expect

    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_viewport_size({'width': width, 'height': 844})
    intercept(page, SNAPSHOT)
    page.goto('/#/flow')
    heatpump = page.locator('[data-device="heatpump"]')
    expect(heatpump).to_contain_text('-8')
    expect(heatpump).to_contain_text('Chyba měření')
    expect(page.locator('[data-device="fridge"]')).to_contain_text('Zařízení nedostupné')
    expect(page.locator('[data-device="other_appliances"]')).to_contain_text('neúplné měření')
    expect(page.locator('.story-flow-summary')).to_contain_text('Topení povoleno v TNG')
    expect(page.locator('.story-flow-summary')).to_contain_text('Možné udržovací')
    expect(page.locator('.story-flow-summary')).to_contain_text('10 %')
    expect(page.locator('#view')).not_to_contain_text('Topení je aktivní')
    expect(page.locator('#view')).not_to_contain_text('200 W')
    expect(page.locator('#view')).not_to_contain_text('150 W')
    assert heatpump.locator('dt').evaluate('e => parseFloat(getComputedStyle(e).fontSize)') >= 16
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    if width < 768:
        expect(page.locator('.flow-main-readings')).to_be_visible()
        expect(page.locator('.flow-desktop')).to_be_hidden()
        expect(page.locator('.flow-reading--pv strong')).to_have_text('0 W')
        expect(page.locator('.flow-reading--battery strong')).to_have_text('143 W')
    else:
        expect(page.locator('.flow-desktop')).to_be_visible()
    evidence = os.environ.get('HEC_EVIDENCE_DIR')
    if evidence:
        Path(evidence).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(evidence) / f'flow-{width}.png'), full_page=True)
    # Text zoom must reflow instead of clipping or requiring horizontal scrolling.
    page.add_style_tag(content='html { font-size: 200% !important; }')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    assert not errors


@pytest.mark.parametrize('watts,missing', [(0, False), (0, True)])
def test_today_zero_and_unknown_never_become_demo_values(page, watts, missing):
    from playwright.sync_api import expect

    data = deepcopy(SNAPSHOT)
    data['sources']['goodwe'] = {} if missing else {
        'pv_w': watts, 'house_w': 0, 'grid_import_w': 0, 'grid_export_w': 0,
        'battery_soc': 0, 'battery_charge_w': 0, 'battery_discharge_w': 0}
    intercept(page, data)
    page.route('**/api/prediction*', lambda route: route.fulfill(json={'days': []}))
    page.route('**/api/weather*', lambda route: route.fulfill(json={}))
    page.route('**/api/prices*', lambda route: route.fulfill(json={}))
    page.goto('/#/overview')
    expect(page.locator('.today-screen')).to_be_visible()
    expect(page.locator('.kpi-card--pv .kpi-value')).to_contain_text('–' if missing else '0')
    expect(page.locator('.kpi-card--battery .kpi-value')).to_contain_text('–' if missing else '0')
    body = page.locator('#view')
    for fake in ('1,86', '1,1 kW', '18,4 Kč', '52 – 108', '11:40 – 14:30'):
        expect(body).not_to_contain_text(fake)
    expect(body.locator('.multi-curve-svg')).to_have_count(0)
    catalog = json.loads((Path(__file__).parents[2] / 'locales/cs.json').read_text(encoding='utf-8'))
    expect(page.locator('.kpi-card--grid .kpi-trend')).to_have_text(catalog['flow']['grid_unknown' if missing else 'grid_balanced'])


def test_stale_source_does_not_appear_as_live_measurement(page):
    from playwright.sync_api import expect

    data = deepcopy(SNAPSHOT)
    data['status']['stale_sources'] = ['goodwe', 'shelly']
    intercept(page, data)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto('/#/flow')
    expect(page.locator('.flow-reading--pv strong')).to_contain_text('–')
    expect(page.locator('[data-device="heatpump"]')).to_contain_text('Zastaralé měření')


def test_reader_error_invalidates_even_recent_cached_power(page):
    from playwright.sync_api import expect

    data = deepcopy(SNAPSHOT)
    data['sources']['shelly']['heatpump_power_w'] = 1500
    data['sources']['shelly']['heatpump_quality'] = 'valid'
    data['status']['readers'] = {'shelly': {'state': 'error', 'last_error': 'timeout', 'enabled': True}}
    intercept(page, data)
    page.goto('/#/flow')
    row = page.locator('[data-device="heatpump"]')
    expect(row).to_contain_text('Zařízení nedostupné')
    expect(row.locator('strong')).to_have_text('–')


def test_forecast_still_renders_after_today_changes(page):
    from playwright.sync_api import expect

    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('**/api/prediction*', lambda route: route.fulfill(json={
        'generated_at': '2026-10-21T00:10:00+02:00', 'days': [
            {'date': '2026-10-21', 'confidence': 'low', 'pv_kwh_low': 0, 'pv_kwh_high': 0}]}))
    page.goto('/#/prediction')
    expect(page.locator('#forecast-grid')).to_be_visible()
    expect(page.locator('.forecast-day-card')).to_have_count(1)
    assert not errors
