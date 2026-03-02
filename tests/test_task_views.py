from datetime import datetime

import pytz

from taskvarios import task_views


class FakeWarrior:
    def __init__(self, tasks):
        self._tasks = tasks

    def load_tasks(self):
        return {"pending": self._tasks}


class FakeConfirm:
    def __init__(self, value):
        self._value = value

    def ask(self):
        return self._value


def test_display_due_tasks_includes_today_tasks(monkeypatch, capsys):
    now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
    due_today = now_utc.strftime("%Y%m%dT%H%M%SZ")
    warrior = FakeWarrior(
        [{"id": 42, "description": "today task", "due": due_today, "tags": []}]
    )

    monkeypatch.setattr(task_views.questionary, "confirm", lambda *a, **k: FakeConfirm(False))
    task_views.display_due_tasks(warrior, pytz.UTC)

    output = capsys.readouterr().out
    assert "Today" in output
    assert "[42]" in output
    assert "today task" in output
