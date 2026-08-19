"""Regresní testy ote_reader.py – parsování 15minutových cen a atomický zápis."""

from __future__ import annotations

import json

import pytest

import ote_reader as legacy

PAGE = """
<html><body>
<table><tr><th>Něco jiného</th></tr><tr><td>1</td></tr></table>
<table>
  <tr><th>Časový interval</th><th>15min cena (EUR/MWh)</th><th>Množství (MWh)</th></tr>
  <tr><td>00:00 - 00:15</td><td>123,48</td><td>1 000,5</td></tr>
  <tr><td>00:15 - 00:30</td><td>1 221,78</td><td>900,1</td></tr>
  <tr><td>bez pomlčky</td><td>50,00</td><td>0</td></tr>
  <tr><td>00:30 - 00:45</td><td>-15,20</td><td>10</td></tr>
</table>
</body></html>
"""


def test_number_handles_czech_format():
    assert legacy._number("1 221,78") == 1221.78
    assert legacy._number("\xa0123,48\xa0") == 123.48
    assert legacy._number("-15,20") == -15.2


def test_extract_price_table_picks_the_right_table():
    periods = legacy._extract_price_table(PAGE)

    # Řádek bez časového rozsahu se přeskakuje, ostatní se číslují od jedné.
    assert [p.period for p in periods] == [1, 2, 3]
    assert periods[0].start == "00:00" and periods[0].end == "00:15"
    assert periods[1].price_eur_mwh == 1221.78
    # Záporná cena je legitimní stav trhu, ne chyba.
    assert periods[2].price_eur_mwh == -15.2


def test_extract_price_table_raises_when_table_missing():
    with pytest.raises(RuntimeError):
        legacy._extract_price_table("<html><body>nic</body></html>")


def test_save_day_writes_atomically(tmp_path, monkeypatch):
    monkeypatch.setattr(legacy, "DATA_DIR", tmp_path)
    payload = {"date": "2026-08-19", "periods": [], "period_count": 0}

    path = legacy.save_day(payload)

    assert path == tmp_path / "ote-2026-08-19.json"
    assert json.loads(path.read_text(encoding="utf-8"))["date"] == "2026-08-19"
    # Po dokončení nesmí zůstat dočasný soubor.
    assert list(tmp_path.glob("*.tmp")) == []
