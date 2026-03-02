from taskvarios import reports


class FakeWarrior:
    def load_tasks(self):
        return {
            "pending": [
                {
                    "id": 1,
                    "description": "task with no due",
                    "project": "proj.alpha",
                    "tags": [],
                }
            ]
        }


def test_basic_summary_handles_tasks_without_due_date(monkeypatch):
    monkeypatch.setattr(reports, "warrior", FakeWarrior())
    reports.basic_summary()
