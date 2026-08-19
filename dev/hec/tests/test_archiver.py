"""Testy archivace. Klíčové pravidlo: lokální data se mažou až po ověřené kopii."""

from __future__ import annotations

import gzip
from datetime import timedelta

from hec.core import config as config_mod
from hec.core import schema
from hec.core.timeutil import now_local, to_iso
from hec.storage.archiver import Archiver
from hec.storage.jsonl import JsonlStorage


def make(tmp_path, archive="archive", days=30, compress=True):
    data = schema.defaults()
    data["storage"]["archive_path"] = str(tmp_path / archive) if archive else ""
    data["storage"]["archive_after_days"] = days
    data["storage"]["compress_archive"] = compress
    config = config_mod.Config(data, path=tmp_path / "c.json", root=tmp_path)
    config.ensure_dirs()
    storage = JsonlStorage(config.data_dir, config.history_dir)
    return config, storage


def seed(storage, days_ago, source="goodwe"):
    stamp = now_local() - timedelta(days=days_ago)
    storage.append(source, {"timestamp": to_iso(stamp), "source": source, "pv_w": 1000})
    return storage.history_dir / source / f"{stamp:%Y-%m-%d}.jsonl"


def test_disabled_when_no_archive_path(tmp_path):
    config, storage = make(tmp_path, archive="")
    seed(storage, 40)

    result = Archiver(config, storage).run()
    assert result == {"enabled": False, "archived": 0, "failed": 0}


def test_only_files_older_than_the_limit_are_archived(tmp_path):
    config, storage = make(tmp_path, days=30)
    old = seed(storage, 40)
    fresh = seed(storage, 5)

    archiver = Archiver(config, storage)
    assert archiver.candidates() == [old]

    archiver.run()
    assert not old.exists()
    assert fresh.exists()


def test_archived_file_is_compressed_and_identical(tmp_path):
    config, storage = make(tmp_path)
    old = seed(storage, 40)
    original = old.read_bytes()

    Archiver(config, storage).run()

    target = config.archive_dir / "goodwe" / f"{old.stem}.jsonl.gz"
    assert gzip.decompress(target.read_bytes()) == original


def test_uncompressed_archive_is_supported(tmp_path):
    config, storage = make(tmp_path, compress=False)
    old = seed(storage, 40)
    original = old.read_bytes()

    Archiver(config, storage).run()
    assert (config.archive_dir / "goodwe" / f"{old.stem}.jsonl").read_bytes() == original


def test_unavailable_nas_never_deletes_local_data(tmp_path, monkeypatch):
    """Odpojený NAS je běžný stav, ne důvod ke ztrátě historie."""
    config, storage = make(tmp_path)
    old = seed(storage, 40)

    def refuse(*args, **kwargs):
        raise OSError("network share unavailable")

    monkeypatch.setattr("hec.storage.archiver.gzip.open", refuse)
    result = Archiver(config, storage).run()

    assert result["failed"] == 1 and result["archived"] == 0
    assert old.exists()


def test_failed_verification_keeps_local_file_and_removes_bad_copy(tmp_path, monkeypatch):
    config, storage = make(tmp_path)
    old = seed(storage, 40)
    # Simulace poškozeného přenosu: kopie má jiný otisk než zdroj.
    digests = iter(["zdroj", "poskozena-kopie"])
    monkeypatch.setattr("hec.storage.archiver.sha256", lambda data: next(digests))

    assert Archiver(config, storage).archive_file(old) is False
    assert old.exists()
    assert not (config.archive_dir / "goodwe" / f"{old.stem}.jsonl.gz").exists()


def test_retry_succeeds_after_the_share_comes_back(tmp_path, monkeypatch):
    config, storage = make(tmp_path)
    old = seed(storage, 40)
    archiver = Archiver(config, storage)

    monkeypatch.setattr("hec.storage.archiver.gzip.open",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))
    archiver.run()
    assert old.exists()

    monkeypatch.undo()
    assert archiver.run()["archived"] == 1
    assert not old.exists()
