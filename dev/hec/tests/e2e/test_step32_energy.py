"""Current read-only controller page must never present daily counters as power.

Daily grid-energy projection is covered in test_step32_grid_energy.py. Step42
replaced the old daily-energy panel with instantaneous flows and one common plan.
"""
import os
from pathlib import Path

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e
LEGACY = {'e_day_kwh': 0, 'e_load_day_kwh': 7.9, 'e_export_day_kwh': 7.9, 'e_import_day_kwh': 0}
SEMANTICS = 'ac-grid-separated-v1'


@pytest.mark.parametrize('lang', ['cs', 'en'])
@pytest.mark.parametrize('case', ['goodwe-legacy', 'goodwe-corrected', 'sdg-raw', 'sdg-legacy', 'summary', 'verified-zero', 'measured-power'])
def test_live_grid_power_never_uses_daily_ac_or_summary_counters(page, lang, case):
    sources = {}
    summary = []
    if case == 'goodwe-legacy':
        sources['goodwe'] = LEGACY
    elif case == 'goodwe-corrected':
        sources['goodwe'] = {**LEGACY, 'e_export_day_kwh': None, 'e_import_day_kwh': None,
                             'inverter_ac_export_day_kwh': 7.9, 'energy_counter_semantics': SEMANTICS}
    elif case == 'sdg-raw':
        sources['sdg_history'] = {'values': {'e_day': 0, 'e_load_day': 7.9, 'e_day_exp': 7.9, 'e_day_imp': 0}}
    elif case == 'sdg-legacy':
        sources['sdg_history'] = {'values': LEGACY}
    elif case == 'summary':
        summary = [{'pv_kwh': 0, 'house_kwh': 7.9, 'grid_import_kwh': 0.07, 'grid_export_kwh': 0.04}]
    elif case == 'verified-zero':
        sources['goodwe'] = {**LEGACY, 'e_export_day_kwh': 0, 'e_import_day_kwh': 0,
                             'energy_counter_semantics': SEMANTICS,
                             'grid_import_w': 0, 'grid_export_w': 0}
    else:
        sources['goodwe'] = {**LEGACY, 'grid_import_w': 520, 'grid_export_w': 0}
    page.route('**/api/status', lambda r: r.fulfill(json={'ui': {'language': lang}, 'readers': {}, 'controller': {}}))
    page.route('**/api/current*', lambda r: r.fulfill(json={'sources': sources}))
    page.route('**/api/decisions*', lambda r: r.fulfill(json={'decisions': []}))
    page.route('**/api/prices*', lambda r: r.fulfill(json={}))
    page.route('**/api/prediction*', lambda r: r.fulfill(json={'days': []}))
    page.route('**/api/appliances*', lambda r: r.fulfill(json={'cycles': []}))
    page.route('**/api/summaries*', lambda r: r.fulfill(json={'days': summary}))
    page.set_viewport_size({'width': 390, 'height': 844})
    errors = []
    writes = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: writes.append(request.url)
            if request.method not in ('GET', 'HEAD') else None)
    page.goto('/#/control-plan')
    panel = page.locator('[data-process="energy"]')
    expect(panel).to_be_visible()
    # Import/export are the third/fourth metrics; neither an AC register nor a
    # daily summary can supply them. A genuine measured zero remains visible.
    for index in (2, 3):
        cell = panel.locator('dd').nth(index)
        if case in ['verified-zero', 'measured-power']:
            number = '0.52' if case == 'measured-power' and index == 2 else '0.00'
            expect(cell).to_have_text((number.replace('.', ',') if lang == 'cs' else number) + ' kW')
        else:
            expect(cell).to_have_text('—')
    expect(panel).not_to_contain_text('kWh')
    expect(panel).not_to_contain_text('7,9' if lang == 'cs' else '7.9')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    assert not errors
    assert not writes
    if os.environ.get('HEC_EVIDENCE_DIR'):
        panel.screenshot(path=str(Path(os.environ['HEC_EVIDENCE_DIR']) / f'{case}-{lang}.png'))
