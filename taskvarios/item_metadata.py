"""Item metadata date/detail views extracted from TaskVarios."""

from datetime import datetime, timedelta

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from taskw import TaskWarrior as Warrior


warrior = Warrior()


def get_creation_date(item_name, pending_tasks=None):
    if pending_tasks is None:
        pending_tasks = warrior.load_tasks()["pending"]
    for task in pending_tasks:
        project = task.get("project")
        if project and (
            project == item_name or project.startswith("AoR." + item_name)
        ):
            created = task.get("entry")
            if created:
                return datetime.strptime(created, "%Y%m%dT%H%M%SZ")

    return None


def get_last_modified_date(item_name, pending_tasks=None):
    if pending_tasks is None:
        pending_tasks = warrior.load_tasks()["pending"]
    last_modified = None
    for task in pending_tasks:
        project = task.get("project")
        if project and (
            project == item_name or project.startswith("AoR." + item_name)
        ):
            modified = task.get("modified")
            if modified:
                modified_date = datetime.strptime(modified, "%Y%m%dT%H%M%SZ")
                if last_modified is None or modified_date > last_modified:
                    last_modified = modified_date

    return last_modified


def view_project_metadata(item, tags, item_name):
    console = Console()
    pending_tasks = warrior.load_tasks()["pending"]
    # Display creation date
    creation_date = get_creation_date(item["name"], pending_tasks)
    if creation_date:
        current_datetime = datetime.now()
        creation_time_difference = current_datetime - creation_date
        creation_days_remaining = creation_time_difference.days
        creation_time_remaining = creation_time_difference.seconds
        creation_time_prefix = "-" if creation_days_remaining > 0 else "+"
        creation_time_remaining_formatted = str(
            timedelta(seconds=abs(creation_time_remaining))
        )
        creation_time_difference_formatted = f"({creation_time_prefix}{abs(creation_days_remaining)} days, {creation_time_remaining_formatted})"
        console.print(
            Panel(
                f"[blue]Creation Date: [yellow]{creation_date.strftime('%Y-%m-%d %H:%M')} {creation_time_difference_formatted}[/yellow]",
                title="Creation Date",
                expand=False,
            )
        )

    # Display last modified date
    last_modified_date = get_last_modified_date(item["name"], pending_tasks)
    if last_modified_date:
        current_datetime = datetime.now()
        last_modified_time_difference = current_datetime - last_modified_date
        last_modified_days_remaining = last_modified_time_difference.days
        last_modified_time_remaining = last_modified_time_difference.seconds
        last_modified_time_prefix = "-" if last_modified_days_remaining > 0 else "+"
        last_modified_time_remaining_formatted = str(
            timedelta(seconds=abs(last_modified_time_remaining))
        )
        last_modified_time_difference_formatted = f"({last_modified_time_prefix}{abs(last_modified_days_remaining)} days, {last_modified_time_remaining_formatted})"
        console.print(
            Panel(
                f"[blue]Last Modified Date: [yellow]{last_modified_date.strftime('%Y-%m-%d %H:%M')} {last_modified_time_difference_formatted}[/yellow]",
                title="Last Modified Date",
                expand=False,
            )
        )

    # Display item name and description
    console.print(
        Panel(
            f"[blue]Name: [yellow]{item['name']}[/yellow]",
            title="Item Name",
            expand=False,
        )
    )
    console.print(
        Panel(
            f"[blue]Description:\n [cornflower_blue]{item.get('description', '')}[/cornflower_blue]",
            title="Description",
            expand=False,
        )
    )

    # # Display task counts
    # pending_tasks = get_task_count(item_name, 'pending')
    # completed_tasks = get_task_count(item_name, 'completed')
    # deleted_tasks = get_task_count(item_name, 'deleted')

    # task_counts = Text.assemble(
    # 	("Pending: ", "yellow"), (f"{pending_tasks}", "yellow"), (" | Completed: ", "yellow"), (f"{completed_tasks}", "green"), (" | Deleted: ", "yellow"), (f"{deleted_tasks}", "blue")
    # )
    # console.print(Panel(task_counts, title="Task Counts", expand=False))

    # console.print("\n")

    # Display standard or outcome
    if "standard" in item or "outcome" in item:
        field_name = "Standard" if "outcome" not in item else "Outcome"
        field_value = (
            item.get("standard") if "outcome" not in item else item.get("outcome")
        )
        console.print(
            Panel(
                f"[blue]{field_name}: [yellow]{field_value}[/yellow]",
                title=field_name,
                expand=False,
            )
        )

    # # Display outcome
    # if 'outcome' in item:
    # 	console.print(Panel(f"[blue]Outcome: [yellow]{item['outcome']}[/yellow]", title="Outcome", expand=False))

    # Display annotations
    if "annotations" in item:
        table = Table(title="Annotations", box=box.SIMPLE)
        table.add_column("Timestamp", style="dim", width=20)
        table.add_column("Content", style="yellow")

        for i, annotation in enumerate(item["annotations"]):
            timestamp_str = annotation.get("timestamp")
            content = annotation.get("content", "")

            # Remove milliseconds if present
            if "." in timestamp_str:
                timestamp_str = timestamp_str.split(".")[0]

            row_style = "gold1" if i % 2 == 0 else "cornflower_blue"
            table.add_row(timestamp_str, content, style=row_style)

        console.print(table)

    # Display work logs
    if "workLogs" in item:
        table = Table(title="Work Logs", box=box.SIMPLE)
        table.add_column("Timestamp", style="bright", width=20)
        table.add_column("Content", style="yellow")

        for i, work_log in enumerate(item["workLogs"]):
            timestamp_str = work_log.get("timestamp")
            content = work_log.get("content", "")

            # Remove milliseconds if present
            if "." in timestamp_str:
                timestamp_str = timestamp_str.split(".")[0]

            row_style = "deep_pink1" if i % 2 == 0 else "cornflower_blue"
            table.add_row(timestamp_str, content, style=row_style)

        console.print(table)
