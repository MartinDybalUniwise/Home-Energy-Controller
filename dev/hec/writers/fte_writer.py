"""Safe GoodWe writer API with idempotent commands and terminal visibility."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..core.logging_setup import error_event, event, get_logger


class FTEWriter:
    """Writer façade that performs safe, auditable GoodWe updates."""

    def __init__(self, config, manager=None):
        self.config = config
        self.log = get_logger("fte_writer")
        self.manager = manager
        self.audit_log: list[dict[str, Any]] = []
        self._terminal_status("initialized")

    def _terminal_status(self, state: str, **details: Any) -> None:
        payload = " ".join(f"{key}={value}" for key, value in details.items())
        print(f"[FTEWriter] state={state} {payload}".rstrip(), flush=True)

    def status_snapshot(self) -> dict[str, Any]:
        manager_status = self.manager.status_snapshot() if self.manager is not None else {}
        return {
            "enabled": bool(self.config.get("goodwe.writer_enabled", False)),
            "hardware_authorization": manager_status.get("hardware_authorization", {
                "status": "NOT_AUTHORIZED",
            }),
            "last_write": manager_status.get("last_write"),
            "last_error": manager_status.get("last_error"),
            "retry_count": manager_status.get("retry_count", 0),
            "audit_count": len(self.audit_log),
            "terminal": "FTEWriter active",
        }

    def _record(self, *, command: str, requested: Any, before: Any, after: Any, success: bool,
                attempts: int = 1, error: str | None = None) -> dict[str, Any]:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "command": command,
            "requested": requested,
            "before": before,
            "actual": after,
            "after": after,
            "success": success,
            "attempts": attempts,
            "error": error,
        }
        self.audit_log.append(entry)
        if success:
            event(self.log, "write_ok", command=command, attempts=attempts)
            self._terminal_status("write_ok", command=command, attempts=attempts)
        else:
            error_event(self.log, "write_failed", command=command, error=error)
            self._terminal_status("write_failed", command=command, error=error)
        return entry

    def _execute(self, command: str, **kwargs: Any) -> dict[str, Any]:
        if self.manager is None:
            raise RuntimeError("GoodWe manager is not configured")
        result = self.manager.execute(command, **kwargs)
        requested = result.get("requested", {"command": command, **kwargs})
        actual = result.get("actual", {"value": result.get("value")})
        return self._record(command=command, requested=requested,
                            before=self.manager.status_snapshot().get("last_write", {}).get("before"),
                            after=actual, success=bool(result.get("success", True)),
                            attempts=int(result.get("attempts", 1)))

    def set_export_limit_enabled(self, value: bool, *, requested_by="controller", source="controller") -> dict[str, Any]:
        return self._execute("set_export_limit_enabled", value=bool(value), requested_by=requested_by, source=source)

    def set_export_limit_w(self, value: int, *, requested_by="controller", source="controller"):
        return self._execute("set_export_limit_w", value=int(value), requested_by=requested_by, source=source)

    def set_on_grid_soc_limit_pct(self, value: int, *, requested_by="controller", source="controller"):
        return self._execute("set_on_grid_soc_limit_pct", value=int(value), requested_by=requested_by, source=source)

    def start_battery_charge(self, power_pct: int, start_soc_pct: int, stop_soc_pct: int, valid_from: Any, valid_to: Any,
                             *, requested_by="controller", source="controller"):
        return self._execute("start_battery_charge", power_pct=power_pct,
                             start_soc_pct=start_soc_pct, stop_soc_pct=stop_soc_pct,
                             valid_from=valid_from, valid_to=valid_to,
                             requested_by=requested_by, source=source)

    def start_battery_discharge(self, power_pct: int, start_soc_pct: int, stop_soc_pct: int, valid_from: Any, valid_to: Any,
                                *, requested_by="controller", source="controller"):
        return self._execute("start_battery_discharge", power_pct=power_pct,
                             start_soc_pct=start_soc_pct, stop_soc_pct=stop_soc_pct,
                             valid_from=valid_from, valid_to=valid_to,
                             requested_by=requested_by, source=source)

    def stop_battery_control(self, *, requested_by="controller", source="controller"):
        return self._execute("stop_battery_control", requested_by=requested_by, source=source)

