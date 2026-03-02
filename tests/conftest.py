"""Pytest test bootstrap for local imports and optional dependency stubs."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _install_taskw_stub() -> None:
    module = types.ModuleType("taskw")

    class TaskWarrior:  # pragma: no cover - simple compatibility stub
        def load_tasks(self):
            return {"pending": [], "completed": []}

    module.TaskWarrior = TaskWarrior
    sys.modules["taskw"] = module


def _install_tasklib_stub() -> None:
    module = types.ModuleType("tasklib")

    class TaskWarrior:  # pragma: no cover - simple compatibility stub
        def get_task(self, **_kwargs):
            return {}

    class Task(dict):  # pragma: no cover - compatibility placeholder
        pass

    module.TaskWarrior = TaskWarrior
    module.Task = Task
    sys.modules["tasklib"] = module


if importlib.util.find_spec("taskw") is None:
    _install_taskw_stub()

if importlib.util.find_spec("tasklib") is None:
    _install_tasklib_stub()
