from taskvarios import task_manager


class FakeConsole:
    _inputs = iter(["CM", ""])

    def __init__(self):
        pass

    def print(self, *args, **kwargs):
        return None

    def input(self, *args, **kwargs):
        return next(self._inputs)


def test_task_manager_accepts_uppercase_cm(monkeypatch):
    called = {"context": 0}

    monkeypatch.setattr(task_manager, "Console", FakeConsole)

    def get_tasks_fn(_):
        return [{"uuid": "u1", "id": 1, "description": "desc"}]

    def context_menu_fn(_):
        called["context"] += 1

    task_manager.task_manager(
        "u1",
        get_tasks_fn,
        context_menu_fn,
        lambda *a, **k: None,
        lambda *a, **k: [],
        lambda *a, **k: "",
        lambda *a, **k: None,
        lambda *a, **k: None,
        lambda *a, **k: None,
        lambda *a, **k: None,
        lambda *a, **k: None,
        lambda *a, **k: None,
        lambda *a, **k: str(a[0])[:8],
    )

    assert called["context"] == 1
