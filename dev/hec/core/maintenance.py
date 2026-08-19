"""Údržba na pozadí: denní bilance, cykly spotřebičů, archivace.

Běží v jednom vlákně mimo readery – výpočet nad historií nesmí zdržet čtení
měniče. Chyba údržby nikdy neshodí sběr dat.
"""

from __future__ import annotations

import threading

from ..analysis.appliances import ApplianceAnalyser
from ..analysis.summaries import Summaries
from ..controller.predictor import Predictor
from ..storage.archiver import Archiver
from .logging_setup import error_event, event, get_logger


class Maintenance:
    def __init__(self, config, storage):
        self.config = config
        self.summaries = Summaries(config, storage)
        self.appliances = ApplianceAnalyser(config, storage)
        self.archiver = Archiver(config, storage)
        self.predictor = Predictor(config, storage, self.summaries)
        self.log = get_logger("maintenance")
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def interval_seconds(self) -> int:
        return max(3600, int(self.config.get("storage.archive_check_hours", 24)) * 3600)

    def run_once(self) -> dict:
        result = {"summaries": 0, "cycles": 0, "forecast": 0, "archive": {}}
        for name, action in (("summaries", lambda: len(self.summaries.run_for_missing(7))),
                             ("cycles", lambda: len(self.appliances.run(2))),
                             ("forecast", self._store_forecast),
                             ("archive", self.archiver.run)):
            try:
                result[name] = action()
            except Exception as exc:                      # noqa: BLE001
                error_event(self.log, "maintenance_step_failed", step=name,
                            error=type(exc).__name__)
        event(self.log, "maintenance_done", **{k: v for k, v in result.items() if k != "archive"})
        return result

    def _store_forecast(self) -> int:
        """Predikce se ukládá, aby se dala zpětně porovnat se skutečností."""
        if not self.config.get("prediction.enabled", True):
            return 0
        forecast = self.predictor.forecast()
        if not forecast.get("available"):
            return 0
        self.predictor.store_forecast(forecast)
        return len(forecast["days"])

    def _loop(self) -> None:
        # První běh hned po startu: po výpadku systému se dopočítá, co chybí.
        while not self._stop.is_set():
            self.run_once()
            self._stop.wait(self.interval_seconds())

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="maintenance", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
