from datetime import datetime, timedelta

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


def display_due_tasks(warrior, local_tz):
    tasks = warrior.load_tasks()

    include_recurrent = questionary.confirm(
        "Include recurrent tasks in the search?", default=False
    ).ask()
    if include_recurrent:
        tasks = tasks["pending"]
    else:
        tasks = [task for task in tasks["pending"] if "recur" not in task]

    now = datetime.now(local_tz)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_overdue = start_of_day - timedelta(days=365)
    end_of_today = start_of_day + timedelta(days=1)
    end_of_tomorrow = end_of_today + timedelta(days=1)
    days_until_next_week = (7 - start_of_day.weekday()) % 7
    if days_until_next_week == 0:
        days_until_next_week = 7
    start_of_next_week = start_of_day + timedelta(days=days_until_next_week)
    end_of_next_week = start_of_next_week + timedelta(days=6)
    start_of_rest_of_the_week = end_of_tomorrow
    end_of_rest_of_the_week = start_of_next_week - timedelta(seconds=1)
    start_of_next_2_weeks = start_of_next_week
    end_of_next_2_weeks = start_of_next_2_weeks + timedelta(days=15)
    start_of_next_3_weeks = start_of_next_week
    end_of_next_3_weeks = start_of_next_3_weeks + timedelta(days=21)
    end_of_next_3_months = start_of_day + timedelta(days=90)
    end_of_next_6_months = start_of_day + timedelta(days=180)
    end_of_next_year = start_of_day + timedelta(days=365)
    end_of_next_3_years = start_of_day + timedelta(days=365 * 3)
    end_of_next_5_years = start_of_day + timedelta(days=365 * 5)
    end_of_next_10_years = start_of_day + timedelta(days=365 * 10)
    end_of_next_20_years = start_of_day + timedelta(days=365 * 20)

    time_frames = [
        ("Next 20 Years", end_of_next_10_years, end_of_next_20_years),
        ("Next 10 Years", end_of_next_5_years, end_of_next_10_years),
        ("Next 5 Years", end_of_next_3_years, end_of_next_5_years),
        ("Next 3 Years", end_of_next_year, end_of_next_3_years),
        ("Next Year", end_of_next_6_months, end_of_next_year),
        ("Next 6 Months", end_of_next_3_months, end_of_next_6_months),
        ("Next 3 Months", end_of_next_3_weeks, end_of_next_3_months),
        ("Next 3 Weeks", end_of_next_week, end_of_next_3_weeks),
        ("Next 2 Weeks", end_of_next_week, end_of_next_2_weeks),
        ("Next Week", start_of_next_week, end_of_next_week),
        ("Rest of the Week", start_of_rest_of_the_week, end_of_rest_of_the_week),
        ("Tomorrow", end_of_today, end_of_tomorrow),
        ("Today", start_of_day, end_of_today),
        ("Overdue", start_of_overdue, start_of_day),
    ]

    categorized_tasks = {name: [] for name, _, _ in time_frames}
    for task in tasks:
        due_date_str = task.get("due")
        if due_date_str:
            due_date = datetime.strptime(due_date_str, "%Y%m%dT%H%M%SZ").replace(
                tzinfo=pytz.UTC
            )
            due_date = due_date.astimezone(local_tz)
            for name, start, end in time_frames:
                if start is None or (start <= due_date < end):
                    if name == "Today":
                        task["time_remaining"] = ""
                    else:
                        delta = due_date - now
                        days, seconds = delta.days, delta.seconds
                        hours = seconds // 3600
                        minutes = (seconds % 3600) // 60
                        task["time_remaining"] = f"{days} days, {hours}:{minutes:02d}"
                    categorized_tasks[name].append(task)
                    break

    for name, tasks in list(categorized_tasks.items()):
        if tasks:
            print(colored(name, "yellow", attrs=["bold"]))
            for task in tasks:
                task_id = colored(f"[{task['id']}]", "yellow")
                description = colored(task["description"], "white")
                tag = colored(",".join(task.get("tags", [])), "red", attrs=["bold"])
                project = colored(task.get("project", ""), "blue", attrs=["bold"])
                time_remaining = colored(
                    task.get("time_remaining", ""), "green", attrs=["bold"]
                )

                print(f"{task_id} {description} {tag} {project} {time_remaining}")

                if "annotations" in task:
                    for annotation in task["annotations"]:
                        entry_date = datetime.strptime(
                            annotation["entry"], "%Y%m%dT%H%M%SZ"
                        ).date()
                        print(
                            f"\t{Fore.CYAN}{entry_date}{Fore.YELLOW}: {annotation['description']}"
                        )
            print("=" * 60)
