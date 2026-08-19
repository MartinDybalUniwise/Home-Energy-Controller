"""Plánovač čtení.

Jedno vlákno na reader. Důvod: čtení GoodWe po 10 s nesmí čekat na pomalou
odpověď tngsmart.cz. Vlákna jsou daemon – proces se ukončí i při zaseknutém
požadavku, o časový limit se stará samotný reader.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from .logging_setup import event, get_logger


class Scheduler:
    def __init__(self, readers, on_sample: Callable | None = None):
        self.readers = list(readers)
        self.on_sample = on_sample
        self.log = get_logger("scheduler")
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    def poll_once(self, reader):
        """Jedno čtení včetně předání vzorku aplikaci. Vrací Sample."""
        sample = reader.poll()
        if self.on_sample is not None:
            try:
                self.on_sample(sample, reader)
            except Exception as exc:                          # noqa: BLE001
                self.log.error("on_sample_failed | reader=%s error=%s", reader.name, exc)
        return sample

    def _run_reader(self, reader) -> None:
        while not self._stop.is_set():
            started = time.monotonic()
            self.poll_once(reader)
            reader.schedule_next(started)
            wait = max(1.0, reader._next_at - time.monotonic())
            self._stop.wait(wait)

    def start(self) -> None:
        for reader in self.readers:
            thread = threading.Thread(target=self._run_reader, args=(reader,),
                                      name=f"reader-{reader.name}", daemon=True)
            thread.start()
            self._threads.append(thread)
            event(self.log, "reader_started", reader=reader.name,
                  interval_s=reader.interval_seconds())

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout=timeout)
        self._threads.clear()

    def run_forever(self) -> None:
        self.start()
        try:
            while not self._stop.is_set():
                self._stop.wait(1.0)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def run_once(self) -> list:
        """Jedno kolo všech readerů – pro `--once`, testy a diagnostiku."""
        return [self.poll_once(reader) for reader in self.readers]
