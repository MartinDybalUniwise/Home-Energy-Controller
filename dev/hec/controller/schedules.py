"""Shared dated schedule resolution, independent of device transport."""
from datetime import datetime

from ..core.timeutil import in_window


def effective_schedule(section: dict, moment: datetime) -> dict:
    """Date-limited owner override; ordinary schedule resumes automatically."""
    override = (section.get("date_overrides") or {}).get(moment.date().isoformat())
    return {**section, **override} if isinstance(override, dict) else section


def scheduled_value(section: dict, moment: datetime):
    """Teplota podle rozvrhu. Poslední vyhovující okno vyhrává."""
    section = effective_schedule(section, moment)
    value = section.get("default_temperature")
    for window in section.get("schedule", []) or []:
        if in_window(moment, window["from"], window["to"]):
            value = window["temperature"]
    return value


def scheduled_operation(section: dict, moment: datetime) -> str | None:
    """Optional exclusive TNG mode; a bounded DHW window cannot starve heating."""
    if not section:
        return None
    section = effective_schedule(section, moment)
    mode = section.get("default_mode", "heating")
    for window in section.get("schedule", []) or []:
        if in_window(moment, window["from"], window["to"]):
            mode = window["mode"]
    if mode not in ("heating", "boiler", "off"):
        raise ValueError("Invalid exclusive TNG operation mode")
    return mode
