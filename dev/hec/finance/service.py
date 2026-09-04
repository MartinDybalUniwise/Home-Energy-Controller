"""Servisní vrstva HEF nad stávajícím úložištěm.

Záměrně nezasahuje do controlleru ani readerů provozní části (GoodWe/TNG/OTE).
V prvním kroku vrací dashboard a ruční položky z historických záznamů tak, aby
bylo možné modul integrovat do stejného API/UI a dál ho rozšiřovat.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from ..core.timeutil import now_local, parse_iso, to_iso

EXPENSE_TYPES = {"CAPEX", "SERVICE", "REPAIR", "REVISION", "EXPENSE", "OTHER"}
INCOME_TYPES = {"SUBSIDY", "EXPORT", "SHARING", "INCOME"}


class FinanceService:
    """Čtení a agregace finančních dat pro API/UI."""

    def __init__(self, app):
        self.app = app

    @staticmethod
    def _amount(row: dict[str, Any]) -> float:
        for key in ("amount_total", "amount", "value"):
            value = row.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0
        return 0.0

    @staticmethod
    def _kind(row: dict[str, Any]) -> str:
        return str(row.get("transaction_type") or row.get("category") or "").strip().upper()

    @staticmethod
    def _when(row: dict[str, Any]) -> datetime | None:
        for key in ("transaction_date", "paid_date", "issue_date", "timestamp"):
            stamp = parse_iso(row.get(key))
            if stamp is not None:
                return stamp
        return None

    def dashboard(self, params: dict[str, str] | None = None) -> dict[str, Any]:
        params = params or {}
        now = now_local()
        year = now.year
        if params.get("year"):
            try:
                year = int(params["year"])
            except (TypeError, ValueError):
                year = now.year

        frm = datetime(year, 1, 1, tzinfo=now.tzinfo)
        to = now if year == now.year else datetime(year, 12, 31, 23, 59, 59, tzinfo=now.tzinfo)
        records = self.app.storage.query("finance_transactions", frm, to)

        totals = defaultdict(float)
        capex_gross = 0.0
        subsidies = 0.0
        monthly_net: dict[str, float] = defaultdict(float)

        for row in records:
            amount = self._amount(row)
            kind = self._kind(row)
            when = self._when(row)

            if kind in INCOME_TYPES:
                totals["income"] += amount
                if kind == "SUBSIDY":
                    subsidies += amount
                month_sign = -1.0
            else:
                totals["cost"] += amount
                if kind == "CAPEX":
                    capex_gross += amount
                month_sign = 1.0

            if when is not None:
                monthly_net[f"{when.year:04d}-{when.month:02d}"] += amount * month_sign

            if kind == "EXPORT":
                totals["export"] += amount
            if kind == "SHARING":
                totals["sharing"] += amount
            if kind in {"SERVICE", "REPAIR", "REVISION"}:
                totals["service"] += amount

        net_capex = capex_gross - subsidies
        opportunity_rate = float(self.app.config.get("finance.settings.opportunity_cost_rate", 0.04) or 0.0)
        opportunity_cost = net_capex * opportunity_rate

        return {
            "available": bool(self.app.config.get("finance.enabled", False)),
            "year": year,
            "currency": self.app.config.get("finance.settings.default_currency", "CZK"),
            "kpi": {
                "energy_costs_ytd": round(totals["cost"], 2),
                "energy_income_ytd": round(totals["income"], 2),
                "net_costs_ytd": round(totals["cost"] - totals["income"], 2),
                "last_12m_costs": round(totals["cost"], 2),
                "fve_revenue": round(totals["export"], 2),
                "sharing_revenue": round(totals["sharing"], 2),
                "service_and_repairs": round(totals["service"], 2),
                "gross_capex": round(capex_gross, 2),
                "subsidies": round(subsidies, 2),
                "net_investment": round(net_capex, 2),
                "simple_payback_years": None,
                "npv": None,
                "irr": None,
                "opportunity_cost": round(opportunity_cost, 2),
            },
            "monthly_net_costs": [
                {"month": month, "amount": round(amount, 2)}
                for month, amount in sorted(monthly_net.items())
            ],
            "audit": {
                "generated_at": to_iso(now),
                "sources": {
                    "finance_transactions": len(records),
                },
                "period": {"from": date(year, 1, 1).isoformat(), "to": to.date().isoformat()},
            },
        }

    def manual_items(self, params: dict[str, str] | None = None) -> dict[str, Any]:
        params = params or {}
        limit_raw = params.get("limit")
        try:
            limit = max(1, min(int(limit_raw), 1000)) if limit_raw else 200
        except (TypeError, ValueError):
            limit = 200

        rows = self.app.storage.last("finance_manual", limit)
        return {
            "available": bool(self.app.config.get("finance.enabled", False)),
            "count": len(rows),
            "items": rows,
            "allowed_types": [
                "CAPEX", "SUBSIDY", "SERVICE", "REPAIR", "REVISION", "INCOME", "OTHER",
            ],
            "audit": {
                "generated_at": to_iso(now_local()),
                "source": "finance_manual",
            },
        }
