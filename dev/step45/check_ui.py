"""Read-only production UI checks with installed Edge; screenshots outside Git."""
import json
import sys
from pathlib import Path

sys.path.insert(0, 'C:/TepelneCerpadlo/hec-ui-test-deps')
from playwright.sync_api import sync_playwright


def main():
    evidence = Path('C:/TepelneCerpadlo/hec-monitoring-evidence/battery-plan-ui-20261031')
    evidence.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
                                     headless=True)
        for width in (390, 1440):
            context = browser.new_context(viewport={'width': width, 'height': 1000}, timezone_id='Europe/Prague')
            page = context.new_page()
            errors, writes = [], []
            page.on('pageerror', lambda error, errors=errors: errors.append(str(error)))
            page.on('request', lambda req, writes=writes: writes.append(req.url) if '/api/' in req.url
                    and req.method not in ('GET', 'HEAD', 'OPTIONS') else None)
            page.goto('http://127.0.0.1:8080/#/control-plan')
            page.locator('.battery-plan').filter(has_text='12:30–15:30').wait_for(timeout=45000)
            body = page.locator('.battery-plan').inner_text()
            assert '12:30–15:30' in body, body
            assert '04:00' not in body, body
            assert '60 %' in body and '20 %' in body, body
            assert 'battery_plan.' not in body, body
            assert page.locator('.battery-plan input, .battery-plan button, .battery-plan form').count() == 0
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            page.locator('.battery-plan').screenshot(path=str(evidence / f'battery-plan-{width}.png'))
            page.screenshot(path=str(evidence / f'control-plan-{width}.png'), full_page=True)
            page.goto('http://127.0.0.1:8080/#/overview')
            page.locator('.timeline-battery-block').wait_for(timeout=45000)
            assert page.locator('.timeline-battery-block').count() == 1
            assert '12:30' in page.locator('.timeline-battery-block').get_attribute('aria-label')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            page.locator('#today-energy-chart').screenshot(path=str(evidence / f'overview-plan-{width}.png'))
            page.goto('http://127.0.0.1:8080/#/settings')
            page.locator('[data-path="controller.optimization.goodwe_control.economic.charge_power_pct"]').wait_for(state='attached', timeout=30000)
            assert page.locator('[data-path="controller.optimization.goodwe_control.charge_power_pct"]').count() == 0
            assert page.locator('[data-path="controller.optimization.goodwe_control.charge_stop_soc_pct"]').count() == 0
            assert page.locator('[data-path="controller.optimization.goodwe_control.enabled"]').count() == 1
            assert not errors, errors
            assert not writes, writes
            results.append({'width': width, 'errors': errors, 'write_requests': writes,
                            'battery_plan': body})
            context.close()
        browser.close()
    (evidence / 'ui-check.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps([{'width': r['width'], 'errors': r['errors'], 'write_requests': r['write_requests']}
                      for r in results]))


if __name__ == '__main__':
    main()
