"""Analýza zatížení fází.

Zadání je v tomto bodě jednoznačné: **nic se automaticky nepřepojuje.**
Výstupem je doporučení pro člověka, ne zásah.
"""

from __future__ import annotations

from datetime import timedelta

from ..core.timeutil import now_local
from ..storage.series import numeric

PHASES = ("l1_w", "l2_w", "l3_w")
IMBALANCE_W = 2000.0          # od jakého rozdílu má smysl doporučovat přepojení
RATIO = 2.5                   # nebo od jakého poměru nejvíc/nejmíň zatížené fáze


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


class PhaseAnalyser:
    def __init__(self, config, storage):
        self.config = config
        self.storage = storage

    def analyse(self, days: int = 7) -> dict:
        records = self.storage.query("goodwe", now_local() - timedelta(days=days), now_local())
        series = {phase: [numeric(r.get(phase)) for r in records] for phase in PHASES}
        series = {phase: [v for v in values if v is not None] for phase, values in series.items()}

        if not all(series.values()):
            # Měnič fázové hodnoty nevystavuje – raději nic než odhad.
            return {"available": False, "reason_key": "analysis.phases_unavailable"}

        stats = {}
        for phase, values in series.items():
            stats[phase] = {
                "mean_w": round(sum(values) / len(values), 1),
                "p95_w": round(percentile(values, 0.95), 1),
                "max_w": round(max(values), 1),
            }

        means = {phase: stats[phase]["mean_w"] for phase in PHASES}
        peaks = {phase: stats[phase]["p95_w"] for phase in PHASES}
        highest = max(means, key=means.get)
        lowest = min(means, key=means.get)
        spread = round(peaks[highest] - peaks[lowest], 1)
        ratio = round(means[highest] / means[lowest], 2) if means[lowest] > 0 else None

        recommendations = []
        if spread >= IMBALANCE_W or (ratio is not None and ratio >= RATIO):
            recommendations.append({
                "reason_key": "analysis.phase_imbalance",
                "reason_params": {
                    "high": highest.upper().replace("_W", ""),
                    "low": lowest.upper().replace("_W", ""),
                    "high_kw": round(peaks[highest] / 1000, 1),
                    "low_kw": round(peaks[lowest] / 1000, 1),
                },
            })

        return {
            "available": True,
            "days": days,
            "samples": len(records),
            "phases": stats,
            "imbalance_w": spread,
            "ratio": ratio,
            "recommendations": recommendations,
        }
