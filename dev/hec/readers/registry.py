"""Sestavení readerů podle konfigurace.

Přidání nového zdroje = nový soubor v `readers/` + jeden řádek zde + sekce
v konfiguračním schématu. Do controlleru se přitom nesahá.
"""

from __future__ import annotations

from ..core.logging_setup import get_logger
from .base import BaseReader
from .goodwe import GoodWeReader
from .ote import OteReader
from .sharing_reader import SharingReader
from .shelly import ShellyReader
from .tng import TngReader
from .weather import WeatherReader

READER_CLASSES: dict[str, type[BaseReader]] = {
    "goodwe": GoodWeReader,
    "tng": TngReader,
    "ote": OteReader,
    "weather": WeatherReader,
    "shelly": ShellyReader,
    "sharing": SharingReader,
}


def build_readers(config, storage) -> list[BaseReader]:
    """Vytvoří povolené readery. Selhání konstruktoru jeden zdroj vypne, ostatní běží."""
    log = get_logger("registry")
    readers: list[BaseReader] = []
    for name, cls in READER_CLASSES.items():
        if not config.get(f"{name}.enabled", False):
            continue
        try:
            readers.append(cls(config, storage))
        except Exception as exc:                              # noqa: BLE001
            log.error("reader_init_failed | reader=%s error=%s: %s", name, type(exc).__name__, exc)
    return readers
