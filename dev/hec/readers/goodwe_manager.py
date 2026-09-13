"""Serialized, safety-gated GoodWe communication boundary."""

from __future__ import annotations

import asyncio
import inspect
import os
import random
import threading
import time
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from ..core.goodwe_hardware_authorization import load as load_authorization
from ..core.logging_setup import error_event, event, get_logger
from ..core.timeutil import now_local, to_iso

COMMANDS = {
    "set_export_limit_enabled",
    "set_export_limit_w",
    "set_on_grid_soc_limit_pct",
    "start_battery_charge",
    "start_battery_discharge",
    "stop_battery_control",
}


def _json_safe(value: Any) -> Any:
    """Convert audit payloads to JSON-safe values without hiding type errors."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return _json_safe(value.value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


class GoodWeManager:
    """Own the GoodWe client and serialize all reads and writes."""

    def __init__(self, config, storage=None, client: Any | None = None, *, physical_io: bool = False,
                 test_fake: bool = False):
        self.config = config
        self.storage = storage
        self.log = get_logger("goodwe_manager")
        self.host = str(config.get("goodwe.host", "") or "").strip()
        self.enabled = bool(config.get("goodwe.enabled", False))
        self.client = client
        self.physical_io = bool(physical_io)
        self.test_fake = bool(test_fake)
        self._lock = threading.RLock()
        self._inverter: Any | None = None
        self._last_error: str | None = None
        self._last_read: Any | None = None
        self._last_write: dict[str, Any] | None = None
        self._last_duration_ms: int | None = None
        self._retry_count = 0
        self._connected = False
        self._model: str | None = None
        self._firmware: str | None = None
        self._terminal_status("initialized")

    def _terminal_status(self, state: str, **details: Any) -> None:
        payload = " ".join(f"{key}={value}" for key, value in details.items())
        print(f"[GoodWeManager] state={state} host={self.host} {payload}".rstrip(), flush=True)

    def _resolve_client(self) -> Any:
        if os.environ.get("PYTEST_CURRENT_TEST"):
            if self.client is not None and self.test_fake and getattr(self.client, "hec_test_fake", False):
                return self.client
            raise PermissionError("GoodWe physical I/O is disabled in test mode")
        if self.client is not None:
            return self.client
        if not self.physical_io:
            raise PermissionError("GoodWe physical I/O is disabled")
        try:
            import goodwe
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("GoodWe library is not installed") from exc
        return goodwe.connect

    async def _await(self, value: Any) -> Any:
        if inspect.isawaitable(value):
            return await asyncio.wait_for(value, timeout=float(self.config.get("goodwe.timeout_seconds", 3)))
        return value

    async def _connect_async(self) -> Any:
        factory = self._resolve_client()
        if not callable(factory):
            return factory
        return await self._await(factory(
            host=self.host,
            family=self.config.get("goodwe.family") or None,
            timeout=int(self.config.get("goodwe.timeout_seconds", 3)),
            retries=int(self.config.get("goodwe.retry_count", 3)),
        ))

    async def _read_runtime_async(self) -> dict[str, Any]:
        self._inverter = await self._connect_async()
        self._model = getattr(self._inverter, "model_name", None)
        self._firmware = getattr(self._inverter, "firmware", None)
        reader = getattr(self._inverter, "read_runtime_data", None)
        data = await self._await(reader()) if reader is not None else self._inverter
        if not isinstance(data, dict):
            raise ValueError("GoodWe runtime response is not an object")
        return dict(data)

    @staticmethod
    def _run(coroutine):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        result: list[Any] = []
        failure: list[BaseException] = []

        def runner() -> None:
            try:
                result.append(asyncio.run(coroutine))
            except BaseException as exc:  # pragma: no cover - active-loop edge case
                failure.append(exc)

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join()
        if failure:
            raise failure[0]
        return result[0]

    def read_runtime(self) -> dict[str, Any]:
        with self._lock:
            started = time.monotonic()
            try:
                data = self._run(self._read_runtime_async())
                self._connected = True
                self._last_error = None
                self._last_read = now_local()
                self._last_duration_ms = int((time.monotonic() - started) * 1000)
                event(self.log, "read_ok", duration_ms=self._last_duration_ms, host=self.host, online=True)
                self._terminal_status("read_ok", duration_ms=self._last_duration_ms, online=True)
                return data
            except Exception as exc:  # noqa: BLE001
                self._connected = False
                self._inverter = None
                self._last_error = f"{type(exc).__name__}: {exc}"
                self._last_duration_ms = int((time.monotonic() - started) * 1000)
                error_event(self.log, "read_failed", host=self.host, error=self._last_error)
                self._terminal_status("read_failed", error=self._last_error)
                if isinstance(exc, PermissionError):
                    raise
                raise RuntimeError(self._last_error) from exc

    def _write_gates(self) -> dict[str, bool]:
        authorization = load_authorization(self.config)
        return {
            "controller.enabled": bool(self.config.get("controller.enabled", False)),
            "goodwe.enabled": bool(self.config.get("goodwe.enabled", False)),
            "goodwe.writer_enabled": bool(self.config.get("goodwe.writer_enabled", False)),
            "hardware_authorization": authorization.get("status") == "APPROVED",
            "physical_io": self.physical_io or self.client is not None,
            "verify_after_write": bool(self.config.get("goodwe.verify_after_write", True)),
        }

    def _require_write_gate(self, command: str) -> dict[str, bool]:
        if command not in COMMANDS:
            raise ValueError(f"Unsupported GoodWe command: {command}")
        gates = self._write_gates()
        blocked = [name for name, enabled in gates.items() if not enabled]
        if blocked:
            raise PermissionError(f"GoodWe write blocked by safety gate: {', '.join(blocked)}")
        return gates

    async def _read_setting(self, name: str) -> Any:
        inverter = self._require_inverter()
        reader = getattr(inverter, "read_setting", None)
        if reader is None:
            raise NotImplementedError(f"GoodWe setting read is unsupported: {name}")
        return await self._await(reader(name))

    async def _apply_command(self, command: str, kwargs: dict[str, Any]) -> None:
        inverter = self._require_inverter()
        if command == "set_export_limit_enabled":
            await self._await(inverter.write_setting("grid_export", int(bool(kwargs["value"]))))
        elif command == "set_export_limit_w":
            await self._await(inverter.set_grid_export_limit(int(kwargs["value"])))
        elif command == "set_on_grid_soc_limit_pct":
            value = max(0, min(100, int(kwargs["value"])))
            await self._await(inverter.set_ongrid_battery_dod(100 - value))
        elif command in {"start_battery_charge", "start_battery_discharge"}:
            from goodwe import OperationMode

            await self._await(inverter.set_operation_mode(
                OperationMode.ECO,
                eco_mode_power=int(kwargs["power_pct"]),
                eco_mode_soc=int(kwargs["stop_soc_pct"]),
            ))
        elif command == "stop_battery_control":
            from goodwe import OperationMode

            await self._await(inverter.set_operation_mode(OperationMode.GENERAL))

    async def _read_command_state(self, command: str) -> Any:
        inverter = self._require_inverter()
        if command == "set_export_limit_enabled":
            return bool(await self._read_setting("grid_export"))
        if command == "set_export_limit_w":
            return int(await self._await(inverter.get_grid_export_limit()))
        if command == "set_on_grid_soc_limit_pct":
            return 100 - int(await self._await(inverter.get_ongrid_battery_dod()))
        mode = await self._await(inverter.get_operation_mode())
        return getattr(mode, "name", str(mode))

    def _require_inverter(self) -> Any:
        if self._inverter is None:
            raise RuntimeError("GoodWe inverter is not connected")
        return self._inverter

    def _audit(self, record: dict[str, Any]) -> None:
        if self.storage is not None:
            self.storage.append("goodwe_audit", _json_safe(record))

    def _record_attempt(self, *, command_id: str, command: str, requested: dict[str, Any],
                        gates: dict[str, bool], before: Any, attempt: int,
                        write_result: str, readback: Any, final_status: str,
                        error: str | None = None) -> None:
        self._audit({
            "command_id": command_id,
            "timestamp": to_iso(now_local()),
            "command": command,
            "requested": requested,
            "requested_by": requested.get("requested_by", "controller"),
            "source": requested.get("source", "controller"),
            "safety_gates": gates,
            "before": before,
            "write_result": write_result,
            "readback": readback,
            "attempt": attempt,
            "final_status": final_status,
            "error": error,
        })

    def execute(self, command: str, *, requested_by: str = "controller",
                source: str = "controller", **kwargs: Any) -> dict[str, Any]:
        """Perform a supported write; retry only after evidence of non-application."""
        with self._lock:
            gates = self._require_write_gate(command)
            attempts = int(self.config.get("goodwe.retry_count", 3)) + 1
            command_id = str(uuid4())
            requested = {"command": command, **kwargs, "requested_by": requested_by, "source": source}
            before = self.read_runtime()
            for attempt in range(1, attempts + 1):
                try:
                    self._terminal_status("write_requested", command=command, attempt=attempt)
                    self._run(self._apply_command(command, kwargs))
                    actual = self._run(self._read_command_state(command))
                    expected = self._expected_value(command, kwargs)
                    if actual != expected:
                        second_read = self._run(self._read_command_state(command))
                        if second_read == expected:
                            actual = second_read
                        else:
                            self._record_attempt(command_id=command_id, command=command, requested=requested,
                                                 gates=gates, before=before, attempt=attempt,
                                                 write_result="applied", readback=second_read,
                                                 final_status="readback_mismatch",
                                                 error="read-back mismatch; retry evidence says not applied")
                            if attempt >= attempts:
                                raise RuntimeError(
                                    f"GoodWe read-back mismatch: expected={expected!r} actual={second_read!r}")
                            self._retry_count += 1
                            self._backoff(attempt)
                            continue
                    self._record_attempt(command_id=command_id, command=command, requested=requested,
                                         gates=gates, before=before, attempt=attempt,
                                         write_result="applied", readback=actual, final_status="success")
                    self._last_write = {"command_id": command_id, "command": command,
                                        "requested": requested, "before": before,
                                        "after": {"value": actual}, "success": True,
                                        "attempts": attempt}
                    self._last_duration_ms = 0
                    self._terminal_status("write_ok", command=command, attempts=attempt)
                    return {"command_id": command_id, "requested": requested,
                            "actual": {"value": actual}, "success": True, "attempts": attempt}
                except Exception as exc:  # noqa: BLE001
                    try:
                        evidence = self._run(self._read_command_state(command))
                    except Exception as verify_exc:
                        error = f"ambiguous write state: {type(verify_exc).__name__}: {verify_exc}"
                        self._record_attempt(command_id=command_id, command=command, requested=requested,
                                             gates=gates, before=before, attempt=attempt,
                                             write_result="ambiguous", readback=None,
                                             final_status="ambiguous", error=error)
                        raise RuntimeError(error) from exc
                    expected = self._expected_value(command, kwargs)
                    if evidence == expected:
                        self._record_attempt(command_id=command_id, command=command, requested=requested,
                                             gates=gates, before=before, attempt=attempt,
                                             write_result="applied", readback=evidence,
                                             final_status="success_after_ambiguous")
                        return {"command_id": command_id, "requested": requested,
                                "actual": {"value": evidence}, "success": True,
                                "attempts": attempt}
                    error = f"{type(exc).__name__}: {exc}"
                    self._record_attempt(command_id=command_id, command=command, requested=requested,
                                         gates=gates, before=before, attempt=attempt,
                                         write_result="failed", readback=evidence,
                                         final_status="retrying" if attempt < attempts else "failed",
                                         error=error)
                    if attempt >= attempts:
                        raise RuntimeError(error) from exc
                    self._retry_count += 1
                    self._backoff(attempt)
            raise AssertionError("unreachable")

    def _backoff(self, attempt: int) -> None:
        delay = min(30.0, 0.25 * (2 ** (attempt - 1))) + random.uniform(0.0, 0.25)
        self._terminal_status("write_retry", delay_s=round(delay, 3), attempt=attempt + 1)
        time.sleep(delay)

    @staticmethod
    def _expected_value(command: str, kwargs: dict[str, Any]) -> Any:
        if command == "set_export_limit_enabled":
            return bool(kwargs["value"])
        if command == "set_export_limit_w":
            return int(kwargs["value"])
        if command == "set_on_grid_soc_limit_pct":
            return int(kwargs["value"])
        if command == "stop_battery_control":
            return "GENERAL"
        return "ECO"

    def status_snapshot(self) -> dict[str, Any]:
        authorization = load_authorization(self.config)
        return {
            "enabled": self.enabled,
            "host": self.host,
            "connected": self._connected,
            "last_error": self._last_error,
            "last_read": to_iso(self._last_read) if self._last_read else None,
            "last_write": self._last_write,
            "last_duration_ms": self._last_duration_ms,
            "retry_count": self._retry_count,
            "model": self._model,
            "firmware": self._firmware,
            "writer_enabled": bool(self.config.get("goodwe.writer_enabled", False)),
            "hardware_authorization": authorization,
            "physical_io": self.physical_io,
            "terminal": "GoodWeManager active",
        }
