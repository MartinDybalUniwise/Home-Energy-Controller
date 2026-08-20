"""Modul predikcí (dev/step09/EXTENSION_PLAN.md, kap. 3 a 5, fáze A).

Fáze A definuje jen datový kontrakt každé predikce. Predikční logika (PV,
spotřeba, sdílení) přichází ve fázích B a D a staví na dnešním
`controller/predictor.py` – ten se touto fází nemění.

Readery čtou, controller rozhoduje; forecast/ predikuje z už uložených dat
přes StorageBackend a nikdy sám nesahá na síť ani na TNG.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..core.timeutil import now_local, to_iso

CONFIDENCE_LEVELS = ("low", "medium", "high")


@dataclass
class Forecast:
    """Jednotný tvar každé predikce z forecast/ – hodnota, interval kolem ní,
    slovní jistota, verze modelu a čas výpočtu. Chybějící hodnota je `None`
    ("zatím nevíme"), ne 0 nebo odhad."""

    value: float | None
    range: tuple[float, float] | None = None
    confidence: str = "low"
    model_version: str = "unknown"
    generated_at: datetime = field(default_factory=now_local)

    def __post_init__(self) -> None:
        if self.confidence not in CONFIDENCE_LEVELS:
            raise ValueError(
                f"neplatná jistota '{self.confidence}', očekáváno jedna z {CONFIDENCE_LEVELS}")

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "range": list(self.range) if self.range else None,
            "confidence": self.confidence,
            "model_version": self.model_version,
            "generated_at": to_iso(self.generated_at),
        }
