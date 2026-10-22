"""Geometry, actual touch gestures and measured flow directions for Step31."""
import os
from copy import deepcopy
from pathlib import Path

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e
SAMPLE = {'timestamp': '2026-10-21T13:03:00+02:00', 'last_measurement_at': '2026-10-21T13:03:00+02:00',
          'status': {'stale_sources': [], 'controller': {'enabled': False}}, 'sources': {
              'goodwe': {'pv_w': 4030, 'house_w': 348, 'battery_charge_w': 3680,
                         'battery_discharge_w': 0, 'grid_import_w': 3, 'grid_export_w': 0, 'battery_soc': 74},
              'tng': {'heating_on': True},
              'shelly': {'heatpump_power_w': -9, 'heatpump_quality': 'negative', 'devices': {},
                         'device_status': {'fridge': {'appliance_type': 'fridge', 'quality': 'offline'}}}}}


def fixtures(page, lang='cs', sample=None, motion='off'):
    page.route('**/api/status', lambda r: r.fulfill(json={
        'ui': {'language': lang, 'animations': motion}, 'controller': {'enabled': False},
        'readers': {}, 'stale_sources': []}))
    page.route('**/api/current*', lambda r: r.fulfill(json=sample or SAMPLE))
    page.route('**/api/prediction*', lambda r: r.fulfill(json={'days': []}))
    page.route('**/api/weather*', lambda r: r.fulfill(json={}))
    page.route('**/api/prices*', lambda r: r.fulfill(json={}))


def fits(page, selector):
    result = page.locator(selector).evaluate("""el => {
      const box = el.getBoundingClientRect();
      return {width:el.clientWidth, scroll:el.scrollWidth, height:el.clientHeight,
        contentHeight:el.scrollHeight, left:box.left, right:box.right, viewport:innerWidth};
    }""")
    assert result['scroll'] <= result['width'] + 1, (selector, result)
    assert result['contentHeight'] <= result['height'] + 1, (selector, result)
    assert result['left'] >= -1 and result['right'] <= result['viewport'] + 1, (selector, result)


@pytest.mark.parametrize('width', [360, 390, 430, 1280])
@pytest.mark.parametrize('lang', ['cs', 'en'])
def test_layout_long_unavailable_text_and_zoom(page, width, lang):
    fixtures(page, lang)
    page.set_viewport_size({'width': width, 'height': 844})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('/#/overview')
    expect(page.locator('.hero-main-window--unavailable')).to_be_visible()
    for zoom in [100, 200]:
        page.add_style_tag(content=f'html {{ font-size: {zoom}% !important; }}')
        for selector in ['.today-recommendation-panel', '.hero-primary-card', '.hero-main-window', '.hero-card-footer']:
            fits(page, selector)
        for selector in ['.kpi-trend', '.recommendation-status', '.weather-details']:
            for el in page.locator(selector).all():
                result = el.evaluate('(e)=>({width:e.clientWidth,scroll:e.scrollWidth})')
                assert result['scroll'] <= result['width'] + 1, (selector, result)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.add_style_tag(content='html { font-size: 100% !important; }')
    page.goto('/#/flow')
    expect(page.locator('[data-device="heatpump"]')).to_be_visible()
    for zoom in [100, 200]:
        page.add_style_tag(content=f'html {{ font-size: {zoom}% !important; }}')
        for selector in ['#live-flow', '.flow-device-list', '.flow-device-row', '.flow-reading']:
            for el in page.locator(selector).all():
                if el.is_visible():
                    result = el.evaluate('(e)=>({width:e.clientWidth,scroll:e.scrollWidth,height:e.clientHeight,content:e.scrollHeight})')
                    assert result['scroll'] <= result['width'] + 1, (selector, result)
                    assert result['content'] <= result['height'] + 1, (selector, result)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    if width < 768:
        expect(page.locator('.flow-mobile-link--pv')).to_be_visible()
    evidence = os.environ.get('HEC_EVIDENCE_DIR')
    if evidence:
        Path(evidence).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(evidence) / f'flow-{lang}-{width}-zoom200.png'), full_page=True)
    assert not errors


@pytest.mark.parametrize('charge,discharge,imported,exported,pv', [
    (3680, 0, 3, 0, 4030), (0, 600, 800, 0, 0), (0, 0, 0, 900, 1300),
    (0, 0, 0, 0, 0), (None, None, None, None, None), (-10, 0, -20, 0, -30)])
