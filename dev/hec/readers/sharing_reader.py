"""Reader sdílení energie (dev/step09/EXTENSION_PLAN.md, fáze C).

Na rozdíl od ostatních readerů nečte živé API – GoEnergy (sdružení, přes
které se sdílení odbavuje) žádné nevystavuje. Místo toho sleduje lokální
složku (`sharing.import_path`), kam uživatel jednou měsíčně ručně uloží
stažený export vyúčtování (formát: `dev/step09/SHARING_IMPORT_FORMAT.md`).
Readery jen čtou, controller sem nezasahuje – zdroj dat je tu jen soubor
místo HTTP odpovědi.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..core.logging_setup import event
from ..core.model import EnergyInterval, Sample
from ..core.timeutil import to_iso
from ..storage.base import atomic_write_json, read_json
from .base import BaseReader
from .sharing_parser import parse_sharing_export


class SharingReader(BaseReader):
    name = "sharing"

    def __init__(self, config, storage=None, load_workbook=None):
        self.processed: dict[str, str] = {}
        self.latest_settlement: dict | None = None
        self._interval_records: list[dict] = []
        self._new_settlements: list[dict] = []
        self._load_workbook = load_workbook          # injektovatelné kvůli testům
        super().__init__(config, storage)
        self.state_path = Path(config.data_dir) / "sharing_runtime_state.json"
        self._load_state()

    def interval_seconds(self) -> int:
        return int(self.config.get("polling.sharing_hours", 24)) * 3600

    # --- stav (dedup importovaných souborů) ---------------------------------
    def _load_state(self) -> None:
        saved = read_json(self.state_path, {}) or {}
        if isinstance(saved.get("processed_files"), dict):
            self.processed = saved["processed_files"]
        if isinstance(saved.get("latest_settlement"), dict):
            self.latest_settlement = saved["latest_settlement"]

    def _save_state(self) -> None:
        atomic_write_json(self.state_path, {
            "processed_files": self.processed,
            "latest_settlement": self.latest_settlement,
        })

    # --- import --------------------------------------------------------------
    def _import_dir(self) -> Path:
        raw = str(self.config.get("sharing.import_path", "") or "").strip()
        if not raw:
            raise RuntimeError("sharing.import_path není nastaven – "
                               "nastavte složku s měsíčními exporty v Nastavení")
        path = Path(raw)
        if not path.is_absolute():
            path = self.config.root / path
        if not path.is_dir():
            raise RuntimeError(f"sharing.import_path '{path}' neexistuje nebo není složka")
        return path

    @staticmethod
    def _fingerprint(path: Path) -> str:
        stat = path.stat()
        return f"{stat.st_mtime_ns}:{stat.st_size}"

    @staticmethod
    def _to_history_records(payload: dict) -> list[dict]:
        """Intervalová data exportu -> EnergyInterval (dev/step09 kap. 3).

        Pohled exportu je "výrobce": co se skutečně sdílelo komu, soubor
        neříká, proto `shared_received_kwh` zůstává None – jen `shared_sent_kwh`
        (kolik výrobce ze své výroby na sdílení odevzdal) je známé.
        """
        records = []
        for row in payload["intervals"]:
            interval = EnergyInterval(
                timestamp=row["timestamp"], source="sharing",
                ean=row["ean"] or payload["ean"] or "", role="producer",
                production_kwh=row.get("production_kwh"),
                shared_sent_kwh=row.get("shared_kwh"),
            )
            record = interval.to_dict()
            record["sold_kwh"] = row.get("sold_kwh")   # navíc oproti obecnému tvaru – prodáno GoEnergy
            records.append(record)
        return records

    def read(self) -> dict:
        directory = self._import_dir()
        self._interval_records = []
        self._new_settlements = []
        newly_imported: list[str] = []

        for path in sorted(directory.glob("*.xlsx")):
            fingerprint = self._fingerprint(path)
            if self.processed.get(path.name) == fingerprint:
                continue
            try:
                payload = parse_sharing_export(path, load_workbook=self._load_workbook)
            except Exception as exc:                              # noqa: BLE001 – jeden vadný soubor nesmí shodit zbytek
                self.log.warning("sharing_import_failed | file=%s error=%s: %s",
                                 path.name, type(exc).__name__, exc)
                continue

            self._interval_records.extend(self._to_history_records(payload))
            settlement = payload["settlement"]
            settlement["period_from"] = payload["period_from"].isoformat()
            settlement["period_to"] = payload["period_to"].isoformat()
            settlement["source_file"] = path.name
            # "timestamp" = konec zúčtovaného období – JsonlStorage podle něj
            # řadí záznam do denního souboru, ať je dohledatelný podle období,
            # ne podle náhodného okamžiku importu.
            settlement["timestamp"] = to_iso(datetime.combine(payload["period_to"], datetime.min.time()))
            # Poslední zpracovaný soubor podle konce období vyhrává – exporty
            # se mohou dodat i mimo pořadí stažení.
            if (self.latest_settlement is None
                    or settlement["period_to"] >= self.latest_settlement.get("period_to", "")):
                self.latest_settlement = settlement
            self._new_settlements.append(settlement)
            self.processed[path.name] = fingerprint
            newly_imported.append(path.name)
            event(self.log, "sharing_import_ok", file=path.name,
                  intervals=len(payload["intervals"]))

        if newly_imported:
            self._save_state()

        settlement = self.latest_settlement or {}
        return {
            "producer_ean": self.config.get("sharing.producer_ean", "") or settlement.get("ean"),
            "period_from": settlement.get("period_from"),
            "period_to": settlement.get("period_to"),
            "delivered_kwh": settlement.get("delivered_kwh"),
            "shared_kwh": settlement.get("shared_kwh"),
            "sold_kwh": settlement.get("sold_kwh"),
            "deduction_czk": settlement.get("deduction_czk"),
            "invoice_czk": settlement.get("invoice_czk"),
            "imported_files": len(self.processed),
            "newly_imported": newly_imported,
        }

    def history_targets(self, values: dict, sample: Sample) -> list[tuple[str, dict]]:
        # Dva proudy: jemná intervalová data pod "sharing" (stejně jako u
        # ostatních readerů) a jeden souhrnný záznam na naimportovaný měsíc
        # pod "sharing_settlement" – z něj se učí forecast/
        # sharing_consumption_forecast.py (fáze D), aniž by musel znát
        # tenhle reader nebo formát XLSX.
        targets = [(self.name, record) for record in self._interval_records]
        targets.extend((f"{self.name}_settlement", settlement) for settlement in self._new_settlements)
        return targets
