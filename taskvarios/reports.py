"""Reporting commands extracted from TaskVarios."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import subprocess

from dateutil.parser import parse
import pytz
from rich.console import Console
from rich.text import Text
from rich.tree import Tree
from taskw import TaskWarrior as Warrior

try:
    import ujson as json
except ImportError:
    import json

try:
    import pandas as pd
except ImportError:
    pd = None


warrior = Warrior()

# Branch colors used in report tree output.
SUMMARY_COLORS = ["red", "green", "yellow", "magenta", "cyan"]

def basic_summary():

    

    console = Console()
    tasks = warrior.load_tasks()
    project_data = defaultdict(lambda: defaultdict(list))
    project_task_count = defaultdict(int)
    now = datetime.utcnow().replace(tzinfo=pytz.UTC)

    for task in tasks["pending"]:
        project = task.get("project", None)
        tags = task.get("tags", [])
        description = task.get("description", "")
        task_id = task.get("id", "")
        due_date_str = task.get("due")
        due_date = (
            parse(due_date_str) if due_date_str and due_date_str != "" else None
        )

        if project:
            # Count tasks for each level of the project hierarchy
            project_levels = project.split(".")
            for i in range(1, len(project_levels) + 1):
                project_task_count[".".join(project_levels[:i])] += 1

            if tags:
                for tag in tags:
                    time_remaining = due_date - now if due_date else None
                    time_remaining_str = (
                        str(time_remaining)[:-7] if time_remaining else ""
                    )
                    project_data[project][tag].append(
                        [
                            f"{task_id} {description}",
                            due_date_str,
                            time_remaining_str,
                        ]
                    )
            else:
                project_data[project]["No Tag"].append(
                    [f"{task_id} {description}", due_date_str, time_remaining_str]
                )
        else:
            project_task_count["No Project"] += 1
            if tags:
                for tag in tags:
                    project_data["No Project"][tag].append(
                        [
                            f"{task_id} {description}",
                            due_date_str,
                            time_remaining_str,
                        ]
                    )
            else:
                project_data["No Project"]["No Tag"].append(
                    [f"{task_id} {description}", due_date_str, time_remaining_str]
                )

    tree = Tree("Tasks Summary")

    for project, tag_data in sorted(project_data.items()):
        if project != "No Project":
            project_levels = project.split(".")
            project_branch = tree
            for i, level in enumerate(project_levels):
                color = SUMMARY_COLORS[i % len(SUMMARY_COLORS)]
                current_project = ".".join(project_levels[: i + 1])
                level_text = Text(
                    f"{level} [{project_task_count[current_project]}]",
                    style=f"{color} bold",
                )

                if level_text not in [
                    child.label for child in project_branch.children
                ]:
                    project_branch = project_branch.add(level_text)
                else:
                    project_branch = next(
                        child
                        for child in project_branch.children
                        if child.label == level_text
                    )

            for tag, tasks_data in sorted(tag_data.items()):
                tag_color = "green" if not project.startswith("AoR.") else "cyan"
                tag_branch = project_branch.add(
                    Text(f"{tag} [{len(tasks_data)}]", style=f"{tag_color} bold")
                )

    # Handle "No Project" separately to make sure it comes at the end
    if "No Project" in project_data:
        project_branch = tree.add(
            Text(
                f"No Project [{project_task_count['No Project']}]", style="red bold"
            )
        )
        for tag, tasks_data in sorted(project_data["No Project"].items()):
            tag_color = "blue"
            tag_branch = project_branch.add(
                Text(f"{tag} [{len(tasks_data)}]", style=f"{tag_color} bold")
            )

    console.print(tree)

def next_summary():


    console = Console()

    tasks = warrior.load_tasks()

    project_data = defaultdict(lambda: defaultdict(list))
    now = datetime.utcnow().replace(tzinfo=pytz.UTC)

    for task in tasks["pending"]:
        project = task.get("project", None)
        tags = task.get("tags", [])
        description = task.get("description", "")
        task_id = task.get("id", "")
        due_date_str = task.get("due")
        due_date = (
            parse(due_date_str) if due_date_str and due_date_str != "" else None
        )

        # Only process tasks with the "next" tag
        if "next" in tags:
            if project:
                time_remaining = due_date - now if due_date else None
                time_remaining_str = (
                    str(time_remaining)[:-7] if time_remaining else ""
                )
                project_data[project]["next"] = [
                    f"{task_id} {description}",
                    due_date_str,
                    time_remaining_str,
                ]
            else:
                # For tasks without a project, we will put them under "No Project" key
                project_data["No Project"]["next"].append(
                    f"{task_id} {description}"
                )

    tree = Tree(Text("Saikou", style="green bold"))

    for project, tag_data in sorted(project_data.items()):
        if project != "No Project":
            project_levels = project.split(".")
            project_branch = tree

            for level_idx, level in enumerate(project_levels):
                if level not in [
                    child.label.plain for child in project_branch.children
                ]:
                    project_branch = project_branch.add(
                        Text(level, style=f"{SUMMARY_COLORS[level_idx % len(SUMMARY_COLORS)]} bold")
                    )
                else:
                    project_branch = next(
                        child
                        for child in project_branch.children
                        if child.label.plain == level
                    )

            if "next" in tag_data:
                tag_color = "blue" if not project.startswith("AoR.") else "yellow"
                tag_branch = project_branch.add(
                    Text("next", style=f"{tag_color} bold")
                )

                task_data = tag_data["next"][0]
                if task_data:
                    task_id, description = (task_data.split(" ", 1) + [""])[:2]
                    due_date = (
                        tag_data["next"][1] if len(tag_data["next"]) > 1 else None
                    )
                    try:
                        due_date_formatted = (
                            datetime.strptime(due_date, "%Y%m%dT%H%M%SZ").strftime(
                                "%Y-%m-%d"
                            )
                            if due_date
                            else ""
                        )
                    except ValueError:
                        due_date_formatted = ""

                    time_remaining = (
                        tag_data["next"][2] if len(tag_data["next"]) > 2 else None
                    )

                    tag_branch.add(
                        f"[red bold]{task_id}[/red bold] [white bold]{description}[/white bold] [blue bold]{due_date_formatted}[/blue bold] [green bold]{time_remaining}[/green bold]"
                    )

    # Handle "No Project" separately to make sure it comes at the end
    if "No Project" in project_data:
        project_branch = tree.add(Text("No Project", style="red bold"))
        if "next" in project_data["No Project"]:
            tag_color = "blue"
            tag_branch = project_branch.add(Text("next", style=f"{tag_color} bold"))

            for task_data in project_data["No Project"]["next"]:
                task_id, description = (task_data.split(" ", 1) + [""])[:2]
                tag_branch.add(
                    f"[red bold]{task_id}[/red bold] [white]{description}[/white]"
                )

    console.print(tree)

def detailed_summary():


    console = Console()

    tasks = warrior.load_tasks()

    project_data = defaultdict(lambda: defaultdict(list))
    now = datetime.utcnow().replace(tzinfo=pytz.UTC)

    for task in tasks["pending"]:
        project = task.get("project", None)
        tags = task.get("tags", [])
        description = task.get("description", "")
        task_id = task.get("id", "")
        due_date_str = task.get("due")
        due_date = (
            parse(due_date_str) if due_date_str and due_date_str != "" else None
        )

        if project:
            if tags:
                for tag in tags:
                    if not project_data[project][tag] or (
                        due_date
                        and (
                            not project_data[project][tag][1]
                            or due_date < parse(project_data[project][tag][1])
                        )
                    ):
                        time_remaining = due_date - now if due_date else None
                        time_remaining_str = (
                            str(time_remaining)[:-7] if time_remaining else ""
                        )
                        project_data[project][tag] = [
                            f"{task_id} {description}",
                            due_date_str,
                            time_remaining_str,
                        ]
            else:
                time_remaining = due_date - now if due_date else None
                time_remaining_str = (
                    str(time_remaining)[:-7] if time_remaining else ""
                )
                project_data[project]["No Tag"] = [
                    f"{task_id} {description}",
                    due_date_str,
                    time_remaining_str,
                ]

        else:
            # For tasks without a project, we will put them under "No Project" key
            if tags:
                for tag in tags:
                    project_data["No Project"][tag].append(
                        f"{task_id} {description}"
                    )
            else:
                # For tasks without a project and without tags, we put them under "No Tag" key
                project_data["No Project"]["No Tag"].append(
                    f"{task_id} {description}"
                )

    tree = Tree(Text("Saikou", style="green bold"))

    for project, tag_data in sorted(project_data.items()):
        if project != "No Project":
            project_levels = project.split(".")
            project_branch = tree

            for level_idx, level in enumerate(project_levels):
                if level not in [
                    child.label.plain for child in project_branch.children
                ]:
                    project_branch = project_branch.add(
                        Text(level, style=f"{SUMMARY_COLORS[level_idx % len(SUMMARY_COLORS)]} bold")
                    )
                else:
                    project_branch = next(
                        child
                        for child in project_branch.children
                        if child.label.plain == level
                    )

            for tag, data in sorted(tag_data.items()):
                tag_color = "blue" if not project.startswith("AoR.") else "yellow"
                tag_branch = project_branch.add(
                    Text(tag, style=f"{tag_color} bold")
                )

                task_data = data[0]
                if task_data:
                    task_id, description = (task_data.split(" ", 1) + [""])[:2]
                    due_date = data[1] if len(data) > 1 else None
                    try:
                        due_date_formatted = (
                            datetime.strptime(due_date, "%Y%m%dT%H%M%SZ").strftime(
                                "%Y-%m-%d"
                            )
                            if due_date
                            else ""
                        )
                    except ValueError:
                        due_date_formatted = ""

                    time_remaining = data[2] if len(data) > 2 else None

                    tag_branch.add(
                        f"[red bold]{task_id}[/red bold] [white bold]{description}[/white bold] [blue bold]{due_date_formatted}[/blue bold] [green bold]{time_remaining}[/green bold]"
                    )

    # Handle "No Project" separately to make sure it comes at the end
    if "No Project" in project_data:
        project_branch = tree.add(Text("No Project", style="red bold"))
        for tag, data in sorted(project_data["No Project"].items()):
            tag_color = "blue"
            tag_branch = project_branch.add(Text(tag, style=f"{tag_color} bold"))

            task_data = data[0]
            if task_data:
                task_id, description = (task_data.split(" ", 1) + [""])[:2]
                due_date = data[1] if len(data) > 1 else None
                try:
                    due_date_formatted = (
                        datetime.strptime(due_date, "%Y%m%dT%H%M%SZ").strftime(
                            "%Y-%m-%d"
                        )
                        if due_date
                        else ""
                    )
                except ValueError:
                    due_date_formatted = ""

                time_remaining = data[2] if len(data) > 2 else None

                tag_branch.add(
                    f"[red bold]{task_id}[/red bold] [white]{description}[/white] [blue bold]{due_date_formatted}[/blue bold] [green bold]{time_remaining}[/green bold]"
                )

    console.print(tree)

def all_summary():
    # from rich import print


    console = Console()

    tasks = warrior.load_tasks()

    project_data = defaultdict(lambda: defaultdict(list))
    no_project_data = defaultdict(list)
    no_project_no_tag_data = []
    now = datetime.utcnow().replace(tzinfo=pytz.UTC)

    for task in tasks["pending"]:
        project = task.get("project", None)
        tags = task.get("tags", [])
        description = task.get("description", "")
        task_id = task.get("id", "")
        due_date_str = task.get("due")
        due_date = (
            parse(due_date_str) if due_date_str and due_date_str != "" else None
        )
        time_remaining = due_date - now if due_date else None
        time_remaining_str = str(time_remaining)[:-7] if time_remaining else ""
        priority = task.get("priority", "")

        if project:
            if tags:
                for tag in tags:
                    project_data[project][tag].append(
                        [
                            f"{task_id} {description}",
                            due_date_str,
                            time_remaining_str,
                            priority,
                        ]
                    )
            else:
                project_data[project]["No Tag"].append(
                    [
                        f"{task_id} {description}",
                        due_date_str,
                        time_remaining_str,
                        priority,
                    ]
                )
        elif tags:
            for tag in tags:
                no_project_data[tag].append(
                    [
                        f"{task_id} {description}",
                        due_date_str,
                        time_remaining_str,
                        priority,
                    ]
                )
        else:
            no_project_no_tag_data.append(
                [
                    f"{task_id} {description}",
                    due_date_str,
                    time_remaining_str,
                    priority,
                ]
            )

    tree = Tree("Saikou", style="green bold")

    sorted_projects = sorted(
        [project for project in project_data.keys() if project != "No Project"]
    ) + ["No Project" if "No Project" in project_data else ""]

    for project in sorted_projects:
        tag_data = project_data[project]
        project_levels = project.split(".")
        project_branch = tree

        for level_idx, level in enumerate(project_levels):
            if level not in [
                child.label.plain for child in project_branch.children
            ]:
                project_branch = project_branch.add(
                    Text(level, style=f"{SUMMARY_COLORS[level_idx % len(SUMMARY_COLORS)]} bold")
                )
            else:
                project_branch = next(
                    child
                    for child in project_branch.children
                    if child.label.plain == level
                )

        for tag, tasks_data in sorted(tag_data.items()):
            tag_color = "blue" if not project.startswith("AoR.") else "yellow"
            tag_branch = project_branch.add(Text(tag, style=f"{tag_color} bold"))

            for data in tasks_data:
                task_data = data[0]
                task_id, description = (task_data.split(" ", 1) + [""])[:2]
                due_date = data[1] if len(data) > 1 else None
                priority = data[3] if len(data) > 3 else "No Priority"
                try:
                    due_date_formatted = (
                        datetime.strptime(due_date, "%Y%m%dT%H%M%SZ").strftime(
                            "%Y-%m-%d"
                        )
                        if due_date
                        else ""
                    )
                except ValueError:
                    due_date_formatted = ""

                time_remaining = data[2] if len(data) > 2 else None

                color_pri = ""
                if priority == "H":
                    color_pri = "red"
                else:
                    color_pri = "white"

                tag_branch.add(
                    f"[yellow bold]{priority}[/yellow bold] [red bold]{task_id}[/red bold] [{color_pri}]{description}[/{color_pri}] [blue bold]{due_date_formatted}[/blue bold] [green bold]{time_remaining}[/green bold]"
                )

    # Handle "No Project" tasks
    no_project_branch = tree.add("No Project", style="red bold")

    for tag, tasks_data in no_project_data.items():
        tag_branch = no_project_branch.add(
            Text(f"{tag} [{len(tasks_data)} tasks]", style="blue bold")
        )

        for data in tasks_data:
            task_data = data[0]
            task_id, description = (task_data.split(" ", 1) + [""])[:2]
            due_date = data[1] if len(data) > 1 else None
            priority = data[3] if len(data) > 3 else "No Priority"
            try:
                due_date_formatted = (
                    datetime.strptime(due_date, "%Y%m%dT%H%M%SZ").strftime(
                        "%Y-%m-%d"
                    )
                    if due_date
                    else ""
                )
            except ValueError:
                due_date_formatted = ""

            time_remaining = data[2] if len(data) > 2 else None

            tag_branch.add(
                f"[yellow bold]{priority}[/yellow bold] [red bold]{task_id}[/red bold] [white]{description}[/white] [blue bold]{due_date_formatted}[/blue bold] [green bold]{time_remaining}[/green bold] "
            )

    # Handle "No Project, No Tag" tasks
    no_project_no_tag_branch = tree.add("No Project, No Tag", style="red bold")

    for data in no_project_no_tag_data:
        task_data = data[0]
        task_id, description = (task_data.split(" ", 1) + [""])[:2]
        due_date = data[1] if len(data) > 1 else None
        priority = data[3] if len(data) > 3 else "No Priority"
        try:
            due_date_formatted = (
                datetime.strptime(due_date, "%Y%m%dT%H%M%SZ").strftime("%Y-%m-%d")
                if due_date
                else ""
            )
        except ValueError:
            due_date_formatted = ""

        time_remaining = data[2] if len(data) > 2 else None

        no_project_no_tag_branch.add(
            f"[yellow bold]{priority}[/yellow bold] [red bold]{task_id}[/red bold] [white]{description}[/white] [blue bold]{due_date_formatted}[/blue bold] [green bold]{time_remaining}[/green bold]"
        )

    console.print(tree)

def recurrent_report():
    from rich.table import Table
    from rich.console import Console
    from statistics import mean

    def parse_date(date_str):
        utc_time = datetime.strptime(date_str, "%Y%m%dT%H%M%SZ")
        return utc_time.replace(tzinfo=timezone.utc).astimezone(tz=None)

    def color_code_percentage(percentage):
        if percentage > 0.75:
            return "[green]", "[/green]"
        elif 0.5 <= percentage <= 0.75:
            return "[yellow]", "[/yellow]"
        elif 0.25 <= percentage < 0.5:
            return "[magenta]", "[/magenta]"
        else:
            return "[red]", "[/red]"

    def get_all_deleted_tasks():
        # Run the 'task export' command and get the output
        result = subprocess.run(["task", "export"], stdout=subprocess.PIPE)

        # Load the output into Python as JSON
        all_tasks = json.loads(result.stdout)

        # Prepare a list to store tasks
        deleted_tasks = []

        # Iterate over all tasks
        for task in all_tasks:
            # Check if task status is 'deleted'
            if task["status"] == "deleted" and "due" in task:
                task["due"] = datetime.strptime(
                    task["due"], "%Y%m%dT%H%M%SZ"
                ).date()  # convert to datetime.date object
                deleted_tasks.append(task)

        # Return the list of tasks
        return deleted_tasks

    if pd is None:
        Console().print("pandas is required for recurrent_report.", style="bold red")
        return

    quote = "We are what we repeatedly do. Excellence, then, is not an act, but a habit."
    print(quote)

    all_tasks = warrior.load_tasks()

    completed_tasks = all_tasks["completed"]
    pending_tasks = all_tasks["pending"]

    tasks_today = [
        task
        for task in pending_tasks + completed_tasks
        if "recur" in task
        and "due" in task
        and parse_date(task["due"]).date() == datetime.now().date()
    ]

    deleted_tasks = get_all_deleted_tasks()

    weekly_report = {}
    task_counter = 1  # Start task_counter from 1
    task_map = {}
    completion_rates = []
    total_status_counter = Counter()
    for task in tasks_today:
        status_counter = Counter()
        task_description = task["description"]
        task_id = task["id"]

        weekly_report[task_counter] = {}

        for i in range(8):
            date = datetime.now().date() - timedelta(days=i)

            completed = any(
                task
                for task in completed_tasks
                if task.get("end")
                and parse_date(task["end"]).date() == date
                and task["description"] == task_description
            )
            pending = any(
                task
                for task in pending_tasks
                if "due" in task
                and parse_date(task["due"]).date() == date
                and task["description"] == task_description
            )
            deleted = any(
                task
                for task in deleted_tasks
                if task["description"] == task_description and task["due"] == date
            )

            due = pending

            if completed:
                weekly_report[task_counter][date.strftime("%m-%d")] = (
                    "[green]C[/green]"
                )
                status_counter["C"] += 1
            elif deleted:
                weekly_report[task_counter][date.strftime("%m-%d")] = "[red]D[/red]"
                status_counter["D"] += 1
            elif due:
                weekly_report[task_counter][date.strftime("%m-%d")] = (
                    "[red bold]P[/red bold]"
                )
                status_counter["P"] += 1
            else:
                weekly_report[task_counter][date.strftime("%m-%d")] = "-"

        completion_percentage = status_counter["C"] / sum(status_counter.values())
        completion_rates.append(completion_percentage)
        color_open, color_close = color_code_percentage(completion_percentage)

        if completion_percentage >= 0.80:
            task_description = f"[white bold]{task_description}[/white bold]"
        task_map[task_counter] = (
            f"{color_open}{completion_percentage:.0%}{color_close} {task_description} [{task_id:02}]"
        )

        total_status_counter += status_counter

        task_counter += 1  # Increment task_counter

    total_tasks = sum(total_status_counter.values())
    average_completion_percentage = mean(completion_rates)

    # Convert the weekly report to a pandas DataFrame
    report_df = pd.DataFrame(weekly_report)

    console = Console()
    table = Table(show_header=True, header_style="bold cyan")

    # Add columns
    table.add_column("Date")
    for col in range(1, len(report_df.columns) + 1):
        table.add_column(f"{col:02}")

    # Add rows
    for date, statuses in report_df.iterrows():
        table.add_row(date, *[str(status) for status in statuses])

    console.print(table)

    for task_number, task_description in task_map.items():
        console.print(f"Task {task_number:02}: {task_description}")
    # Print summary statistics
    console.print(f"\nTotal Tasks: {total_tasks}")
    console.print(f"Tasks Completed: {total_status_counter['C']}")
    console.print(f"Tasks Deleted: {total_status_counter['D']}")
    console.print(f"Tasks Pending: {total_status_counter['P']}")
    console.print(f"Average Completion Rate: {average_completion_percentage:.2%}")
