"""Reference snapshots: immutable verified baseline plus changed payloads only.

No routine history traversal. Call capture only with every writer process stopped.
Restore is explicit and always targets a new, empty staging directory.
"""
from __future__ import annotations

import argparse
import contextlib
import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from ..storage.backup_tracking import TRACKING_PROTOCOL, HistoryChanges, history_relative

FROZEN_NAME = 'odlozene-logy'


def safe_relative(value: str) -> str:
    path = PurePosixPath(value)
    if (not value or not path.parts or path.is_absolute() or '..' in path.parts or '\\' in value or ':' in value
            or any(part.casefold() == FROZEN_NAME for part in path.parts)):
        raise ValueError('Unsafe backup path')
    return path.as_posix()


def safe_root(path: Path) -> Path:
    path = Path(os.path.abspath(path))
    # Reject the frozen directory lexically, before resolving or entering it.
    if any(part.casefold() == FROZEN_NAME for part in path.parts):
        raise ValueError('Frozen logs must not be accessed')
    for ancestor in [path, *path.parents]:
        if ancestor.is_symlink() or (hasattr(ancestor, 'is_junction') and ancestor.is_junction()):
            raise ValueError('Linked backup paths are unsupported')
    return path


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as handle:
            json.dump(payload, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def file_digest(path: Path, *, jsonl: bool = False) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as handle:
        blocks = iter(handle.readline, b'') if jsonl else iter(lambda: handle.read(1024 * 1024), b'')
        for block in blocks:
            digest.update(block)
            size += len(block)
            if jsonl and block.strip() and not isinstance(json.loads(block), dict):
                raise ValueError('History requires JSON objects')
    return digest.hexdigest(), size


def process_running(pid: int) -> bool:
    if pid <= 0:
        raise ValueError('Expected a positive writer PID')
    if os.name == 'nt':
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            error = ctypes.get_last_error()
            if error == 87:  # ERROR_INVALID_PARAMETER: no such process.
                return False
            raise OSError(error, 'Cannot verify stopped writer')
        try:
            code = ctypes.c_ulong()
            if not kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code)):
                raise OSError('Cannot inspect writer process')
            return code.value == 259
        finally:
            kernel.CloseHandle(ctypes.c_void_p(handle))
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


