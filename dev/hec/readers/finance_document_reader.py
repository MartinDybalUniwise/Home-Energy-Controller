"""Import dokumentů do HEF (Home Energy Finance).

Reader běží odděleně od provozního controlleru. Sleduje složku inbox, dělá
základní klasifikaci podle názvu souboru, ukládá auditní stopu a přesouvá
zpracované soubory do archivu.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from ..core.model import Sample
from ..core.timeutil import now_local, to_iso
from ..storage.base import atomic_write_json, read_json
from .base import BaseReader

SUPPORTED_EXTENSIONS = {".pdf", ".xls", ".xlsx", ".csv"}
ARCHIVE_CATEGORIES = ("electricity", "gas", "water", "export", "sharing", "service", "other")
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "electricity": ("electric", "elekt", "ote", "ean"),
    "gas": ("gas", "plyn"),
    "water": ("water", "voda", "vodne", "stocne"),
    "export": ("export", "vykup", "pretok"),
    "sharing": ("sharing", "sdil"),
    "service": ("service", "servis", "reviz", "oprava"),
}
NUMBER_RE = re.compile(r"(?<!\d)\d{6,}(?!\d)")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{8})")


@dataclass(frozen=True)
class FileMetadata:
    supplier: str | None = None
    document_number: str | None = None
    issue_date: str | None = None

    def dedup_key(self) -> str | None:
        parts = [self.supplier or "", self.document_number or "", self.issue_date or ""]
        if not any(parts):
            return None
        return "|".join(parts)


class FinanceDocumentReader(BaseReader):
    """Import inboxu HEF bez zásahu do řídicí logiky."""

    name = "finance_document_reader"

    def __init__(self, config, storage=None):
        self.state_path = Path(config.data_dir) / "finance_document_reader_state.json"
        self.processed_hashes: dict[str, dict] = {}
        self.processed_keys: set[str] = set()
        self._imported_records: list[dict] = []
        super().__init__(config, storage)
        self._load_state()

    def interval_seconds(self) -> int:
        return int(self.config.get("polling.finance_document_reader_seconds", 3600))

    def is_enabled(self) -> bool:
        return bool(self.config.get("finance.enabled", False))

    def _load_state(self) -> None:
        saved = read_json(self.state_path, {}) or {}
        hashes = saved.get("processed_hashes")
        keys = saved.get("processed_keys")
        if isinstance(hashes, dict):
            self.processed_hashes = hashes
        if isinstance(keys, list):
            self.processed_keys = {str(value) for value in keys if str(value).strip()}

    def _save_state(self) -> None:
        atomic_write_json(self.state_path, {
            "processed_hashes": self.processed_hashes,
            "processed_keys": sorted(self.processed_keys),
        })

    def _inbox_path(self) -> Path:
        raw = str(self.config.get("finance.documents.inbox_path", "data/finance/inbox") or "").strip()
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = self.config.root / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _ensure_layout(inbox_path: Path) -> tuple[Path, Path, Path]:
        base = inbox_path.parent
        processed = base / "processed"
        error = base / "error"
        archive = base / "archive"
        processed.mkdir(parents=True, exist_ok=True)
        error.mkdir(parents=True, exist_ok=True)
        for category in ARCHIVE_CATEGORIES:
            (archive / category).mkdir(parents=True, exist_ok=True)
        return processed, error, archive

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 64), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _classify(path: Path) -> str:
        probe = path.stem.lower()
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in probe for keyword in keywords):
                return category
        return "other"

    @staticmethod
    def _metadata_from_filename(path: Path) -> FileMetadata:
        stem = path.stem.replace(" ", "_")
        tokens = [token for token in re.split(r"[^a-zA-Z0-9]+", stem) if token]
        supplier = tokens[0].lower() if tokens else None

        number_match = NUMBER_RE.search(stem)
        date_match = DATE_RE.search(stem)

        issue_date = None
        if date_match:
            raw = date_match.group(1)
            if len(raw) == 8:
                issue_date = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
            else:
                issue_date = raw

        return FileMetadata(
            supplier=supplier,
            document_number=number_match.group(0) if number_match else None,
            issue_date=issue_date,
        )

    @staticmethod
    def _unique_target(directory: Path, original_name: str, file_hash: str) -> Path:
        target = directory / original_name
        if not target.exists():
            return target
        return directory / f"{Path(original_name).stem}-{file_hash[:8]}{Path(original_name).suffix}"

    @staticmethod
    def _move_safe(path: Path, directory: Path, file_hash: str) -> Path:
        target = FinanceDocumentReader._unique_target(directory, path.name, file_hash)
        path.replace(target)
        return target

    def read(self) -> dict:
        inbox = self._inbox_path()
        _processed, error_dir, archive_dir = self._ensure_layout(inbox)
        now = now_local()
        newly_imported: list[str] = []
        self._imported_records = []

        documents_enabled = bool(self.config.get("finance.documents.enabled", False))
        if not documents_enabled:
            return {
                "documents_enabled": False,
                "inbox_path": str(inbox),
                "newly_imported": [],
                "processed_documents": len(self.processed_hashes),
            }

        for path in sorted(inbox.iterdir()):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            file_hash = self._sha256(path)
            metadata = self._metadata_from_filename(path)
            dedup_key = metadata.dedup_key()
            if file_hash in self.processed_hashes or (dedup_key and dedup_key in self.processed_keys):
                continue

            category = self._classify(path)
            parser = "filename_classifier_v1"
            parser_version = "0.1"
            try:
                archived = self._move_safe(path, archive_dir / category, file_hash)
            except Exception as exc:  # noqa: BLE001
                # Soubor i chyba se uchovají pro ruční zásah; jeden pád neblokuje inbox.
                if path.exists():
                    self._move_safe(path, error_dir, file_hash)
                self.log.warning("finance_import_failed | file=%s error=%s: %s",
                                 path.name, type(exc).__name__, exc)
                continue

            record = {
                "timestamp": to_iso(now),
                "filename": archived.name,
                "original_path": str(path),
                "archive_path": str(archived),
                "file_hash": file_hash,
                "document_type": category,
                "document_number": metadata.document_number,
                "supplier": metadata.supplier,
                "issue_date": metadata.issue_date,
                "status": "PROCESSED",
                "parser": parser,
                "parser_version": parser_version,
                "error_message": None,
                "processed_at": to_iso(now),
            }
            self._imported_records.append(record)
            self.processed_hashes[file_hash] = {
                "filename": archived.name,
                "document_number": metadata.document_number,
                "supplier": metadata.supplier,
                "issue_date": metadata.issue_date,
                "processed_at": record["processed_at"],
            }
            if dedup_key:
                self.processed_keys.add(dedup_key)
            newly_imported.append(path.name)

        if newly_imported:
            self._save_state()

        return {
            "documents_enabled": True,
            "inbox_path": str(inbox),
            "newly_imported": newly_imported,
            "processed_documents": len(self.processed_hashes),
        }

    def history_targets(self, values: dict, sample: Sample) -> list[tuple[str, dict]]:
        return [("finance_documents", record) for record in self._imported_records]
