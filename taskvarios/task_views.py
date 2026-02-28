from datetime import datetime

import pytz
import questionary
from colorama import Fore
from termcolor import colored


def display_overdue_tasks(warrior, local_tz):
    tasks = warrior.load_tasks()
    print(colored("Overdue Tasks", "yellow", attrs=["bold"]))
    include_recurrent = questionary.confirm(
        "Include recurrent tasks in the search?", default=False
    ).ask()
    if include_recurrent:
        tasks = tasks["pending"]
    else:
        tasks = [task for task in tasks["pending"] if "recur" not in task]

    overdue_tasks = []
    now = datetime.now(local_tz)
    for task in tasks:
        due_date_str = task.get("due")
        if due_date_str:
            due_date = datetime.strptime(due_date_str, "%Y%m%dT%H%M%SZ").replace(
                tzinfo=pytz.UTC
            )
            due_date = due_date.astimezone(local_tz)
            if due_date < now:
                time_remaining = now - due_date
                task["time_remaining"] = str(time_remaining.days) + " days"
                overdue_tasks.append(task)

    overdue_tasks.sort(key=lambda task: task["due"])

    if overdue_tasks:
        for task in overdue_tasks:
            task_id = colored(f"{task['id']}", "yellow")
            if task.get("value"):
                task_value = colored(f"{int(task['value'])}", "red", attrs=["bold"])
            else:
                task_value = ""

            description = colored(task["description"], "cyan")
            tag = colored(",".join(task.get("tags", [])), "red", attrs=["bold"])
            project = colored(task.get("project", ""), "blue", attrs=["bold"])
            time_remaining = colored(
                task.get("time_remaining", ""), "green", attrs=["bold"]
            )

            print(f"{task_id} {description} {task_value} {tag} {project} -{time_remaining}")

            if "annotations" in task:
                for annotation in task["annotations"]:
                    entry_date = datetime.strptime(
                        annotation["entry"], "%Y%m%dT%H%M%SZ"
                    ).date()
                    print(
                        f"\t{Fore.CYAN}{entry_date}{Fore.YELLOW}: {annotation['description']}"
                    )
        print("=" * 60)
    else:
        print("No overdue tasks found.")
