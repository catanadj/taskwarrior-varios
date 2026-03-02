from taskvarios import interactive


class FakeSelect:
    def __init__(self, value):
        self._value = value

    def ask(self):
        return self._value


def test_search_project_route_calls_project_search(monkeypatch):
    calls = {"project_search": 0}

    responses = iter(["s", "e"])
    monkeypatch.setattr("builtins.input", lambda: next(responses))
    monkeypatch.setattr(
        interactive.questionary,
        "select",
        lambda *a, **k: FakeSelect("Search Project"),
    )

    def sync_with_taskwarrior_fn(aors, projects, file_path):
        return aors, [], projects, []

    def call_and_process_task_projects_fn():
        calls["project_search"] += 1

    interactive.interactive_prompt(
        "db.json",
        [],
        [],
        sync_with_taskwarrior_fn,
        lambda *a, **k: None,
        lambda *a, **k: {},
        lambda *a, **k: None,
        lambda *a, **k: None,
        call_and_process_task_projects_fn,
        lambda *a, **k: None,
        lambda *a, **k: None,
        lambda *a, **k: None,
        lambda *a, **k: None,
        lambda *a, **k: None,
        lambda *a, **k: None,
        lambda *a, **k: None,
        lambda *a, **k: None,
        lambda *a, **k: None,
        lambda *a, **k: None,
        lambda *a, **k: None,
        lambda *a, **k: None,
    )

    assert calls["project_search"] == 1
