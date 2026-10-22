"""Persistent write-ahead history change set, independent of clean shutdown."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from datetime import date
from pathlib import Path, PurePosixPath

from .base import atomic_write_json

TRACKING_PROTOCOL = 1
_TRACKING_LOCK = threading.RLock()


def history_relative(value: str) -> str:
    path = PurePosixPath(value)
    if (path.is_absolute() or len(path.parts) != 2 or any(p in ('.', '..') for p in path.parts)
            or '\\' in value or ':' in value or not path.name.endswith('.jsonl')):
        raise ValueError('Invalid history path')
    date.fromisoformat(path.name.removesuffix('.jsonl'))
    return path.as_posix()


class HistoryChanges:
    def __init__(self, history_dir: Path):
        self.history_dir = Path(history_dir).absolute()
        self.root = self.history_dir.with_name(self.history_dir.name + '.backup-tracking')
        self.state_path = self.root / 'state.json'

    def state(self) -> dict:
        state = json.loads(self.state_path.read_text(encoding='utf-8'))
        if (state.get('protocol') != TRACKING_PROTOCOL or state.get('history_root') != str(self.history_dir)
                or not isinstance(state.get('valid'), bool) or not state.get('epoch')):
            raise ValueError('History tracking belongs to a different installation/protocol or is invalid')
        return state

    @staticmethod
    def _durable_json(path: Path, payload: dict) -> None:
        atomic_write_json(path, payload)
        with path.open('r+b') as handle:
            os.fsync(handle.fileno())

    def ensure(self) -> dict:
        with _TRACKING_LOCK:
            return self._ensure()

    def _ensure(self) -> dict:
        if self.state_path.exists():
            state = self.state()
            if state.get('protocol') != TRACKING_PROTOCOL or state.get('history_root') != str(self.history_dir):
                raise ValueError('History tracking belongs to a different installation/protocol')
            if state.get('last_writer_pid') != os.getpid():
                state['last_writer_pid'] = os.getpid()
                self._durable_json(self.state_path, state)
            return state
        self.root.mkdir(parents=True, exist_ok=True)
        state = {'protocol': TRACKING_PROTOCOL, 'epoch': uuid.uuid4().hex,
                 'history_root': str(self.history_dir), 'valid': True, 'last_writer_pid': os.getpid()}
        self._durable_json(self.state_path, state)
        return state

    def mark(self, path: Path, *, deleted: bool = False) -> None:
        relative = history_relative(Path(path).absolute().relative_to(self.history_dir).as_posix())
        self.ensure()
        target = self.root / 'dirty' / (hashlib.sha256(relative.encode()).hexdigest() + '.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        if deleted:
            self._durable_json(target, {'path': relative, 'deleted': True})
            return
        # The complete marker is durable before any history mutation. A partial
        # marker after interruption fails closed at backup; it cannot hide a change.
        try:
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return
        with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
            json.dump({'path': relative, 'deleted': False}, handle)
            handle.flush()
            os.fsync(handle.fileno())

    def pending(self) -> list[tuple[Path, str]]:
        result = []
        for marker in sorted((self.root / 'dirty').glob('*.json')):
            relative = history_relative(json.loads(marker.read_text(encoding='utf-8'))['path'])
            expected = hashlib.sha256(relative.encode()).hexdigest() + '.json'
            if marker.name != expected:
                raise ValueError('Invalid dirty marker')
            result.append((marker, relative))
        return result

    def invalidate(self, reason: str) -> None:
        state = self.ensure()
        state.update(valid=False, reason=reason)
        self._durable_json(self.state_path, state)