def test_mobile_arrows_use_only_valid_measured_directions(page, charge, discharge, imported, exported, pv):
    data = deepcopy(SAMPLE)
    data['sources']['goodwe'].update(battery_charge_w=charge, battery_discharge_w=discharge,
                                     grid_import_w=imported, grid_export_w=exported, pv_w=pv)
    fixtures(page, sample=data)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto('/#/flow')
    expect(page.locator('.flow-mobile-link--battery')).to_be_visible()
    expected = {'pv': ('pv', 'house') if pv is not None and pv > 20 else ('', ''),
                'battery': ('house', 'battery') if charge is not None and charge > 20 else
                           ('battery', 'house') if discharge is not None and discharge > 20 else ('', ''),
                'grid': ('grid', 'house') if imported is not None and imported > 20 else
                        ('house', 'grid') if exported is not None and exported > 20 else ('', '')}
    for name, (source, target) in expected.items():
        link = page.locator(f'.flow-mobile-link--{name}')
        assert link.get_attribute('data-from') == source
        assert link.get_attribute('data-to') == target
        paths = link.locator(':scope > path')
        assert bool(paths.get_attribute('marker-start') or paths.get_attribute('marker-end')) == bool(source)
        if source:
            assert 2 <= float(paths.get_attribute('stroke-width')) <= 8
        assert paths.evaluate('e=>getComputedStyle(e).animationName') == 'none'


def touch_drag(page, selector, horizontal=True):
    page.locator(selector).scroll_into_view_if_needed()
    box = page.locator(selector).bounding_box()
    x = box['x'] + min(box['width'] - 20, 250)
    y = max(70, min(box['y'] + box['height'] / 2, 700))
    session = page.context.new_cdp_session(page)
    session.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y}]})
    for n in range(1, 9):
        session.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [
            {'x': x - (n * 20 if horizontal else 0), 'y': y - (0 if horizontal else n * 20)}]})
    session.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
    session.detach()


def test_real_touch_scroll_keeps_route_and_menu_still_navigates(browser):
    context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True,
                                  base_url=os.environ['HEC_BASE_URL'])
    page = context.new_page()
    fixtures(page)
    page.goto('/#/overview')
    expect(page.locator('.today-screen')).to_be_visible()
    strip = page.locator('.rhythm-left-panel')
    strip.wait_for()
    # Test the real horizontal scroller with browser-generated touch events.
    scroller = strip.locator('..')
    before = scroller.evaluate('e=>e.scrollLeft')
    touch_drag(page, '.rhythm-left-panel')
    assert page.url.endswith('#/overview')
    assert scroller.evaluate('e=>e.scrollLeft') > before
    touch_drag(page, '.hero-primary-card')
    assert page.url.endswith('#/overview')
    page.evaluate('scrollTo(0,0)')
    touch_drag(page, '.today-recommendation-panel', horizontal=False)
    assert page.evaluate('scrollY') > 0
    page.locator('#menu-toggle').click()
    page.locator('#nav a[href="#/flow"]').click()
    expect(page.locator('.flow-main-readings')).to_be_visible()
    assert page.url.endswith('#/flow')
    context.close()


@pytest.mark.parametrize('motion,reduced', [('full', False), ('reduced', False), ('off', False), ('full', True)])
def test_mobile_connector_respects_motion_preferences(page, motion, reduced):
    fixtures(page, motion=motion)
    page.emulate_media(reduced_motion='reduce' if reduced else 'no-preference')
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto('/#/flow')
    edge = page.locator('.flow-mobile-link--battery > path')
    expect(edge).to_be_visible()
    animation = edge.evaluate('el=>getComputedStyle(el).animationName')
    assert (animation != 'none') == (motion == 'full' and not reduced)


@pytest.mark.parametrize('discharging', [False, True])
def test_moving_dashes_follow_the_visible_flow_direction(page, discharging):
    data = deepcopy(SAMPLE)
    data['sources']['goodwe'].update(
        battery_charge_w=0 if discharging else 600,
        battery_discharge_w=600 if discharging else 0,
        grid_import_w=800 if discharging else 0,
        grid_export_w=0 if discharging else 800)
    fixtures(page, sample=data, motion='full')
    page.emulate_media(reduced_motion='no-preference')
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto('/#/flow')
    for name in ['pv', 'battery', 'grid']:
        edge = page.locator(f'.flow-mobile-link--{name} > path')
        expect(page.locator(f'.flow-mobile-link--{name}')).to_be_visible()
        assert float(edge.get_attribute('stroke-width')) > 0
        reverse = discharging and name in ['battery', 'grid']
        offsets = edge.evaluate("""el => {
            const animation = el.getAnimations()[0];
            animation.pause();
            animation.currentTime = 250;
            const before = parseFloat(getComputedStyle(el).strokeDashoffset);
            animation.currentTime = 500;
            return {before, after:parseFloat(getComputedStyle(el).strokeDashoffset),
                    direction:getComputedStyle(el).animationDirection};
        }""")
        assert offsets['direction'] == ('reverse' if reverse else 'normal')
        assert (offsets['after'] > offsets['before']) if reverse else (offsets['after'] < offsets['before'])
