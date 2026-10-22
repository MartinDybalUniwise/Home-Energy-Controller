"""Real browser proof for truthful overview data, history and spacious layout."""
import os
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


@pytest.fixture(scope='session')
def browser_context_args(browser_context_args):
    return {**browser_context_args, 'timezone_id': 'Europe/Prague'}

SAMPLE = {'last_measurement_at': '2026-10-22T13:47:00+02:00',
          'status': {'stale_sources': [], 'controller': {'enabled': False}},
          'sources': {
              'goodwe': {'timestamp': '2026-10-22T13:44:40+02:00', 'pv_w': 1214, 'house_w': 3113,
                         'grid_import_w': 1864, 'grid_export_w': 0, 'battery_charge_w': 0,
                         'battery_discharge_w': 42, 'battery_soc': 10},
              'shelly': {'heatpump_power_w': -1740, 'heatpump_quality': 'negative'},
              'tng': {'heating_on': True}}}
PRICES = {'today': {'date': '2026-10-22', 'periods': [
    {'start': f'{h:02}:00', 'end': f'{h+1:02}:00', 'price_total_czk_kwh': -1 if h < 5 else 5 + h/24}
    for h in range(24)]}}
HISTORY = {'bucket_seconds': 300, 'rows': [
    {'timestamp': '2026-10-22T13:00:00+02:00', 'pv_w': 1400, 'house_w': 3100},
    {'timestamp': '2026-10-22T13:05:00+02:00', 'pv_w': 1300, 'house_w': 3000},
    {'timestamp': '2026-10-22T13:10:00+02:00', 'pv_w': None, 'house_w': None},
    {'timestamp': '2026-10-22T13:40:00+02:00', 'pv_w': 1214, 'house_w': 3113}]}


def fixtures(page, lang='cs', sample=None, history=None):
    page.clock.install(time=datetime(2026, 10, 22, 11, 47, tzinfo=UTC))
    page.route('**/api/status', lambda r: r.fulfill(json={
        'ui': {'language': lang, 'animations': 'off'}, 'controller': {'enabled': False},
        'readers': {}, 'stale_sources': []}))
    page.route('**/api/current*', lambda r: r.fulfill(json=sample or SAMPLE))
    page.route('**/api/prices*', lambda r: r.fulfill(json=PRICES))
    page.route('**/api/weather*', lambda r: r.fulfill(json={'current': {'temp_c': 11, 'wind_kmh': 12}}))
    page.route('**/api/prediction*', lambda r: r.fulfill(json={'days': [{
        'date': '2026-10-23', 'best_appliance_window': '12:15 – 14:15',
        'pv_kwh_low': 12.8, 'pv_kwh_high': 26.6, 'confidence': 'low'}]}))
    page.route('**/api/history*', lambda r: r.fulfill(json=history or HISTORY))


@pytest.mark.parametrize('width,height', [(360,844),(390,844),(430,844),(1280,800),(1440,900),(1920,1080)])
@pytest.mark.parametrize('lang', ['cs','en'])
def test_readable_today_chart_and_geometry(page, width, height, lang):
    fixtures(page,lang)
    page.set_viewport_size({'width':width,'height':height})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('/#/overview')
    expect(page.locator('.today-plot')).to_have_count(2, timeout=15000)
    expect(page.locator('.kpi-card--heatpump .kpi-value')).to_contain_text('–')
    expect(page.locator('.kpi-card--heatpump')).not_to_contain_text('1,74')
    expect(page.locator('.hero-main-window')).to_contain_text('23')
    expect(page.locator('.rhythm-production-summary strong')).to_have_text('–')
    expect(page.locator('.kpi-card--pv .kpi-trend')).to_contain_text('13:44')
    expect(page.locator('.weather-details')).to_contain_text('12')
    assert page.locator('.today-header').evaluate('e=>e.getBoundingClientRect().height')>=150
    for zoom in [100,200]:
        page.add_style_tag(content=f'html {{font-size:{zoom}% !important}}')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        for selector in ['.hero-primary-card','.recommendation-status','.kpi-card','.forecast-chart-card']:
            for e in page.locator(selector).all():
                dims=e.evaluate('e=>[e.clientWidth,e.scrollWidth,e.clientHeight,e.scrollHeight]')
                assert dims[1]<=dims[0]+1 and dims[3]<=dims[2]+1,(selector,dims,width,zoom)
    page.add_style_tag(content='html {font-size:100% !important}')
    evidence=os.environ.get('HEC_EVIDENCE_DIR')
    if evidence:
        Path(evidence).mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(Path(evidence)/f'today-{lang}-{width}.png'),full_page=True)
    assert not errors


