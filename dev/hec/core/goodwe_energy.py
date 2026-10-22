"""Keep inverter AC counters distinct from grid-meter counters (GoodWe ET)."""
from __future__ import annotations

from math import isfinite

SEMANTICS = 'ac-grid-separated-v1'
AC_FIELDS = {'e_import_day_kwh': 'inverter_ac_import_day_kwh',
             'e_export_day_kwh': 'inverter_ac_export_day_kwh'}


def energy_number(value):
    return value if (isinstance(value, (int, float)) and not isinstance(value, bool)
                     and isfinite(value) and value >= 0) else None


def energy_values(raw: dict) -> dict:
    """ET e_day_imp/exp belong to Kind.AC, not the Kind.GRID meter.

    There is no daily GRID sensor in this runtime response. A lifetime meter
    total cannot become a daily value without a separately verified baseline.
    """
    meter_available = raw.get('meter_comm_status', 1) == 1
    return {
        'energy_counter_semantics': SEMANTICS,
        'inverter_ac_import_day_kwh': energy_number(raw.get('e_day_imp')),
        'inverter_ac_export_day_kwh': energy_number(raw.get('e_day_exp')),
        'grid_import_total_kwh': energy_number(raw.get('meter_e_total_imp')) if meter_available else None,
        'grid_export_total_kwh': energy_number(raw.get('meter_e_total_exp')) if meter_available else None,
        'e_import_day_kwh': None,
        'e_export_day_kwh': None,
    }


def project_energy(record: dict) -> dict:
    """Mask known legacy AC-as-GRID mappings without modifying raw records."""
    nested = isinstance(record.get('values'), dict)
    values = {**record, **record['values']} if nested else record
    if values.get('energy_counter_semantics') == SEMANTICS:
        return record
    if not any(key in values for key in AC_FIELDS):
        return record
    projected = {'energy_counter_semantics': SEMANTICS}
    for old, explicit in AC_FIELDS.items():
        if old in values:
            projected[explicit] = values.get(explicit, energy_number(values[old]))
            projected[old] = None
    if nested:
        top_level_masks = {key: None for key in AC_FIELDS if key in record}
        return {**record, **top_level_masks, 'values': {**record['values'], **projected}}
    return {**record, **projected}
