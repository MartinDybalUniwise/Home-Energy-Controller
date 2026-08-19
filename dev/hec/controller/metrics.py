"""Měření přínosu systému (kap. 34 zadání).

Poctivost před efektem: **nepočítáme hypotetickou úsporu proti scénáři, který
nikdy neproběhl.** Počítáme, co je z dat doložitelné – kolik se nakoupilo,
kolik dodalo, jaký podíl výroby zůstal doma a za jakou cenu se ohřívala voda.
"""

from __future__ import annotations

from datetime import timedelta

from ..core.timeutil import now_local


class Metrics:
    def __init__(self, config, storage, summaries):
        self.config = config
        self.storage = storage
        self.summaries = summaries

    def totals(self, days: int = 30) -> dict:
        history = self.summaries.recent(days)
        if not history:
            return {"days": 0}

        def total(field: str) -> float:
            return round(sum(day.get(field) or 0 for day in history), 1)

        pv = total("pv_kwh")
        export = total("grid_export_kwh")
        house = total("house_kwh")
        grid_import = total("grid_import_kwh")
        priced = [day for day in history if day.get("priced")]

        return {
            "days": len(history),
            "pv_kwh": pv,
            "house_kwh": house,
            "grid_import_kwh": grid_import,
            "grid_export_kwh": export,
            "heatpump_kwh": total("heatpump_kwh"),
            "appliances_kwh": total("appliances_kwh"),
            "self_consumption_pct": round((pv - export) / pv * 100, 1) if pv else None,
            "self_sufficiency_pct": round((house - grid_import) / house * 100, 1) if house else None,
            "cost_czk": round(sum(day.get("cost_czk") or 0 for day in priced), 1) if priced else None,
            "revenue_czk": round(sum(day.get("revenue_czk") or 0 for day in priced), 1) if priced else None,
            "priced_days": len(priced),
        }

    def decisions(self, days: int = 30) -> dict:
        """Kolik rozhodnutí systém udělal a kolik jich skutečně dopadlo na čerpadlo."""
        records = self.storage.query(self.source_name, now_local() - timedelta(days=days), now_local())
        applied = [record for record in records if record.get("applied")]
        by_rule: dict[str, int] = {}
        for record in records:
            by_rule[record.get("rule", "?")] = by_rule.get(record.get("rule", "?"), 0) + 1
        return {"total": len(records), "applied": len(applied), "by_rule": by_rule}

    source_name = "controller"

    def report(self, days: int = 30) -> dict:
        return {
            "days": days,
            "totals": self.totals(days),
            "decisions": self.decisions(days),
            # Srovnání proti provozu bez optimalizace vyžaduje referenční období;
            # dokud neproběhne, systém žádnou úsporu netvrdí.
            "counterfactual_available": False,
        }
