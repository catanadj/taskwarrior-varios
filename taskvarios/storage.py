"""Persistence helpers for TaskVarios metadata storage."""

from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import ujson as json
except ImportError:
    import json


def get_default_db_path(script_file: str) -> str:
    """Return path to `variosdb.json` located next to a script file."""
    return str(Path(script_file).resolve().parent / "variosdb.json")


@lru_cache(maxsize=None)
def load_sultandb(file_path: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            sultandb = json.load(file)
    except FileNotFoundError:
        sultandb = {"aors": [], "projects": []}
    return sultandb["aors"], sultandb["projects"]


def save_sultandb(
    file_path: str, aors: list[dict[str, Any]], projects: list[dict[str, Any]]
) -> None:
    sultandb = {"aors": aors, "projects": projects}
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(sultandb, file, default=str, indent=4)
    load_sultandb.cache_clear()
