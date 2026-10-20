import json

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize('viewport', [(1920, 1080), (390, 844)])
def test_version_and_changelog_in_prague_time(page, viewport):
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_viewport_size({'width': viewport[0], 'height': viewport[1]})
    # A known release fixture tests Prague formatting regardless of browser zone.
    payload = {'current': '0.1.1', 'releases': [
        {'version': '0.1.0', 'released_at': '2026-01-01T12:35:00Z', 'changes': ['release.versioning']},
        {'version': '0.1.1', 'released_at': '2026-10-20T12:35:00Z', 'changes': ['release.history']}]}
    page.route('**/api/releases', lambda route: route.fulfill(content_type='application/json', body=json.dumps(payload)))
    page.goto('/')
    if viewport[0] <= 1023:
        page.locator('#menu-toggle').click()
    button = page.locator('#app-version')
    expect(button).to_have_text('v0.1.1')
    button.click()
    dialog = page.locator('#release-dialog')
    expect(dialog).to_be_visible()
    expect(dialog.locator('h3').first).to_have_text('v0.1.1')
    expect(dialog.locator('.release-time').first).to_contain_text('14:35')
    expect(dialog.locator('.release-time').last).to_contain_text('13:35')
    page.keyboard.press('Escape')
    expect(dialog).not_to_be_visible()
    expect(button).to_be_focused()
    button.click()
    page.locator('#release-close').click()
    expect(dialog).not_to_be_visible()
    assert not errors