class ReleaseBackups:
    def __init__(self, source: Path, vault: Path):
        self.source = safe_root(source)
        self.vault = safe_root(vault)
        if self.vault.is_relative_to(self.source) or self.source.is_relative_to(self.vault):
            raise ValueError('Backup store must be separate from the installation')
        self.tracking = HistoryChanges(self.source / 'history')

    def require_offline(self, stopped_pid: int | None, *, bootstrap: bool = False) -> None:
        if stopped_pid is None or process_running(stopped_pid):
            raise ValueError('Writer PID is missing or still running; no backup/invalidation performed')
        if self.tracking.state_path.exists():
            try:
                owner = load_json(self.tracking.state_path).get('last_writer_pid')
            except (ValueError, TypeError):
                if not bootstrap:
                    raise
                owner = None
            if owner is not None and process_running(owner):
                raise ValueError('Tracked history writer is still running')
        config = load_json(self.source / 'dev/hec/config/config.json')
        port = int(config.get('web', {}).get('port', 8080))
        try:
            with urlopen(f'http://127.0.0.1:{port}/api/status', timeout=2):
                pass
        except HTTPError as exc:
            raise ValueError('Configured API port still responds; writers are not proven stopped') from exc
        except URLError as exc:
            if not isinstance(exc.reason, ConnectionRefusedError):
                raise ValueError('Cannot establish that the configured API is offline') from exc
        except TimeoutError as exc:
            raise ValueError('Cannot establish that the configured API is offline') from exc
        else:
            raise ValueError('Configured API still responds; writers are not stopped')

    @contextlib.contextmanager
    def locked(self):
        self.vault.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = self.vault / '.lock'
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(descriptor, 'w') as handle:
                handle.write(str(os.getpid()))
            yield
        finally:
            lock.unlink()

    def _snapshot(self, identifier: str | None = None) -> dict:
        identifier = identifier or load_json(self.vault / 'HEAD.json')['snapshot']
        if not re.fullmatch(r'[a-f0-9]{32}', identifier):
            raise ValueError('Invalid snapshot identifier')
        snapshot = load_json(self.vault / 'snapshots' / (identifier + '.json'))
        if snapshot['source_root'] != str(self.source):
            raise ValueError('Snapshot belongs to another installation')
        return snapshot

    def unlock(self) -> dict:
        lock = self.vault / '.lock'
        content = lock.read_text(encoding='utf-8')
        if process_running(int(content)):
            raise ValueError('Backup lock owner is still running')
        if lock.read_text(encoding='utf-8') != content:
            raise ValueError('Backup lock changed during verification')
        lock.unlink()
        return {'unlocked': True}

    def _publish(self, snapshot: dict) -> None:
        atomic_json(self.vault / 'snapshots' / (snapshot['id'] + '.json'), snapshot)
        atomic_json(self.vault / 'HEAD.json', {'snapshot': snapshot['id']})

    def register(self, baseline: Path) -> dict:
        """Register the existing verified backup using metadata only, never payloads."""
        baseline = safe_root(baseline)
        if baseline.is_relative_to(self.source) or baseline.is_relative_to(self.vault):
            raise ValueError('Verified baseline must remain outside source and incremental store')
        with self.locked():
            if (self.vault / 'HEAD.json').exists():
                raise ValueError('A baseline is already registered')
            verified = load_json(baseline / 'verified.json')
            original = load_json(baseline / 'manifest.json')
            if (verified.get('files') != len(original)
                    or verified.get('bytes') != sum(row['bytes'] for row in original.values())):
                raise ValueError('Baseline verification totals disagree with manifest')
            files = {}
            for name, row in original.items():
                name = safe_relative(name)
                if not re.fullmatch(r'[a-f0-9]{64}', row['sha256']) or row['bytes'] < 0:
                    raise ValueError('Invalid baseline manifest entry')
                if name.startswith(('history/', 'data/', 'dev/hec/config/')) or name in ('.env', 'connect.json', 'config.json'):
                    files[name] = {'baseline': name, 'sha256': row['sha256'], 'bytes': row['bytes']}
            snapshot = {'id': uuid.uuid4().hex, 'source_root': str(self.source), 'baseline_root': str(baseline),
                        'created_at': datetime.now(UTC).isoformat(), 'ready': False, 'tracking_epoch': None,
                        'files': files, 'registered_verified_bytes': verified['bytes']}
            self._publish(snapshot)
            return {'snapshot': snapshot['id'], 'status': 'registered_requires_initial_audit',
                    'history_files': sum(name.startswith('history/') for name in files),
                    'copied_bytes': 0, 'history_bytes_read': 0}

    def _layout(self) -> None:
        config = load_json(self.source / 'dev/hec/config/config.json')
        storage = config['storage']
        for key, expected in (('data_path', 'data'), ('history_path', 'history'), ('logs_path', 'logs')):
            path = Path(storage[key])
            resolved = safe_root(path if path.is_absolute() else self.source / path)
            if resolved != self.source / expected:
                raise ValueError('External/custom storage requires explicit backup support')
        if storage.get('archive_path'):
            raise ValueError('External archive mode is unsupported; no silent incomplete backup')

    def _payload(self, reference: dict, snapshot: dict) -> Path:
        digest = reference['sha256']
        if not re.fullmatch(r'[a-f0-9]{64}', digest):
            raise ValueError('Invalid payload digest')
        if 'baseline' in reference:
            return safe_root(Path(snapshot['baseline_root']) / 'files' / safe_relative(reference['baseline']))
        if reference.get('object') != digest:
            raise ValueError('Invalid payload reference')
        return safe_root(self.vault / 'objects' / digest[:2] / digest)

    def _store(self, path: Path, previous: dict | None, report: dict, *, history: bool = False) -> dict:
        safe_root(path)
        before = path.stat()
        digest, size = file_digest(path, jsonl=history)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('Source changed while backing up')
        if history:
            report['history_files_read'] += 1
            report['history_bytes_read'] += size
        if previous and previous['sha256'] == digest and previous['bytes'] == size:
            return previous
        target = safe_root(self.vault / 'objects' / digest[:2] / digest)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(digest + '.' + uuid.uuid4().hex + '.part')
            try:
                shutil.copyfile(path, temporary)
                if file_digest(temporary) != (digest, size):
                    raise ValueError('Copied payload verification failed')
                with temporary.open('r+b') as handle:
                    os.fsync(handle.fileno())
                os.replace(temporary, target)
                target.chmod(0o600)
            finally:
                temporary.unlink(missing_ok=True)
            report['copied_bytes'] += size
            report['copied_files'] += 1
        return {'object': digest, 'sha256': digest, 'bytes': size}

    def _current_files(self):
        for relative in ('data', 'dev/hec/config'):
            directory = safe_root(self.source / relative)
            if directory.exists():
                for parent, directories, names in os.walk(directory, followlinks=False):
                    directories[:] = [name for name in directories if name.casefold() != FROZEN_NAME]
                    for name in directories:
                        safe_root(Path(parent) / name)
                    for name in names:
                        path = safe_root(Path(parent) / name)
                        if path.is_file():
                            yield path
        for name in ('.env', 'connect.json', 'config.json'):
            path = self.source / name
            if path.is_file():
                yield path
        logs = safe_root(self.source / 'logs')
        cutoff = datetime.now(UTC).timestamp() - timedelta(days=7).total_seconds()
        if logs.exists():
            for path in logs.iterdir():
                safe_root(path)
                if path.is_file() and path.stat().st_mtime >= cutoff:
                    yield path

    def capture(self, *, bootstrap: bool = False) -> dict:
        """Caller must hold a maintenance window: no source writers may remain."""
        with self.locked():
            self._layout()
            previous = self._snapshot()
            state = ({'protocol': TRACKING_PROTOCOL, 'epoch': uuid.uuid4().hex,
                      'history_root': str(self.tracking.history_dir), 'valid': True,
                      'last_writer_pid': os.getpid()} if bootstrap else self.tracking.state())
            if not bootstrap and (not state['valid'] or not previous['ready']
                                  or previous['tracking_epoch'] != state['epoch']):
                raise ValueError('Tracking gap: explicit stopped-writer bootstrap audit required')
            if not bootstrap and not (self.source / 'dev/hec/storage/backup_tracking.py').is_file():
                raise ValueError('Installed writer lacks history tracking; invalidate before untracked rollback')
            if bootstrap:
                # This is the only history glob, explicitly requested for initial transition/recovery.
                history_paths = []
                history_root = safe_root(self.source / 'history')
                if history_root.exists():
                    for directory in history_root.iterdir():
                        if directory.name.casefold() == FROZEN_NAME:
                            continue
                        safe_root(directory)
                        if directory.is_dir():
                            history_paths.extend(directory.glob('*.jsonl'))
                dirty = list((self.tracking.root / 'dirty').glob('*.json'))
                deleted_paths = set()
            else:
                pending = self.tracking.pending()
                history_paths = [self.source / 'history' / relative for _, relative in pending]
                dirty = [marker for marker, _ in pending]
                deleted_paths = {relative for marker, relative in pending if load_json(marker).get('deleted')}
            files = {name: row for name, row in previous['files'].items() if name.startswith('history/')}
            if bootstrap:
                present = {path.relative_to(self.source).as_posix() for path in history_paths}
                files = {name: row for name, row in files.items() if name in present}
            report = {'initial_audit': bootstrap, 'history_files_read': 0, 'history_bytes_read': 0,
                      'copied_files': 0, 'copied_bytes': 0, 'history_deleted': 0, 'uncreated_days': 0}
            for path in history_paths:
                name = safe_relative(path.relative_to(self.source).as_posix())
                history_relative(path.relative_to(self.source / 'history').as_posix())
                if not path.exists():
                    if name not in files:
                        if path.relative_to(self.source / 'history').as_posix() in deleted_paths:
                            raise ValueError('Unbacked history disappeared; external recovery required')
                        # Write-ahead marking may succeed before the first append fails.
                        report['uncreated_days'] += 1
                        continue
                    del files[name]
                    report['history_deleted'] += 1
                else:
                    files[name] = self._store(path, files.get(name), report, history=True)
            for path in self._current_files():
                name = safe_relative(path.relative_to(self.source).as_posix())
                files[name] = self._store(path, previous['files'].get(name), report)
            # Code/config rollback is captured per release; old runtime data is referenced, not copied.
            subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--'], cwd=self.source, check=True)
            revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.source, text=True).strip()
            if previous.get('revision') == revision and all(key in previous['files'] for key in ('@code', '@git')):
                files.update({key: previous['files'][key] for key in ('@code', '@git')})
            else:
                with tempfile.TemporaryDirectory(prefix='hec-code-') as staging:
                    code = Path(staging) / 'code.tar'
                    subprocess.run(['git', 'archive', '--format=tar', '-o', str(code), revision], cwd=self.source, check=True)
                    files['@code'] = self._store(code, previous['files'].get('@code'), report)
                    bundle = Path(staging) / 'repository.bundle'
                    subprocess.run(['git', 'bundle', 'create', str(bundle), 'HEAD'], cwd=self.source,
                                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                    files['@git'] = self._store(bundle, previous['files'].get('@git'), report)
            snapshot = {'id': uuid.uuid4().hex, 'parent': previous['id'], 'source_root': str(self.source),
                        'baseline_root': previous['baseline_root'], 'created_at': datetime.now(UTC).isoformat(),
                        'ready': True, 'tracking_epoch': state['epoch'], 'revision': revision, 'files': files,
                        'report': report}
            self._publish(snapshot)
            # Publication is atomic and precedes acknowledgement. Interrupted cleanup is harmless.
            if bootstrap:
                atomic_json(self.tracking.state_path, state)
            for marker in dirty:
                marker.unlink(missing_ok=True)
            report.update(snapshot=snapshot['id'], logical_bytes=sum(row['bytes'] for row in files.values()))
            return report

    def restore(self, target: Path, *, snapshot_id: str | None = None) -> dict:
        target = safe_root(target)
        if (target.exists() or target.is_relative_to(self.source) or self.source.is_relative_to(target)
                or target.is_relative_to(self.vault) or self.vault.is_relative_to(target)):
            raise ValueError('Restore requires a new staging directory outside source and backup store')
        with self.locked():
            snapshot = self._snapshot(snapshot_id)
            if not snapshot['ready']:
                raise ValueError('Registered baseline alone is not a current release snapshot')
            for name, reference in snapshot['files'].items():
                if name not in ('@code', '@git'):
                    safe_relative(name)
                if not self._payload(reference, snapshot).is_file():
                    raise ValueError('Missing backup dependency; baseline/object must be retained')
            target.mkdir(parents=True, exist_ok=False, mode=0o700)
            bundle_reference = snapshot['files']['@git']
            bundle = self._payload(bundle_reference, snapshot)
            if file_digest(bundle) != (bundle_reference['sha256'], bundle_reference['bytes']):
                raise ValueError('Corrupt Git backup')
            subprocess.run(['git', 'clone', '--quiet', '--no-checkout', str(bundle), str(target)], check=True,
                           capture_output=True)
            subprocess.run(['git', 'checkout', '--quiet', snapshot['revision']], cwd=target, check=True,
                           capture_output=True)
            subprocess.run(['git', 'remote', 'remove', 'origin'], cwd=target, check=True)
            code_reference = snapshot['files']['@code']
            code = self._payload(code_reference, snapshot)
            if file_digest(code) != (code_reference['sha256'], code_reference['bytes']):
                raise ValueError('Corrupt code backup')
            with tarfile.open(code) as archive:
                for member in archive:
                    destination = target / safe_relative(member.name)
                    if member.isdir():
                        destination.mkdir(parents=True, exist_ok=True)
                    elif member.isfile():
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        with archive.extractfile(member) as src, destination.open('wb') as dst:
                            shutil.copyfileobj(src, dst)
                        destination.chmod(member.mode & 0o777)
                    else:
                        raise ValueError('Linked/special code archive member unsupported')
            for name, reference in snapshot['files'].items():
                if name in ('@code', '@git'):
                    continue
                destination = target / safe_relative(name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self._payload(reference, snapshot), destination)
                if file_digest(destination) != (reference['sha256'], reference['bytes']):
                    raise ValueError('Restored payload verification failed')
            # A restore/rollback creates a new coverage boundary; never reuse live dirty state blindly.
            HistoryChanges(target / 'history').invalidate('restored snapshot: bind via explicit bootstrap before next capture')
            return {'snapshot': snapshot['id'], 'restored_to': str(target), 'files': len(snapshot['files'])}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('register', 'capture', 'restore', 'invalidate', 'unlock'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--vault', type=Path, required=True)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--bootstrap', action='store_true', help='Explicit one-time audit; never implicit')
    parser.add_argument('--stopped-pid', type=int, help='Actual production writer PID verified/stopped by release procedure')
    parser.add_argument('--target', type=Path)
    parser.add_argument('--snapshot')
    args = parser.parse_args(argv)
    backups = ReleaseBackups(args.root, args.vault)
    if args.action in ('capture', 'invalidate'):
        backups.require_offline(args.stopped_pid, bootstrap=args.bootstrap)
    if args.action == 'register':
        if args.baseline is None:
            parser.error('--baseline is required')
        result = backups.register(args.baseline)
    elif args.action == 'capture':
        result = backups.capture(bootstrap=args.bootstrap)
    elif args.action == 'restore':
        if args.target is None:
            parser.error('--target is required')
        result = backups.restore(args.target, snapshot_id=args.snapshot)
    elif args.action == 'invalidate':
        backups.tracking.invalidate('explicit untracked writer/rollback transition')
        result = {'tracking': 'invalidated_requires_bootstrap'}
    else:
        result = backups.unlock()
    print(json.dumps(result, indent=2))
    return 0
