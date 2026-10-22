"""Persistence regressions against the hardware-free mock preview."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def open_settings(page):
    page.goto("/#/settings")
    expect(page.locator("#settings-form")).to_be_visible()


def save_settings(page):
    with page.expect_response(
        lambda response: response.url.endswith("/api/config")
        and response.request.method == "PUT"
    ) as saved:
        page.locator("#settings-form button[type='submit']").click()
    assert saved.value.ok, saved.value.text()
    assert saved.value.json()["saved"] is True


def test_optional_numeric_overrides_roundtrip_values_and_null(page):
    open_settings(page)
    page.locator("details.technical-settings").click()
    for source in ("goodwe", "tng", "ote"):
        page.locator(f"#f_controller_max_data_age_by_source_{source}").fill("600")
    save_settings(page)
    config = page.request.get("/api/config").json()["config"]
    assert config["controller"]["max_data_age_by_source"] == dict.fromkeys(("goodwe", "tng", "ote"), 600)
    for source in ("goodwe", "tng", "ote"):
        page.locator(f"#f_controller_max_data_age_by_source_{source}").fill("")
    save_settings(page)
    page.reload()
    expect(page.locator("#settings-form")).to_be_visible()
    config = page.request.get("/api/config").json()["config"]
    assert config["controller"]["max_data_age_by_source"] == dict.fromkeys(("goodwe", "tng", "ote"))
    assert config["controller"]["enabled"] is False
    assert config["tng"]["write_enabled"] is False
    assert config["goodwe"]["enabled"] is False


def test_rejected_save_preserves_active_language(page):
    open_settings(page)
    language = page.locator("html").get_attribute("lang")
    page.route("**/api/config", lambda route: route.fulfill(
        status=400, json={"errors": ["Rejected test configuration"]}
    ) if route.request.method == "PUT" else route.continue_())
    page.locator("#f_ui_language").select_option("cs" if language == "en" else "en")
    page.locator("#settings-form button[type='submit']").click()
    expect(page.locator("#settings-message .error")).to_have_text("Rejected test configuration")
    expect(page.locator("html")).to_have_attribute("lang", language)
    page.reload()
    expect(page.locator("#settings-form")).to_be_visible()
    expect(page.locator("html")).to_have_attribute("lang", language)
