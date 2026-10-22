"""Actual browser: AC counters cannot leak through GoodWe or SDG fallbacks."""
import os
from pathlib import Path

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e
LEGACY = {'e_day_kwh': 0, 'e_load_day_kwh': 7.9, 'e_export_day_kwh': 7.9, 'e_import_day_kwh': 0}
SEMANTICS = 'ac-grid-separated-v1'


@pytest.mark.parametrize('lang', ['cs', 'en'])
@pytest.mark.parametrize('case', ['goodwe-legacy', 'goodwe-corrected', 'sdg-raw', 'sdg-legacy', 'summary', 'verified-zero'])
def test_grid_daily_energy_never_uses_ac_counter(page, lang, case):
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
    else:
        sources['goodwe'] = {**LEGACY, 'e_export_day_kwh': 0, 'e_import_day_kwh': 0,
                             'energy_counter_semantics': SEMANTICS}
    page.route('**/api/status', lambda r: r.fulfill(json={'ui': {'language': lang}, 'readers': {}, 'controller': {}}))
    page.route('**/api/current*', lambda r: r.fulfill(json={'sources': sources}))
    page.route('**/api/decisions*', lambda r: r.fulfill(json={'decisions': []}))
    page.route('**/api/prices*', lambda r: r.fulfill(json={}))
    page.route('**/api/prediction*', lambda r: r.fulfill(json={'days': []}))
    page.route('**/api/appliances*', lambda r: r.fulfill(json={'cycles': []}))
    page.route('**/api/summaries*', lambda r: r.fulfill(json={'days': summary}))
    page.set_viewport_size({'width': 390, 'height': 844})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('/#/control-plan')
    panel = page.locator('.control-plan-daily-energy')
    expect(panel).to_be_visible()
    for tone in ['export', 'import']:
        cell = panel.locator(f'[data-tone="{tone}"] strong')
        if case in ['summary', 'verified-zero']:
            number = ('0.04' if tone == 'export' else '0.07') if case == 'summary' else '0.00'
            expect(cell).to_contain_text(number.replace('.', ',') if lang == 'cs' else number)
        else:
            expect(cell).not_to_contain_text('kWh')
            expect(cell).not_to_contain_text('7,9' if lang == 'cs' else '7.9')
    if case in ['sdg-raw', 'sdg-legacy']:
        expect(panel.locator('header')).to_contain_text('SDG')
    if case.startswith('goodwe'):
        expect(panel.locator('header')).to_contain_text('GoodWe')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    assert not errors
    if os.environ.get('HEC_EVIDENCE_DIR'):
        panel.screenshot(path=str(Path(os.environ['HEC_EVIDENCE_DIR']) / f'{case}-{lang}.png'))
