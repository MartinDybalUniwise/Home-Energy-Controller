"""Testy scaffoldu finance_document_reader (dev/step10)."""

from __future__ import annotations

from hec.core import config as config_mod
from hec.core import schema
from hec.readers.finance_document_reader import FinanceDocumentReader


def make_config(tmp_path, **finance):
    data = schema.defaults()
    data["finance"]["enabled"] = True
    data["finance"]["documents"].update({
        "enabled": True,
        "inbox_path": "data/finance/inbox",
    })
    for key, value in finance.items():
        if key == "documents" and isinstance(value, dict):
            data["finance"]["documents"].update(value)
        else:
            data["finance"][key] = value
    config = config_mod.Config(data, path=tmp_path / "c.json", root=tmp_path)
    config.ensure_dirs()
    return config


def test_finance_reader_imports_supported_files_and_archives_them(tmp_path):
    config = make_config(tmp_path)
    inbox = tmp_path / "data" / "finance" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    sample_file = inbox / "electricity_2026-08-10_9302448004.pdf"
    sample_file.write_bytes(b"invoice")

    reader = FinanceDocumentReader(config)
    sample = reader.poll()

    assert sample.ok is True
    assert sample.values["newly_imported"] == [sample_file.name]
    assert not sample_file.exists()
    archived = tmp_path / "data" / "finance" / "archive" / "electricity" / sample_file.name
    assert archived.exists()



def test_finance_reader_deduplicates_by_hash_between_runs(tmp_path):
    config = make_config(tmp_path)
    inbox = tmp_path / "data" / "finance" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "gas_2026-08-10_123456.pdf").write_bytes(b"same-content")

    reader = FinanceDocumentReader(config)
    first = reader.read()

    # Stejný dokument znovu ve stejném inboxu -> díky hash deduplikaci se nepřijme.
    (inbox / "gas_2026-08-10_123456_copy.pdf").write_bytes(b"same-content")
    second = reader.read()

    assert first["newly_imported"]
    assert second["newly_imported"] == []



def test_finance_reader_can_keep_running_when_documents_import_is_disabled(tmp_path):
    config = make_config(tmp_path, documents={"enabled": False})
    reader = FinanceDocumentReader(config)

    result = reader.read()
    assert result["documents_enabled"] is False
