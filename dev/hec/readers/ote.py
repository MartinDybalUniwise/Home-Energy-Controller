"""Reader spotových cen OTE (denní trh, 15minutová perioda).

Zachovává formát `data/ote-YYYY-MM-DD.json` z prototypu – je to kontrakt.
Nová pole (ceny v CZK) se přidávají, stávající se nepřejmenovávají.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import requests
from bs4 import BeautifulSoup

from ..core.timeutil import now_local, to_iso
from ..storage.base import atomic_write_json, read_json
from .base import BaseReader

OTE_URL = "https://webdav.ote-cr.cz/cs/kratkodobe-trhy/elektrina/denni-trh"
CNB_URL = "https://www.cnb.cz/cs/financni-trhy/devizovy-trh/kurzy-devizoveho-trhu/kurzy-devizoveho-trhu/denni_kurz.txt"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36")


def parse_number(text: str) -> float:
    return float(text.replace("\xa0", " ").strip().replace(" ", "").replace(",", "."))


def extract_periods(html: str) -> list[dict]:
    """Najde tabulku 15minutových cen. Ostatní tabulky na stránce se ignorují."""
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [c.get_text(" ", strip=True).lower() for c in rows[0].find_all(["th", "td"])]
        joined = " | ".join(headers)
        if "časový interval" not in joined or "15min cena" not in joined:
            continue

        interval_idx = next(i for i, h in enumerate(headers) if "časový interval" in h)
        price_idx = next(i for i, h in enumerate(headers) if "15min cena" in h)
        periods: list[dict] = []
        for row in rows[1:]:
            cells = row.find_all(["th", "td"])
            if len(cells) <= max(interval_idx, price_idx):
                continue
            interval = cells[interval_idx].get_text(" ", strip=True)
            if "-" not in interval:
                continue
            try:
                start, end = (part.strip() for part in interval.split("-", 1))
                price = parse_number(cells[price_idx].get_text(" ", strip=True))
            except (ValueError, StopIteration):
                continue
            periods.append({"period": len(periods) + 1, "start": start, "end": end,
                            "price_eur_mwh": price})
        if periods:
            return periods
    raise RuntimeError("OTE: tabulka 15min cen nebyla na stránce nalezena")


class OteReader(BaseReader):
    name = "ote"

    def __init__(self, config, storage=None, session=None):
        self.session = session or requests.Session()
        super().__init__(config, storage)

    def interval_seconds(self) -> int:
        return int(self.config.get("polling.ote_minutes", 240)) * 60

    def _next_publish_boundary_seconds(self, moment: datetime) -> float | None:
        """Ceny pro zítřek jednou zveřejněné se už neregenerují – dokud je
        nemáme uložené, má smysl probudit se blízko obvyklého času zveřejnění
        (kolem 13:00-13:30) místo čekání na celý (několikahodinový) interval."""
        tomorrow = moment.date() + timedelta(days=1)
        if self.day_path(tomorrow).exists():
            return None
        candidate = moment.replace(hour=13, minute=15, second=0, microsecond=0)
        if candidate <= moment:
            return None                                        # dnešní okno už proběhlo
        return (candidate - moment).total_seconds()

    def schedule_next(self, monotonic_now: float) -> None:
        super().schedule_next(monotonic_now)
        boundary = self._next_publish_boundary_seconds(now_local())
        if boundary is not None:
            self._next_at = min(self._next_at, monotonic_now + boundary)

    # --- kurz --------------------------------------------------------------
    def eur_czk_rate(self) -> float:
        """Kurz ČNB s pádem zpět na hodnotu z konfigurace, když je banka nedostupná."""
        fallback = float(self.config.get("ote.eur_czk_rate", 25.0))
        if not self.config.get("ote.fetch_rate_from_cnb", True):
            return fallback

        cache_path = self.config.data_dir / "current_fx.json"
        cached = read_json(cache_path, {}) or {}
        if cached.get("date") == now_local().date().isoformat() and cached.get("eur_czk"):
            return float(cached["eur_czk"])

        try:
            response = self.session.get(CNB_URL, headers={"User-Agent": USER_AGENT}, timeout=15)
            response.raise_for_status()
            for line in response.text.splitlines():
                parts = line.split("|")
                if len(parts) == 5 and parts[3] == "EUR":
                    rate = parse_number(parts[4]) / float(parts[2] or 1)
                    atomic_write_json(cache_path, {"date": now_local().date().isoformat(),
                                                   "eur_czk": rate, "source": "cnb",
                                                   "fetched_at": to_iso(now_local())})
                    return rate
        except Exception as exc:                              # noqa: BLE001
            self.log.warning("cnb_rate_failed | error=%s fallback=%s", type(exc).__name__, fallback)
        return fallback

    # --- ceny --------------------------------------------------------------
    def price_czk_kwh(self, eur_mwh: float, rate: float) -> tuple[float, float]:
        """Vrací (holý spot, konečná cena včetně distribuce, poplatků a DPH)."""
        spot = eur_mwh * rate / 1000.0
        total = (spot
                 + float(self.config.get("ote.distribution_czk_kwh", 0.0))
                 + float(self.config.get("ote.fees_czk_kwh", 0.0)))
        total *= 1.0 + float(self.config.get("ote.vat_rate", 0.0))
        return round(spot, 4), round(total, 4)

    def fetch_day(self, day: date) -> dict:
        response = self.session.get(
            OTE_URL,
            params={"date": day.isoformat(), "time_resolution": "PT15M"},
            headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"},
            timeout=30,
        )
        response.raise_for_status()
        periods = extract_periods(response.text)

        rate = self.eur_czk_rate()
        for period in periods:
            spot, total = self.price_czk_kwh(period["price_eur_mwh"], rate)
            period["price_czk_kwh"] = spot
            period["price_total_czk_kwh"] = total

        prices = [p["price_eur_mwh"] for p in periods]
        return {
            "date": day.isoformat(),
            "market": "OTE day-ahead market",
            "resolution": "PT15M",
            "currency": "EUR/MWh",
            "source": str(response.url),
            "fetched_at": to_iso(now_local()),
            "period_count": len(periods),
            "min_price_eur_mwh": min(prices),
            "max_price_eur_mwh": max(prices),
            "avg_price_eur_mwh": round(sum(prices) / len(prices), 4),
            "eur_czk_rate": round(rate, 4),
            "periods": periods,
        }

    def save_day(self, payload: dict):
        return atomic_write_json(self.config.data_dir / f"ote-{payload['date']}.json", payload)

    def day_path(self, day: date):
        return self.config.data_dir / f"ote-{day.isoformat()}.json"

    def load_or_fetch_day(self, day: date, *, required: bool = True) -> dict | None:
        """Jednou zveřejněná cena pro daný den se už nemění – síť se zatěžuje
        jen dokud soubor ještě nemáme, ne při každém pravidelném čtení."""
        cached = read_json(self.day_path(day), None)
        if cached is not None:
            return cached
        try:
            payload = self.fetch_day(day)
        except Exception as exc:                              # noqa: BLE001
            if required:
                raise
            self.log.info("ote_tomorrow_unavailable | day=%s reason=%s",
                          day.isoformat(), type(exc).__name__)
            return None
        self.save_day(payload)
        return payload

    @staticmethod
    def period_for(payload: dict, moment: datetime) -> dict | None:
        clock = moment.strftime("%H:%M")
        for period in payload.get("periods", []):
            if period["start"] <= clock < period["end"]:
                return period
        return None

    def read(self) -> dict:
        today = now_local().date()
        payload = self.load_or_fetch_day(today)
        # D+1 se zveřejňuje po uzávěrce aukce ve 12:00, výsledky bývají na webu
        # OTE k dispozici kolem 13:00-13:30; dřívější prázdný výsledek není chyba.
        tomorrow_payload = self.load_or_fetch_day(today + timedelta(days=1), required=False)

        current = self.period_for(payload, now_local()) or {}
        prices = [p["price_total_czk_kwh"] for p in payload["periods"]]
        return {
            "date": payload["date"],
            "eur_czk_rate": payload["eur_czk_rate"],
            "price_eur_mwh": current.get("price_eur_mwh"),
            "price_czk_kwh": current.get("price_czk_kwh"),
            "price_total_czk_kwh": current.get("price_total_czk_kwh"),
            "period_start": current.get("start"),
            "min_today_czk_kwh": min(prices) if prices else None,
            "max_today_czk_kwh": max(prices) if prices else None,
            "avg_today_czk_kwh": round(sum(prices) / len(prices), 4) if prices else None,
            "tomorrow_available": bool(tomorrow_payload),
        }