def test_chart_units_gaps_table_ranges_and_keyboard(page):
    fixtures(page)
    requests=[]
    page.on('request',lambda r:requests.append(r.url) if '/api/history?' in r.url else None)
    page.goto('/#/overview')
    expect(page.locator('path[data-series="pv"]')).to_have_count(1, timeout=15000)
    path=page.locator('path[data-series="pv"]').get_attribute('d')
    assert path.count('M')==2 and path.count('L')==1
    expect(page.locator('.today-axis-unit').nth(0)).to_have_text('kW')
    expect(page.locator('.today-axis-unit').nth(1)).to_have_text('Kč/kWh')
    page.locator('[data-table]').click()
    expect(page.locator('.today-chart-table')).to_be_visible()
    expect(page.locator('.today-chart-table')).to_contain_text('1,21')
    expect(page.locator('.today-chart-table')).to_contain_text('Měření GoodWe')
    expect(page.locator('.today-chart-table')).not_to_contain_text('W/m²')
    page.locator('.today-chart-panels').focus()
    page.keyboard.press('ArrowRight')
    expect(page.locator('.today-chart-tooltip')).to_contain_text('kW')
    for days in [2,7,1]:
        page.locator(f'[data-days="{days}"]').click()
        expect(page.locator(f'[data-days="{days}"]')).to_have_attribute('aria-pressed','true')
    # Returning to Today reuses its minute cache instead of rereading the day.
    assert len(requests)==3
    assert all('fields=pv_w%2Chouse_w' in r for r in requests)


def test_shared_snapshot_and_prague_dst_dates(page):
    fixtures(page)
    page.goto('/#/overview')
    expect(page.locator('.today-plot')).to_have_count(2, timeout=15000)
    result=page.evaluate('''async sample => {
      const {energySnapshot,heatpumpPower}=await import('/js/telemetry.js');
      const {chartRange,siteDate}=await import('/js/today-chart.js');
      const {bestAdvice}=await import('/js/advisor.js?v=33');
      const a=chartRange(1,new Date('2026-10-25T12:00:00Z'));
      const b=chartRange(1,new Date('2026-03-29T12:00:00Z'));
      return {snapshot:energySnapshot(sample), invalid:heatpumpPower(sample.sources.shelly),
        hoursFall:(a.to-a.from)/3600000,hoursSpring:(b.to-b.from)/3600000,
        date:siteDate(new Date('2026-10-22T23:00:00Z')),
        advice:bestAdvice({days:[{date:'2026-10-22',best_appliance_window:'06:15 – 08:45'},
          {date:'2026-10-23',best_appliance_window:'12:00 – 14:00'}]}, {},new Date('2026-10-22T11:47:00Z'))};
    }''',SAMPLE)
    assert result['snapshot']['house_w']==3113
    assert result['invalid'] is None
    assert result['hoursFall']==25 and result['hoursSpring']==23
    assert result['date']=='2026-10-23'
    assert result['advice']['day']['date']=='2026-10-23'
    page.goto('/#/flow')
    expect(page.locator('.main-node--house')).to_contain_text('3,11')


