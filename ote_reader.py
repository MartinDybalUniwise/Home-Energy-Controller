import argparse
import json
import time
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OTE_URL = "https://webdav.ote-cr.cz/cs/kratkodobe-trhy/elektrina/denni-trh"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"


@dataclass
class OTEPeriod:
    period: int
    start: str
    end: str
    price_eur_mwh: float


def _number(text: str) -> float:
    s = text.replace("\xa0", " ").strip().replace(" ", "").replace(",", ".")
    return float(s)


def _extract_price_table(html: str) -> list[OTEPeriod]:
    soup = BeautifulSoup(html, "html.parser")

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header_cells = rows[0].find_all(["th", "td"])
        headers = [c.get_text(" ", strip=True).lower() for c in header_cells]
        joined = " | ".join(headers)
        if "časový interval" not in joined or "15min cena" not in joined:
            continue

        interval_idx = next(i for i, h in enumerate(headers) if "časový interval" in h)
        price_idx = next(i for i, h in enumerate(headers) if "15min cena" in h)
        result: list[OTEPeriod] = []

        for row in rows[1:]:
            cells = row.find_all(["th", "td"])
            if len(cells) <= max(interval_idx, price_idx):
                continue
            interval = cells[interval_idx].get_text(" ", strip=True)
            price_text = cells[price_idx].get_text(" ", strip=True)
            if "-" not in interval:
                continue
            try:
                start, end = [x.strip() for x in interval.split("-", 1)]
                price = _number(price_text)
            except Exception:
                continue
            result.append(OTEPeriod(len(result) + 1, start, end, price))

        if result:
            return result

    raise RuntimeError("OTE: tabulka 15min cen nebyla na stránce nalezena")


def fetch_day(day: date, timeout: int = 30) -> dict:
    params = {"date": day.isoformat(), "time_resolution": "PT15M"}
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "cs,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    response = requests.get(OTE_URL, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    periods = _extract_price_table(response.text)

    # Since 1 Oct 2025 the day-ahead market uses 15-minute periods; normally 96 rows/day.
    # DST transition days can legitimately differ, therefore only an empty result is fatal.
    if not periods:
        raise RuntimeError(f"OTE: pro {day.isoformat()} nebyla nalezena žádná data")

    prices = [p.price_eur_mwh for p in periods]
    return {
        "date": day.isoformat(),
        "market": "OTE day-ahead market",
        "resolution": "PT15M",
        "currency": "EUR/MWh",
        "source": response.url,
        "fetched_at": datetime.now().astimezone().isoformat(),
        "period_count": len(periods),
        "min_price_eur_mwh": min(prices),
        "max_price_eur_mwh": max(prices),
        "avg_price_eur_mwh": round(sum(prices) / len(prices), 4),
        "periods": [asdict(p) for p in periods],
    }


def save_day(payload: dict) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"ote-{payload['date']}.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path


def fetch_and_save(day: date) -> Optional[Path]:
    try:
        payload = fetch_day(day)
        path = save_day(payload)
        print(f"OTE OK  {day.isoformat()}  {payload['period_count']} period  {path}")
        return path
    except Exception as exc:
        print(f"OTE ERROR  {day.isoformat()}  {exc}")
        return None


def run_once(include_tomorrow: bool = True) -> int:
    today = datetime.now().astimezone().date()
    ok = fetch_and_save(today) is not None
    if include_tomorrow:
        # Before OTE publishes D+1 results this can return no usable table; that is expected.
        fetch_and_save(today + timedelta(days=1))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="OTE day-ahead 15-minute price reader")
    parser.add_argument("--date", help="YYYY-MM-DD; when omitted reads today and tomorrow")
    parser.add_argument("--watch", action="store_true", help="run continuously")
    parser.add_argument("--interval", type=int, default=3600, help="watch interval in seconds (default 3600)")
    args = parser.parse_args()

    if args.date:
        day = date.fromisoformat(args.date)
        return 0 if fetch_and_save(day) else 1

    if not args.watch:
        return run_once(include_tomorrow=True)

    while True:
        run_once(include_tomorrow=True)
        time.sleep(max(60, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
