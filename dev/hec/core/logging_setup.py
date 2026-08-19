"""Strukturované logování s rotací.

Formát řádku: `ts | level | module | event | key=value ...`
Logy jsou anglicky – jsou to diagnostická data, ne uživatelské rozhraní.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_SECRETS: set[str] = set()
_CONFIGURED = False

FORMAT = "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s"
DATEFMT = "%Y-%m-%dT%H:%M:%S%z"


class SecretFilter(logging.Filter):
    """Poslední pojistka: tajemství se nesmí dostat do logu ani omylem."""

    def filter(self, record: logging.LogRecord) -> bool:
        if _SECRETS:
            message = record.getMessage()
            for secret in _SECRETS:
                if secret and secret in message:
                    message = message.replace(secret, "***")
                    record.msg, record.args = message, ()
        return True


def register_secrets(values) -> None:
    _SECRETS.update(v for v in values if isinstance(v, str) and len(v) >= 6)


def configure(logs_dir: str | Path, *, level: str = "INFO", max_bytes: int = 5_000_000,
              backups: int = 5, console: bool = True) -> None:
    """Nastaví kořenový logger. Volá se jednou při startu aplikace."""
    global _CONFIGURED
    logs_dir = Path(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("hec")
    root.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    root.handlers.clear()
    root.propagate = False

    formatter = logging.Formatter(FORMAT, datefmt=DATEFMT)
    secret_filter = SecretFilter()

    file_handler = RotatingFileHandler(logs_dir / "hec.log", maxBytes=max_bytes,
                                       backupCount=backups, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(secret_filter)
    root.addHandler(file_handler)

    error_handler = RotatingFileHandler(logs_dir / "errors.log", maxBytes=max_bytes,
                                        backupCount=backups, encoding="utf-8")
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)
    error_handler.addFilter(secret_filter)
    root.addHandler(error_handler)

    if console:
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        stream.addFilter(secret_filter)
        root.addHandler(stream)

    _CONFIGURED = True


def get_logger(module: str) -> logging.Logger:
    return logging.getLogger(f"hec.{module}")


def is_configured() -> bool:
    return _CONFIGURED


def _pairs(fields: dict) -> str:
    parts = []
    for key, value in fields.items():
        if isinstance(value, float):
            value = f"{value:.3f}".rstrip("0").rstrip(".")
        parts.append(f"{key}={value}")
    return " ".join(parts)


def event(logger: logging.Logger, name: str, level: int = logging.INFO, **fields) -> None:
    """Zaloguje událost ve tvaru `event | key=value`."""
    logger.log(level, "%s | %s", name, _pairs(fields))


def warn_event(logger: logging.Logger, name: str, **fields) -> None:
    event(logger, name, logging.WARNING, **fields)


def error_event(logger: logging.Logger, name: str, **fields) -> None:
    event(logger, name, logging.ERROR, **fields)