def test_prague_labels_in_an_actual_utc_browser(browser):
    context=browser.new_context(base_url=os.environ['HEC_BASE_URL'],timezone_id='UTC')
    page=context.new_page()
    fixtures(page)
    page.goto('/#/overview')
    expect(page.locator('.today-plot')).to_have_count(2, timeout=15000)
    expect(page.locator('.greeting-date')).to_contain_text('13:47')
    expect(page.locator('.kpi-card--pv .kpi-trend')).to_contain_text('13:44')
    page.locator('[data-table]').click()
    expect(page.locator('.today-chart-table')).to_contain_text('13:00')
    assert page.evaluate('''async () => {
      const {siteDateTime}=await import('/js/today-chart.js');
      return siteDateTime('2026-10-22T23:30:00Z');
    }''')=='23. 10. 01:30'
    context.close()


def test_missing_bucket_is_a_gap_even_without_a_null_record(page):
    history={'bucket_seconds':300,'rows':[
        {'timestamp':'2026-10-22T13:00:00+02:00','pv_w':1000,'house_w':2000},
        {'timestamp':'2026-10-22T13:10:00+02:00','pv_w':1200,'house_w':2200}]}
    fixtures(page,history=history)
    page.goto('/#/overview')
    # Two isolated observations are circles; an M-only SVG path has no stroke.
    expect(page.locator('path[data-series="pv"]')).to_have_count(1, timeout=15000)
    path=page.locator('path[data-series="pv"]').get_attribute('d')
    assert path.count('M')==2 and 'L' not in path


def test_repeated_or_nonexistent_price_hours_are_not_guessed(page):
    fixtures(page)
    page.goto('/#/overview')
    expect(page.locator('.today-plot')).to_have_count(2, timeout=15000)
    result=page.evaluate('''async () => {
      const {chartRows,chartRange,uniqueSiteMoment}=await import('/js/today-chart.js');
      const now=new Date('2026-10-25T12:00:00Z');
      const prices={today:{date:'2026-10-25',periods:[
        {start:'02:00',end:'02:15',price_total_czk_kwh:2},
        {start:'02:00',end:'02:15',price_total_czk_kwh:4},
        {start:'03:00',end:'03:15',price_total_czk_kwh:6}]}};
      return {rows:chartRows({},prices,chartRange(1,now),now),
        repeated:uniqueSiteMoment('2026-10-25','02:00'),
        nonexistent:uniqueSiteMoment('2026-03-29','02:00')};
    }''')
    assert result['repeated'] is None and result['nonexistent'] is None
    assert len(result['rows'])==1 and result['rows'][0]['price']==6


@pytest.mark.parametrize('change', ['stale','negative','conflict','zero'])
def test_invalid_and_zero_values_are_consistent(page,change):
    sample=deepcopy(SAMPLE)
    goodwe=sample['sources']['goodwe']
    if change=='stale':
        sample['status']['stale_sources']=['goodwe']
    elif change=='negative':
        goodwe.update(pv_w=-1,house_w=-20)
    elif change=='conflict':
        goodwe.update(grid_export_w=200,battery_charge_w=200)
    else:
        goodwe.update(pv_w=0,house_w=0)
    fixtures(page,sample=sample)
    page.goto('/#/overview')
    expect(page.locator('.today-plot')).to_have_count(2, timeout=15000)
    if change=='conflict':
        expect(page.locator('.kpi-card--grid .kpi-value')).to_contain_text('–')
    else:
        expected='0' if change=='zero' else '–'
        expect(page.locator('.kpi-card--pv .kpi-value')).to_contain_text(expected)
        expect(page.locator('.kpi-card--house .kpi-value')).to_contain_text(expected)


def test_history_failure_keeps_prices_and_can_retry(page):
    fixtures(page)
    page.route('**/api/history*',lambda r:r.fulfill(status=503,json={'error':'test'}))
    page.goto('/#/overview')
    expect(page.locator('#today-energy-chart [role="alert"]')).to_be_visible()
    expect(page.locator('path[data-series="price"]')).to_be_visible()
    page.unroute('**/api/history*')
    page.route('**/api/history*',lambda r:r.fulfill(json=HISTORY))
    page.locator('[data-days="1"]').click()
    expect(page.locator('#today-energy-chart [role="alert"]')).to_have_count(0)
