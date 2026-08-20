"""Testy importu vyúčtování sdílení (dev/step09, fáze C).

Formát exportu je zdokumentovaný v dev/step09/SHARING_IMPORT_FORMAT.md a
ověřený na reálném souboru. Testy používají syntetická data a falešný
"sešit" (stejný vzor jako FakeSession/FakeResponse pro HTTP readery) místo
skutečné knihovny openpyxl – parser i reader ji nikdy nepotřebují napřímo,
jen přes injektovatelné `load_workbook`.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest
from hec.core import config as config_mod
from hec.core import schema
from hec.readers.sharing_parser import parse_sharing_export
from hec.readers.sharing_reader import SharingReader

EAN = "859000000000000001"


class FakeCell:
    def __init__(self, value):
        self.value = value


class FakeWorksheet:
    def __init__(self, rows: list[list]):
        self._rows = rows
        self.max_row = len(rows)
        self.max_column = max((len(r) for r in rows), default=0)

    def cell(self, row: int, column: int) -> FakeCell:
        values = self._rows[row - 1] if row - 1 < len(self._rows) else []
        value = values[column - 1] if column - 1 < len(values) else None
        return FakeCell(value)


class FakeWorkbook:
    def __init__(self, rows: list[list], sheet_name: str = EAN):
        self.sheetnames = [sheet_name]
        self._ws = FakeWorksheet(rows)

    def __getitem__(self, _name):
        return self._ws


def row(cols: dict) -> list:
    """Řádek dlouhý 14 sloupců (A–N), výchozí None, zadané sloupce indexem 1."""
    values = [None] * 14
    for index, value in cols.items():
        values[index - 1] = value
    return values


HEADER = row({1: "EAN", 2: "DEN", 3: "HODINA", 4: "MINUTA",
               5: "Výroba kWh (dodávka do sítě)", 6: "Výroba kWh (po odečtení sdílení)",
               7: "Sdílená energie (kWH)", 8: "Kč/1MWh", 9: "Celkem"})


def make_rows(day: date = date(2026, 7, 1)) -> list[list]:
    """Čtyři patnáctiminutové intervaly, dva z nich se sdílením + měsíční
    souhrn ve sloupcích K–N (přesně jak leží v reálném exportu vedle sebe)."""
    return [
        HEADER,
        row({1: EAN, 2: day, 3: 9, 4: 0, 5: 0.10, 6: 0.10, 7: 0.0, 8: 4000.0, 9: 0.40}),
        row({1: EAN, 2: day, 3: 9, 4: 15, 5: 0.30, 6: 0.20, 7: 0.10, 8: 3000.0, 9: 0.60,
               11: "Měsíční vyúčtování", 12: "Test Uživatel"}),
        row({1: EAN, 2: day, 3: 9, 4: 30, 5: 0.40, 6: 0.25, 7: 0.15, 8: 2500.0, 9: 0.625,
               11: EAN}),
        row({1: EAN, 2: day, 3: 9, 4: 45, 5: 0.20, 6: 0.20, 7: 0.0, 8: 3500.0, 9: 0.70,
               11: "01.07.2026 - 31.07.2026"}),
        row({11: None, 12: "množství", 13: "jednotková cena", 14: "výsledná cena"}),
        row({11: "Celková dodávka do sítě", 12: 0.001}),        # MWh = 1.0 kWh (sum E)
        row({11: "Sdílená elektřina", 12: 0.00025}),             # MWh = 0.25 kWh (sum G)
        row({11: "Elektřina prodaná GoEnergy", 12: 0.00075}),    # MWh = 0.75 kWh (sum F)
        row({11: "Srážka z ceny", 12: 0.00075, 13: -300.0, 14: -0.225}),
        row({11: "Fakturace", 12: 0.00075, 13: 2989.5, 14: 2.0}),
    ]


# --- parser ------------------------------------------------------------------

def test_parser_reads_intervals_and_settlement_from_synthetic_export():
    payload = parse_sharing_export(Path("irrelevant.xlsx"),
                                    load_workbook=lambda _p: FakeWorkbook(make_rows()))

    assert payload["ean"] == EAN
    assert payload["period_from"] == date(2026, 7, 1)
    assert len(payload["intervals"]) == 4
    assert payload["intervals"][0]["timestamp"] == datetime(2026, 7, 1, 9, 0)
    assert payload["intervals"][2]["shared_kwh"] == 0.15

    settlement = payload["settlement"]
    assert settlement["delivered_kwh"] == 1.0
    assert settlement["shared_kwh"] == 0.25
    assert settlement["sold_kwh"] == 0.75
    assert settlement["deduction_czk"] == -0.225
    assert settlement["invoice_czk"] == 2.0
    assert settlement["period_label"] == "01.07.2026 - 31.07.2026"


def test_parser_rejects_a_file_with_missing_columns():
    broken = [row({1: "EAN", 2: "DEN"})]     # chybí zbytek povinných sloupců
    with pytest.raises(ValueError, match="chybí sloupce"):
        parse_sharing_export(Path("x.xlsx"), load_workbook=lambda _p: FakeWorkbook(broken))


def test_parser_rejects_a_file_with_no_interval_rows():
    empty = [HEADER]
    with pytest.raises(ValueError, match="žádné intervalové"):
        parse_sharing_export(Path("x.xlsx"), load_workbook=lambda _p: FakeWorkbook(empty))


def test_parser_settlement_field_is_none_when_a_row_is_missing_not_guessed():
    rows = make_rows()
    rows.pop()   # odstraní řádek "Fakturace"
    payload = parse_sharing_export(Path("x.xlsx"), load_workbook=lambda _p: FakeWorkbook(rows))
    assert payload["settlement"]["invoice_czk"] is None
    assert payload["settlement"]["deduction_czk"] is not None   # ostatní řádky zůstávají


# --- reader ------------------------------------------------------------------

def make_config(tmp_path, **overrides):
    data = schema.defaults()
    data["sharing"].update({"enabled": True, "producer_ean": EAN, **overrides})
    config = config_mod.Config(data, path=tmp_path / "c.json", root=tmp_path)
    config.ensure_dirs()
    return config


def test_reader_requires_import_path_to_be_configured(tmp_path):
    config = make_config(tmp_path, import_path="")
    reader = SharingReader(config)
    with pytest.raises(RuntimeError, match="import_path"):
        reader.read()


def test_reader_imports_a_new_file_into_history(tmp_path):
    import_dir = tmp_path / "sdileni"
    import_dir.mkdir()
    (import_dir / "2026-07.xlsx").write_bytes(b"stub")   # obsah čte fake loader, ne skutečný soubor
    config = make_config(tmp_path, import_path=str(import_dir))
    reader = SharingReader(config, load_workbook=lambda _p: FakeWorkbook(make_rows()))

    sample = reader.poll()

    assert sample.ok is True
    assert sample.values["shared_kwh"] == 0.25
    assert sample.values["invoice_czk"] == 2.0
    assert sample.values["newly_imported"] == ["2026-07.xlsx"]

    targets = reader.history_targets(sample.values, sample)
    interval_targets = [t for t in targets if t[0] == "sharing"]
    settlement_targets = [t for t in targets if t[0] == "sharing_settlement"]
    assert len(interval_targets) == 4
    assert interval_targets[2][1]["shared_sent_kwh"] == 0.15
    assert interval_targets[2][1]["role"] == "producer"

    assert len(settlement_targets) == 1
    assert settlement_targets[0][1]["shared_kwh"] == 0.25
    assert settlement_targets[0][1]["timestamp"]           # dohledatelné podle konce období, ne importu


def test_reader_does_not_duplicate_settlement_history_when_nothing_new(tmp_path):
    import_dir = tmp_path / "sdileni"
    import_dir.mkdir()
    (import_dir / "2026-07.xlsx").write_bytes(b"stub")
    config = make_config(tmp_path, import_path=str(import_dir))
    reader = SharingReader(config, load_workbook=lambda _p: FakeWorkbook(make_rows()))

    first = reader.poll()
    first_targets = reader.history_targets(first.values, first)
    second = reader.poll()
    second_targets = reader.history_targets(second.values, second)

    assert len([t for t in first_targets if t[0] == "sharing_settlement"]) == 1
    assert second_targets == []   # nic nového tento cyklus – žádný duplicitní zápis


def test_reader_does_not_reimport_an_unchanged_file(tmp_path):
    import_dir = tmp_path / "sdileni"
    import_dir.mkdir()
    (import_dir / "2026-07.xlsx").write_bytes(b"stub")
    config = make_config(tmp_path, import_path=str(import_dir))
    reader = SharingReader(config, load_workbook=lambda _p: FakeWorkbook(make_rows()))

    reader.read()
    second = reader.read()

    assert second["newly_imported"] == []
    # Poslední známé vyúčtování zůstává i bez nového importu tohoto cyklu.
    assert second["shared_kwh"] == 0.25


def test_reader_survives_a_gate_when_config_is_restored(tmp_path):
    """Stav (naimportované soubory) přežije restart readeru – stejný vzor
    jako u TngReader."""
    import_dir = tmp_path / "sdileni"
    import_dir.mkdir()
    (import_dir / "2026-07.xlsx").write_bytes(b"stub")
    config = make_config(tmp_path, import_path=str(import_dir))
    SharingReader(config, load_workbook=lambda _p: FakeWorkbook(make_rows())).read()

    fresh = SharingReader(config, load_workbook=lambda _p: FakeWorkbook(make_rows()))
    result = fresh.read()
    assert result["newly_imported"] == []          # už bylo naimportováno v předchozí instanci
    assert result["shared_kwh"] == 0.25             # ale poslední vyúčtování se dotáhlo ze stavu
