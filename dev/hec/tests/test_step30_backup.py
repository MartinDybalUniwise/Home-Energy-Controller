"""Incremental correctness, zero cold-history I/O, crash retry and actual restore."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from hec.storage.backup_tracking import HistoryChanges
from hec.storage.history import merge_history
from hec.storage.jsonl import JsonlStorage
from hec.tools import release_backup as module
from hec.tools.release_backup import ReleaseBackups


@pytest.fixture(scope='module')
def code_repository(tmp_path_factory):
    root = tmp_path_factory.mktemp('backup-code')
    (root / 'dev/hec/storage').mkdir(parents=True)
    (root / 'dev/hec/storage/backup_tracking.py').write_text('TRACKING_PROTOCOL = 1\n')
    (root / 'app.py').write_text('print("fixture")\n')
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', 'add', '--', 'app.py', 'dev/hec/storage/backup_tracking.py'], cwd=root, check=True)
    subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test',
                    'commit', '-qm', 'fixture'], cwd=root, check=True)
    return root


@pytest.fixture
def backed_up(tmp_path, code_repository):
    root = tmp_path / 'installation'
    root.mkdir()
    (root / 'dev/hec/config').mkdir(parents=True)
    (root / 'dev/hec/storage').mkdir(parents=True)
    (root / 'dev/hec/storage/backup_tracking.py').write_text('TRACKING_PROTOCOL = 1\n')
    (root / 'app.py').write_text('print("fixture")\n')
    config = {'storage': {'data_path': 'data', 'history_path': 'history', 'logs_path': 'logs', 'archive_path': ''},
              'web': {'port': 8189}}
    (root / 'dev/hec/config/config.json').write_text(json.dumps(config))
    (root / '.env').write_text('PRIVATE_FIXTURE=not-real\n')
    (root / 'logs').mkdir()
    (root / 'logs/old.log').write_text('do not copy')
    os.utime(root / 'logs/old.log', (1, 1))
    (root / 'logs/recent.log').write_text('recent fixture')
    shutil.copytree(code_repository / '.git', root / '.git')
    storage = JsonlStorage(root / 'data', root / 'history')
    old = storage.append('tng', {'timestamp': '2026-08-01T10:00:00+02:00', 'value': 1})
    baseline = tmp_path / 'verified-baseline'
    (baseline / 'files/history/tng').mkdir(parents=True)
    data = old.read_bytes()
    (baseline / 'files/history/tng/2026-08-01.jsonl').write_bytes(data)
    manifest = {'history/tng/2026-08-01.jsonl': {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}}
    (baseline / 'manifest.json').write_text(json.dumps(manifest))
    (baseline / 'verified.json').write_text(json.dumps({'files': 1, 'bytes': len(data)}))
    backups = ReleaseBackups(root, tmp_path / 'vault')
    registration = backups.register(baseline)
    assert registration['copied_bytes'] == registration['history_bytes_read'] == 0
    return backups, storage, baseline


def test_registration_never_reads_baseline_payloads(backed_up, monkeypatch):
    backups, _, baseline = backed_up
    original = Path.open

    def reject_payload(path, *args, **kwargs):
        if path.is_relative_to(baseline / 'files'):
            pytest.fail('Registration opened immutable baseline payload')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', reject_payload)
    other = ReleaseBackups(backups.source, backups.vault.with_name('another-vault'))
    assert other.register(baseline)['history_bytes_read'] == 0


def test_repeat_backup_does_not_enumerate_or_read_unchanged_history(backed_up, monkeypatch):
    backups, storage, _ = backed_up
    first = backups.capture(bootstrap=True)
    assert first['history_files_read'] == 1
    original_open, original_glob = Path.open, Path.glob

    def guard_open(path, *args, **kwargs):
        if path.is_relative_to(storage.history_dir):
            pytest.fail('Routine release read unchanged history')
        return original_open(path, *args, **kwargs)

    def guard_glob(path, *args, **kwargs):
        if path.is_relative_to(storage.history_dir):
            pytest.fail('Routine release enumerated history')
        return original_glob(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', guard_open)
    monkeypatch.setattr(Path, 'glob', guard_glob)
    original_run = subprocess.run

    def guard_git(command, *args, **kwargs):
        if command[:2] in (['git', 'archive'], ['git', 'bundle']):
            pytest.fail('Recreated unchanged code artifact')
        return original_run(command, *args, **kwargs)

    monkeypatch.setattr(subprocess, 'run', guard_git)
    repeated = backups.capture()
    assert repeated['history_bytes_read'] == repeated['history_files_read'] == repeated['copied_bytes'] == 0


def test_old_day_correction_new_day_and_full_restore(backed_up, tmp_path):
    backups, storage, _ = backed_up
    backups.capture(bootstrap=True)
    merge_history(storage, 'tng', [{'timestamp': '2026-08-01T10:00:00+02:00', 'value': 7}])
    storage.append('tng', {'timestamp': '2026-10-21T10:00:00+02:00', 'value': 9})
    result = backups.capture()
    assert result['history_files_read'] == 2
    expected_bytes = sum((storage.history_dir / 'tng' / (day + '.jsonl')).stat().st_size
                         for day in ('2026-08-01', '2026-10-21'))
    assert result['history_bytes_read'] == 2 * expected_bytes
    target = tmp_path / 'restored'
    backups.restore(target)
    assert (target / 'app.py').read_text() == 'print("fixture")\n'
    assert (target / '.env').read_text() == 'PRIVATE_FIXTURE=not-real\n'
    for day in ('2026-08-01', '2026-10-21'):
        assert (target / f'history/tng/{day}.jsonl').read_bytes() == (storage.history_dir / f'tng/{day}.jsonl').read_bytes()
    assert not (target / 'logs/old.log').exists()
    assert (target / 'logs/recent.log').read_text() == 'recent fixture'
    assert HistoryChanges(target / 'history').state()['valid'] is False
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=target, text=True).strip() == backups._snapshot()['revision']


def test_bootstrap_rebinds_restored_tracking_after_directory_move(backed_up, tmp_path):
    backups, _, baseline = backed_up
    backups.capture(bootstrap=True)
    restored = tmp_path / 'staging'
    backups.restore(restored)
    installed = tmp_path / 'new-installation'
    restored.rename(installed)
    rebound = ReleaseBackups(installed, tmp_path / 'new-vault')
    rebound.register(baseline)
    rebound.capture(bootstrap=True)
    assert rebound.capture()['history_files_read'] == 0


def test_delete_marker_prevents_resurrecting_deleted_history(backed_up, tmp_path):
    backups, storage, _ = backed_up
    backups.capture(bootstrap=True)
    path = storage.history_dir / 'tng/2026-08-01.jsonl'
    storage.history_changes.mark(path)
    path.unlink()
    assert backups.capture()['history_deleted'] == 1
    backups.restore(tmp_path / 'deleted-restore')
    assert not (tmp_path / 'deleted-restore/history/tng/2026-08-01.jsonl').exists()


def test_publish_failure_retains_head_and_dirty_paths(backed_up, monkeypatch):
    backups, storage, _ = backed_up
    backups.capture(bootstrap=True)
    head = (backups.vault / 'HEAD.json').read_bytes()
    storage.append('tng', {'timestamp': '2026-08-01T11:00:00+02:00', 'value': 2})
    real = backups._publish
    monkeypatch.setattr(backups, '_publish', lambda _: (_ for _ in ()).throw(OSError('interrupted')))
    with pytest.raises(OSError):
        backups.capture()
    assert (backups.vault / 'HEAD.json').read_bytes() == head
    assert storage.history_changes.pending()
    monkeypatch.setattr(backups, '_publish', real)
    assert backups.capture()['history_files_read'] == 1
    assert not storage.history_changes.pending()


def test_interrupted_ack_can_retry_without_payload_copy(backed_up, monkeypatch):
    backups, storage, _ = backed_up
    backups.capture(bootstrap=True)
    storage.append('tng', {'timestamp': '2026-08-01T11:00:00+02:00', 'value': 2})
    original = Path.unlink

    def interrupted(path, *args, **kwargs):
        if path.parent.name == 'dirty':
            raise OSError('interrupted marker acknowledgement')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'unlink', interrupted)
    with pytest.raises(OSError):
        backups.capture()
    monkeypatch.setattr(Path, 'unlink', original)
    assert backups.capture()['copied_bytes'] == 0


@pytest.mark.parametrize('problem', ['missing_state', 'invalidated', 'missing_writer', 'corrupt_marker'])
def test_tracking_gap_never_falls_back_to_full_history_scan(backed_up, monkeypatch, problem):
    backups, storage, _ = backed_up
    backups.capture(bootstrap=True)
    if problem == 'missing_state':
        storage.history_changes.state_path.unlink()
    elif problem == 'invalidated':
        storage.history_changes.invalidate('untracked rollback')
    elif problem == 'missing_writer':
        (backups.source / 'dev/hec/storage/backup_tracking.py').unlink()
    else:
        storage.append('tng', {'timestamp': '2026-10-21T10:00:00+02:00'})
        storage.history_changes.pending()[0][0].write_text('{')
    original = Path.glob

    def guard(path, *args, **kwargs):
        if path == storage.history_dir:
            pytest.fail('Silent full history fallback')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'glob', guard)
    with pytest.raises((ValueError, FileNotFoundError)):
        backups.capture()


@pytest.mark.parametrize('problem', ['missing_baseline', 'corrupt_object', 'existing_target', 'escape_target'])
def test_restore_rejects_broken_dependencies_or_unsafe_destination(backed_up, tmp_path, problem):
    backups, _, baseline = backed_up
    backups.capture(bootstrap=True)
    target = tmp_path / 'restore'
    if problem == 'missing_baseline':
        (baseline / 'files/history/tng/2026-08-01.jsonl').unlink()
    elif problem == 'corrupt_object':
        ref = backups._snapshot()['files']['@code']
        backups._payload(ref, backups._snapshot()).write_bytes(b'corrupt')
    elif problem == 'existing_target':
        target.mkdir()
        (target / 'keep.txt').write_text('keep')
    else:
        target = backups.source / 'unsafe'
    with pytest.raises(ValueError):
        backups.restore(target)
    if problem == 'existing_target':
        assert (target / 'keep.txt').read_text() == 'keep'


def test_mark_failure_happens_before_source_mutation(tmp_path, monkeypatch):
    storage = JsonlStorage(tmp_path / 'data', tmp_path / 'history')
    monkeypatch.setattr(storage.history_changes, 'mark', lambda _: (_ for _ in ()).throw(OSError('journal unavailable')))
    with pytest.raises(OSError):
        storage.append('tng', {'timestamp': '2026-08-01T10:00:00+02:00'})
    assert not (storage.history_dir / 'tng/2026-08-01.jsonl').exists()


def test_external_archive_mode_is_explicitly_rejected(backed_up):
    backups, _, _ = backed_up
    path = backups.source / 'dev/hec/config/config.json'
    config = json.loads(path.read_text())
    config['storage']['archive_path'] = 'archive'
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match='External archive'):
        backups.capture(bootstrap=True)


def test_frozen_folder_is_rejected_without_entering_it(tmp_path, monkeypatch):
    frozen = tmp_path / 'odlozene-logy'
    original = Path.is_symlink

    def guard(path):
        if path == frozen:
            pytest.fail('Touched frozen folder before lexical rejection')
        return original(path)

    monkeypatch.setattr(Path, 'is_symlink', guard)
    with pytest.raises(ValueError, match='Frozen'):
        ReleaseBackups(frozen, tmp_path / 'vault')


def test_cli_refuses_running_writer(backed_up):
    backups, _, _ = backed_up
    with pytest.raises(ValueError, match='still running'):
        module.main(['capture', '--root', str(backups.source), '--vault', str(backups.vault),
                     '--stopped-pid', str(os.getpid()), '--bootstrap'])


def test_marker_survives_failed_first_append_without_blocking_backup(backed_up):
    backups, storage, _ = backed_up
    backups.capture(bootstrap=True)
    storage.history_changes.mark(storage.history_dir / 'tng/2026-10-22.jsonl')
    assert backups.capture()['uncreated_days'] == 1
    assert not storage.history_changes.pending()


def test_unbacked_deletion_is_not_mistaken_for_failed_first_append(backed_up):
    backups, storage, _ = backed_up
    backups.capture(bootstrap=True)
    path = storage.append('tng', {'timestamp': '2026-10-22T10:00:00+02:00'})
    storage.history_changes.mark(path, deleted=True)
    path.unlink()
    with pytest.raises(ValueError, match='Unbacked history'):
        backups.capture()


def test_cli_offline_check_rejects_wrong_pid_when_api_still_responds(backed_up, monkeypatch):
    backups, _, _ = backed_up
    monkeypatch.setattr(module, 'process_running', lambda _: False)
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
    monkeypatch.setattr(module, 'urlopen', lambda *_args, **_kwargs: Response())
    with pytest.raises(ValueError, match='API still responds'):
        backups.require_offline(1234)


def test_reference_path_traversal_rejected(backed_up):
    backups, _, _ = backed_up
    (backups.vault / 'HEAD.json').write_text(json.dumps({'snapshot': '../../unsafe'}))
    with pytest.raises(ValueError, match='identifier'):
        backups._snapshot()


def test_explicit_unlock_only_releases_a_dead_backup_owner(backed_up, monkeypatch):
    backups, _, _ = backed_up
    lock = backups.vault / '.lock'
    lock.write_text(str(os.getpid()))
    with pytest.raises(ValueError, match='still running'):
        backups.unlock()
    monkeypatch.setattr(module, 'process_running', lambda _: False)
    assert backups.unlock() == {'unlocked': True}
    assert not lock.exists()


def test_current_data_walk_prunes_frozen_folder_before_entry(backed_up, monkeypatch):
    backups, storage, _ = backed_up
    frozen = storage.data_dir / 'odlozene-logy'
    frozen.mkdir(parents=True)
    (frozen / 'never-read.log').write_text('fixture')
    original = os.scandir

    def guard(path):
        # POSIX tempfile cleanup also calls scandir with a directory descriptor.
        if not isinstance(path, int) and Path(path) == frozen:
            pytest.fail('Entered frozen folder')
        return original(path)

    monkeypatch.setattr(os, 'scandir', guard)
    for forbidden in (frozen, str(frozen)):
        with pytest.raises(pytest.fail.Exception, match='Entered frozen folder'):
            guard(forbidden)
    backups.capture(bootstrap=True)
    assert not any('odlozene-logy' in name for name in backups._snapshot()['files'])


def test_offline_check_accepts_real_closed_loopback_port(tmp_path, monkeypatch):
    import socket

    source = tmp_path / 'source'
    config = source / 'dev/hec/config/config.json'
    config.parent.mkdir(parents=True)
    monkeypatch.setattr(module, 'process_running', lambda _: False)
    # Reserve the port without listening: no other test can become its owner.
    with socket.socket() as reserved:
        reserved.bind(('127.0.0.1', 0))
        config.write_text(json.dumps({'web': {'port': reserved.getsockname()[1]}}))
        ReleaseBackups(source, tmp_path / 'vault').require_offline(1234)


@pytest.mark.parametrize('reason', [TimeoutError('ambiguous timeout'), OSError('ambiguous failure')])
def test_offline_check_keeps_rejecting_inconclusive_connection_failures(tmp_path, monkeypatch, reason):
    from urllib.error import URLError

    source = tmp_path / 'source'
    config = source / 'dev/hec/config/config.json'
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({'web': {'port': 8080}}))
    monkeypatch.setattr(module, 'process_running', lambda _: False)

    def inconclusive(*_args, **_kwargs):
        raise URLError(reason)

    monkeypatch.setattr(module, 'urlopen', inconclusive)
    with pytest.raises(ValueError, match='Cannot establish'):
        ReleaseBackups(source, tmp_path / 'vault').require_offline(1234)
