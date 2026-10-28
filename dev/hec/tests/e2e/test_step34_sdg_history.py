"""SDG fills overview outages without overwriting live-source history."""
import pytest
from playwright.sync_api import expect
from test_step33_today import fixtures

pytestmark = pytest.mark.e2e


def test_sdg_field_priority_and_validation(page):
    fixtures(page)
    page.goto('/#/overview')
    expect(page.locator('.today-plot')).to_have_count(2, timeout=15000)
    result = page.evaluate('''async () => {
      const {mergeEnergyHistory:m}=await import('/js/history-fallback.js?v=34');
      const t='2026-10-22T12:00:00+02:00';
      return {
        mixed:m({rows:[{timestamp:t,pv_w:0,house_w:-1}]},
          {rows:[{timestamp:'2026-10-22T10:00:00Z',ppvcelkem:5200,total__w:600}]},300),
        invalid:m(null,{rows:[{timestamp:t,ppvcelkem:-1,total__w:null,load_pt:999}]},300)
      };
    }''')
    assert len(result['mixed']['rows']) == 1
    row = result['mixed']['rows'][0]
    assert row['pv_w'] == 0 and row['sources']['pv_w'] == 'goodwe'
    assert row['house_w'] == 600 and row['sources']['house_w'] == 'sdg_history'
    assert result['invalid']['rows'][0]['pv_w'] is None
    assert result['invalid']['rows'][0]['house_w'] is None


@pytest.mark.parametrize('goodwe_failed', [False, True])
def test_sdg_fills_morning_and_retains_source(page, goodwe_failed):
    fixtures(page)

    def history(route):
        if 'source=sdg_history' in route.request.url:
            route.fulfill(json={'rows':[
                {'timestamp':'2026-10-22T09:00:00+02:00','ppvcelkem':1200,'total__w':600},
                {'timestamp':'2026-10-22T13:00:00+02:00','ppvcelkem':900,'total__w':700}]})
        elif goodwe_failed:
            route.fulfill(status=503, json={'error':'offline'})
        else:
            route.fulfill(json={'rows':[
                {'timestamp':'2026-10-22T13:00:00+02:00','pv_w':0,'house_w':800}]})

    page.route('**/api/history*', history)
    page.goto('/#/overview')
    expect(page.locator('.today-plot')).to_have_count(2, timeout=15000)
    page.locator('[data-table]').click()
    table = page.locator('.today-chart-table')
    expect(table).to_contain_text('09:00')
    expect(table).to_contain_text('Archiv SDG')
    if goodwe_failed:
        expect(page.locator('#today-energy-chart [role="alert"]')).to_be_visible()
    else:
        expect(table).to_contain_text('Měření GoodWe')
        expect(table).to_contain_text('0,80')
