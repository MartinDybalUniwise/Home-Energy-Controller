"""Predikce výroby, spotřeby, tepla, nabití baterie a nákladu.

Modely jsou záměrně jednoduché a vysvětlitelné (kap. 11 a 29 zadání):
učí se z vlastní historie lineárním poměrem, ne strojovým učením. Každý výstup
nese interval a míru jistoty – falešná přesnost je horší než přiznaná neznalost.
"""

from __future__ import annotations

from datetime import date, timedelta
from statistics import median

from ..core.logging_setup import get_logger
from ..core.timeutil import now_local, parse_iso, to_iso
from ..storage.base import read_json

# Šířka intervalu podle množství naučených dat.
CONFIDENCE_BANDS = {"high": 0.12, "medium": 0.20, "low": 0.35}
MIN_DAYS_MEDIUM = 7
MIN_DAYS_HIGH = 21
DEFAULT_PERFORMANCE_RATIO = 0.75     # než se systém naučí vlastní poměr
BASE_TEMPERATURE_C = 18.0
APPLIANCE_WINDOW_HOURS = 2
DHW_WINDOW_HOURS = 2


def safe_median(values: list[float]) -> float | None:
    values = [value for value in values if isinstance(value, (int, float))]
    return median(values) if values else None


class Predictor:
    source = "prediction"

    def __init__(self, config, storage, summaries=None):
        self.config = config
        self.storage = storage
        self.summaries = summaries
        self.log = get_logger("predictor")

    # --- učení z vlastní historie ------------------------------------------
    def _history(self) -> list[dict]:
        days = int(self.config.get("prediction.learning_days", 30))
        if self.summaries is not None:
            return self.summaries.recent(days)
        # Stejné okno jako Summaries.recent – záznam na hranici jinak vypadne.
        start = now_local() - timedelta(days=days + 1)
        return self.storage.query("summary", start, now_local())

    def pv_factor(self, history: list[dict] | None = None) -> tuple[float, int]:
        """Kolik kWh vyrobí instalace na 1 kWh/m² ozáření. Naučeno z vlastních dat."""
        history = history if history is not None else self._history()
        ratios = [day["pv_kwh"] / day["irradiation_kwh_m2"]
                  for day in history
                  if day.get("irradiation_kwh_m2") and day.get("pv_kwh")
                  and day["irradiation_kwh_m2"] > 0.5]
        learned = safe_median(ratios)
        if learned:
            return round(learned, 3), len(ratios)
        fallback = float(self.config.get("prediction.pv_peak_kwp", 10.0)) * DEFAULT_PERFORMANCE_RATIO
        return round(fallback, 3), 0

    def consumption_estimate(self, target: date, history: list[dict] | None = None) -> tuple[float, int]:
        """Medián denní spotřeby, zvlášť pro pracovní dny a víkend."""
        history = history if history is not None else self._history()
        weekend = target.weekday() >= 5
        same_kind = [day["house_kwh"] for day in history
                     if day.get("house_kwh") and
                     (parse_iso(day["date"] + "T00:00:00").weekday() >= 5) == weekend]
        value = safe_median(same_kind)
        if value is None:
            value = safe_median([day.get("house_kwh") for day in history])
        return (round(value, 2), len(same_kind)) if value else (0.0, 0)

    def heat_slope(self, history: list[dict] | None = None) -> tuple[float | None, int]:
        """Spotřeba tepelného čerpadla na jeden denostupeň."""
        history = history if history is not None else self._history()
        ratios = [day["heatpump_kwh"] / day["degree_days"]
                  for day in history
                  if day.get("degree_days") and day.get("heatpump_kwh")
                  and day["degree_days"] > 0.5]
        learned = safe_median(ratios)
        return (round(learned, 3), len(ratios)) if learned else (None, 0)

    @staticmethod
    def confidence_for(samples: int) -> str:
        if samples >= MIN_DAYS_HIGH:
            return "high"
        if samples >= MIN_DAYS_MEDIUM:
            return "medium"
        return "low"

    # --- vstupy z počasí a cen ----------------------------------------------
    def _weather(self) -> dict:
        return read_json(self.config.data_dir / "weather.json", {}) or {}

    def _prices_for(self, day: date) -> list[dict]:
        payload = read_json(self.config.data_dir / f"ote-{day.isoformat()}.json") or {}
        return payload.get("periods", [])

    @staticmethod
    def _irradiation_for(weather: dict, day: date) -> float | None:
        """Ozáření [kWh/m²] z hodinové předpovědi pro daný den."""
        total = 0.0
        found = False
        for hour in weather.get("forecast_hourly", []):
            stamp = parse_iso(hour.get("time"))
            ghi = hour.get("ghi_wm2")
            if stamp is None or ghi is None or stamp.date() != day:
                continue
            total += float(ghi) / 1000.0        # W/m² po hodinu = Wh/m²
            found = True
        return round(total, 3) if found else None

    @staticmethod
    def _mean_temperature(weather: dict, day: date) -> float | None:
        for entry in weather.get("forecast_daily", []):
            if entry.get("date") == day.isoformat():
                low, high = entry.get("temp_min_c"), entry.get("temp_max_c")
                if low is not None and high is not None:
                    return round((low + high) / 2.0, 1)
        temps = [hour.get("temp_c") for hour in weather.get("forecast_hourly", [])
                 if parse_iso(hour.get("time")) and parse_iso(hour["time"]).date() == day]
        temps = [t for t in temps if t is not None]
        return round(sum(temps) / len(temps), 1) if temps else None

    # --- okna ----------------------------------------------------------------
    @staticmethod
    def cheapest_window(periods: list[dict], hours: int, *, between: tuple[str, str] | None = None) -> dict | None:
        """Nejlevnější souvislé okno. Ceny jsou po 15 minutách, okno v hodinách."""
        if not periods:
            return None
        usable = [p for p in periods
                  if between is None or (between[0] <= p["start"] < between[1])]
        span = hours * 4
        if len(usable) < span:
            return None

        def price(period):
            return period.get("price_total_czk_kwh", period.get("price_eur_mwh", 0))

        best_index, best_cost = 0, None
        for index in range(len(usable) - span + 1):
            cost = sum(price(p) for p in usable[index:index + span])
            if best_cost is None or cost < best_cost:
                best_index, best_cost = index, cost
        window = usable[best_index:best_index + span]
        return {"from": window[0]["start"], "to": window[-1]["end"],
                "mean_price": round(best_cost / span, 3)}

    # --- předpověď ------------------------------------------------------------
    def forecast(self, days: int = 3) -> dict:
        history = self._history()
        weather = self._weather()
        factor, factor_samples = self.pv_factor(history)
        slope, slope_samples = self.heat_slope(history)

        if not weather.get("forecast_hourly"):
            return {"available": False, "reason_key": "prediction.not_enough_data",
                    "learned_days": len(history)}

        today = now_local().date()
        out_days = []
        for offset in range(1, days + 1):
            day = today + timedelta(days=offset)
            irradiation = self._irradiation_for(weather, day)
            if irradiation is None:
                continue

            pv = round(irradiation * factor, 1)
            confidence = self.confidence_for(factor_samples)
            band = CONFIDENCE_BANDS[confidence]

            consumption, consumption_samples = self.consumption_estimate(day, history)
            mean_temp = self._mean_temperature(weather, day)
            degree_days = max(0.0, BASE_TEMPERATURE_C - mean_temp) if mean_temp is not None else None
            heat = round(slope * degree_days, 1) if (slope and degree_days) else None

            total_load = consumption + (heat or 0.0)
            balance = round(total_load - pv, 1)
            periods = self._prices_for(day)
            cost = self._estimate_cost(balance, periods)

            out_days.append({
                "date": day.isoformat(),
                "pv_kwh": pv,
                "pv_kwh_low": round(pv * (1 - band), 1),
                "pv_kwh_high": round(pv * (1 + band), 1),
                "irradiation_kwh_m2": irradiation,
                "confidence": confidence,
                "consumption_kwh": consumption,
                "heat_kwh": heat,
                "mean_temperature_c": mean_temp,
                "grid_balance_kwh": balance,
                "cost_czk": cost,
                "battery_soc_min_pct": self._simulate_soc(pv, total_load),
                "best_appliance_window": self._format_window(
                    self.cheapest_window(periods, APPLIANCE_WINDOW_HOURS)),
                "best_dhw_window": self._format_window(
                    self.cheapest_window(periods, DHW_WINDOW_HOURS, between=("08:00", "17:00"))),
                "prices_known": bool(periods),
                "learned_days": {"pv": factor_samples, "consumption": consumption_samples,
                                 "heat": slope_samples},
            })

        return {
            "available": bool(out_days),
            "generated_at": to_iso(now_local()),
            "pv_factor_kwh_per_kwh_m2": factor,
            "heat_kwh_per_degree_day": slope,
            "days": out_days,
            "accuracy": self.accuracy(history),
        }

    @staticmethod
    def _format_window(window: dict | None) -> str | None:
        return f"{window['from']}–{window['to']}" if window else None

    def _estimate_cost(self, balance_kwh: float, periods: list[dict]) -> float | None:
        """Odhad nákladu. Bez známých cen se nic nedopočítává."""
        if not periods:
            return None
        prices = [p.get("price_total_czk_kwh") for p in periods if p.get("price_total_czk_kwh") is not None]
        if not prices:
            return None
        mean_price = sum(prices) / len(prices)
        if balance_kwh >= 0:
            return round(balance_kwh * mean_price, 1)
        export_price = float(self.config.get("ote.export_price_czk_kwh", 0.0))
        return round(balance_kwh * export_price, 1)

    def _simulate_soc(self, pv_kwh: float, load_kwh: float) -> float | None:
        """Hrubá simulace: přebytek nabíjí, deficit vybíjí. Meze 10–100 %."""
        capacity = float(self.config.get("prediction.battery_capacity_kwh", 0.0))
        if capacity <= 0:
            return None
        current = self.storage.latest("goodwe") or {}
        soc = float(current.get("battery_soc") or 50.0)
        delta = (pv_kwh - load_kwh) / capacity * 100.0
        return round(max(10.0, min(100.0, soc + delta)), 1)

    # --- zpětné vyhodnocení ----------------------------------------------------
    def store_forecast(self, forecast: dict) -> None:
        for day in forecast.get("days", []):
            self.storage.append(self.source, {"timestamp": to_iso(now_local()),
                                              "source": self.source, **day})

    def accuracy(self, history: list[dict] | None = None) -> dict | None:
        """Průměrná absolutní procentní chyba predikce výroby proti skutečnosti."""
        history = history if history is not None else self._history()
        actual = {day["date"]: day.get("pv_kwh") for day in history if day.get("pv_kwh")}
        if not actual:
            return None

        predicted: dict[str, float] = {}
        start = now_local() - timedelta(days=int(self.config.get("prediction.learning_days", 30)))
        for record in self.storage.query(self.source, start, now_local()):
            # Poslední predikce pro daný den vyhrává (je nejlépe informovaná).
            if record.get("date") and record.get("pv_kwh"):
                predicted[record["date"]] = record["pv_kwh"]

        pairs = [(actual[day], predicted[day]) for day in predicted if day in actual and actual[day] > 0]
        if not pairs:
            return None
        errors = [abs(real - guess) / real for real, guess in pairs]
        return {"pv_mape_pct": round(sum(errors) / len(errors) * 100, 1), "samples": len(pairs)}
