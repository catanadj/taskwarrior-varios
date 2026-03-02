"""Persistence helpers for TaskVarios metadata storage."""

from functools import lru_cache
import logging
from pathlib import Path
import tempfile
from typing import Any

try:
    import ujson as json
except ImportError:
    import json

try:
    JSON_DECODE_ERRORS = (json.JSONDecodeError, ValueError)
except AttributeError:
    JSON_DECODE_ERRORS = (ValueError,)

logger = logging.getLogger(__name__)


def get_default_db_path(script_file: str) -> str:
    """Return path to `variosdb.json` located next to a script file."""
    return str(Path(script_file).resolve().parent / "variosdb.json")


@lru_cache(maxsize=None)
def load_sultandb(file_path: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            sultandb = json.load(file)
    except (FileNotFoundError,) + JSON_DECODE_ERRORS:
        logger.warning("Using empty SultanDB due to missing/corrupt file: %s", file_path)
        sultandb = {"aors": [], "projects": []}
    return sultandb.get("aors", []), sultandb.get("projects", [])


def save_sultandb(
    file_path: str, aors: list[dict[str, Any]], projects: list[dict[str, Any]]
) -> None:
    sultandb = {"aors": aors, "projects": projects}
    destination = Path(file_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=destination.parent, delete=False
    ) as file:
        json.dump(sultandb, file, default=str, indent=4)
        temp_path = Path(file.name)
    temp_path.replace(destination)
    load_sultandb.cache_clear()
