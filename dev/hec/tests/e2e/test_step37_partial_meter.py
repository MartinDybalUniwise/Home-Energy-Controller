"""Display corrected diagnostic power without legitimising incomplete metering."""
import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_partial_meter_diagnostic_keeps_analytics_invalid(page):
    page.goto('/#/overview')
    result = page.evaluate("""async () => {
      const {heatpumpPower, heatpumpReportedPower}=await import('/js/telemetry.js?v=37');
      const sample={heatpump_power_w:1253.9,heatpump_quality:'phase',devices:{hp:{
        role:'heatpump_meter',power_w:1253.9,raw_power_w:-1253.9,l2_v:0,
        measurement_quality:'phase',power_normalization:'absolute-v1'}}};
      return {display:heatpumpReportedPower(sample),analytical:heatpumpPower(sample),
        stale:heatpumpReportedPower({...sample,heatpump_quality:'stale'}),
        offline:heatpumpReportedPower({...sample,device_status:{hp:{role:'heatpump_meter',quality:'offline'}}}),
        uncorrected:heatpumpReportedPower({heatpump_power_w:-10,heatpump_quality:'negative'}),
        missing:heatpumpReportedPower({}),raw:sample.devices.hp.raw_power_w};
    }""")
    assert result == {'display':1253.9,'analytical':None,'stale':None,'offline':None,
                      'uncorrected':None,'missing':None,'raw':-1253.9}


def test_overview_shows_absolute_reading_with_phase_warning(page):
    page.route('**/api/status',lambda route:route.fulfill(json={
        'ui':{'language':'cs'},'controller':{'enabled':False},'readers':{}}))
    page.route('**/api/current*',lambda route:route.fulfill(json={
        'sources':{'shelly':{'heatpump_power_w':1253.9,'heatpump_quality':'phase','devices':{
            'hp':{'role':'heatpump_meter','power_w':1253.9,'raw_power_w':-1253.9,
                  'l2_v':0,'measurement_quality':'phase','power_normalization':'absolute-v1'}}}}}))
    page.goto('/#/overview')
    card=page.locator('.kpi-card--heatpump')
    expect(card.locator('.kpi-value')).to_contain_text('1,25')
    expect(card.locator('.kpi-trend')).to_contain_text('Neúplné měření')
    expect(card).to_have_attribute('data-quality','invalid')
