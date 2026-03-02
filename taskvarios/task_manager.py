"""Task manager workflow extracted from TaskVarios."""

from datetime import datetime, timezone
import subprocess

from dateutil.parser import parse
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from tasklib import TaskWarrior


def display_task_details2(task, short_uuid_fn):
    console = Console()

    # Create the main tree
    task_tree = Tree("Task Details")

    # Add main task details
    task_tree.add(Text(f"Task UUID: {short_uuid_fn(task['uuid'])}", style="cyan"))
    task_tree.add(Text(f"Description: {task['description']}", style="bold"))

    # Handle the 'entry' date
    if "entry" in task:
        try:
            created_date = datetime.strptime(
                task["entry"], "%Y%m%dT%H%M%SZ"
            ).replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - created_date
            delta_str = f"{delta.days} days, {delta.seconds // 3600} hours ago"
            task_tree.add(
                Text(
                    f"Added on: {created_date.strftime('%Y-%m-%d %H:%M:%S')} ({delta_str})",
                    style="light_sea_green",
                )
            )
        except ValueError:
            task_tree.add(
                Text(f"Added on: {task['entry']}", style="light_sea_green")
            )

    # Handle the 'due' date
    if "due" in task:
        try:
            due_date = datetime.strptime(task["due"], "%Y%m%dT%H%M%SZ").replace(
                tzinfo=timezone.utc
            )
            delta = due_date - datetime.now(timezone.utc)
            if delta.total_seconds() < 0:
                delta_str = f"{abs(delta.days)} days, {abs(delta.seconds) // 3600} hours overdue"
                task_tree.add(
                    Text(
                        f"Due Date: {due_date.strftime('%Y-%m-%d %H:%M:%S')} ({delta_str})",
                        style="red",
                    )
                )
            else:
                delta_str = (
                    f"{delta.days} days, {delta.seconds // 3600} hours remaining"
                )
                task_tree.add(
                    Text(
                        f"Due Date: {due_date.strftime('%Y-%m-%d %H:%M:%S')} ({delta_str})",
                        style="light_green",
                    )
                )
        except ValueError:
            task_tree.add(Text(f"Due Date: {task['due']}", style="red"))

    if "project" in task:
        task_tree.add(Text(f"Project: {task['project']}", style="green"))

    if "tags" in task:
        task_tree.add(Text(f"Tags: {', '.join(task['tags'])}", style="yellow"))

    if "ctx" in task:
        task_tree.add(Text(f"Context: {task['ctx']}", style="magenta"))

    # Handle annotations
    annotations = task.get("annotations", [])
    if annotations:
        annotation_branch = task_tree.add(Text("Annotations:", style="white"))
        for annotation in annotations:
            entry_datetime = parse(annotation["entry"])
            if (
                entry_datetime.tzinfo is None
                or entry_datetime.tzinfo.utcoffset(entry_datetime) is None
            ):
                entry_datetime = entry_datetime.replace(tzinfo=timezone.utc)
            entry_datetime = entry_datetime.astimezone(timezone.utc)
            annotation_text = Text(
                f"{entry_datetime.strftime('%Y-%m-%d %H:%M:%S')} - {annotation['description']}",
                style="dim white",
            )
            annotation_branch.add(annotation_text)

    # Create a panel with the tree
    panel = Panel(
        task_tree,
        title="Task Details",
        border_style="blue",
        padding=(1, 1),
        expand=False,
    )

    # Print the panel
    console.print(panel)

def task_manager(
    task_uuid,
    get_tasks_fn,
    context_menu_fn,
    dependency_tree_fn,
    call_and_process_task_projects2_fn,
    search_project3_fn,
    display_tasks_fn,
    add_dependent_tasks_fn,
    manual_sort_dependencies_fn,
    remove_task_dependencies_fn,
    handle_task_fn,
    call_and_process_task_projects_fn,
    short_uuid_fn,
):
    console = Console()
    while True:
        tasks = get_tasks_fn(task_uuid)
        if not tasks:
            console.print(
                Panel("No tasks found with the provided UUID.", style="bold red")
            )
            return
        current_task = tasks[0]
        display_task_details2(current_task, short_uuid_fn)

        # Create a table for menu options
        table = Table(
            box=box.ROUNDED, expand=False, show_header=False, border_style="cyan"
        )
        table.add_column("Option", style="orange_red1")
        table.add_column("Description", style="cornflower_blue")

        # Add the existing options
        if "project" in current_task and current_task["project"]:
            table.add_row("CP", "Change project")
            table.add_row("AS", "Add Sub-tasks")
            table.add_row("DT", "View Dependency Tree")
            table.add_row("LT", "View logical tree")
            table.add_row("SD", "Set Dependency")
            table.add_row("RD", "Remove Dependency")
        else:
            table.add_row("AP", "Assign project")

        # Add the new "Update Context" option
        table.add_row("CM", "Context Menu")

        # Add the remaining options
        table.add_row("TW", "TW prompt")
        table.add_row("SP", "Search Project & Manage")
        table.add_row("SA", "Select Another Task")
        table.add_row("Enter", "Exit")

        console.print(Panel(table, title="Task Management Options", expand=False))
        choice = console.input("[yellow]Enter your choice: ").strip().lower()

        if choice == "cm":
            context_menu_fn(current_task)
        elif choice == "dt":
            if "project" in current_task and current_task["project"]:
                dependency_tree_fn(current_task["project"])
            else:
                console.print(
                    Panel(
                        "This task does not belong to any project.",
                        style="bold red",
                    )
                )
        elif choice in ["cp", "ap"]:
            tw = TaskWarrior()
            task = tw.get_task(uuid=task_uuid)
            project_list = call_and_process_task_projects2_fn()
            project = search_project3_fn(project_list)
            command = ["task", task_uuid, "modify", f"project:{project}"]
            subprocess.run(command, check=True)
            console.print(
                Panel(
                    f"Updated task {task_uuid} to project {project}.",
                    style="bold green",
                )
            )
        elif choice == "lt":
            if "project" in current_task and current_task["project"]:
                display_tasks_fn(f"task pro:{current_task['project']} +PENDING export")
            else:
                console.print(
                    Panel("No project associated with this task.", style="bold red")
                )
        elif choice == "as":
            add_dependent_tasks_fn(
                current_task["description"],
                current_task.get("project", ""),
                current_task["uuid"],
            )
            if "project" in current_task and current_task["project"]:
                dependency_tree_fn(
                    current_task["project"]
                )  # refresh the dependency tree
        elif choice == "sd":
            # dependency_input = console.input("Enter the tasks and their dependencies in the format 'ID>ID>ID, ID>ID':\n")
            manual_sort_dependencies_fn("")
            if "project" in current_task and current_task["project"]:
                dependency_tree_fn(
                    current_task["project"]
                )  # refresh the dependency tree
        elif choice == "rd":
            task_ids_input = console.input(
                "Enter the IDs of the tasks to remove dependencies (comma-separated):\n"
            )
            remove_task_dependencies_fn(task_ids_input)
            if "project" in current_task and current_task["project"]:
                dependency_tree_fn(
                    current_task["project"]
                )  # refresh the dependency tree
        elif choice == "tw":
            handle_task_fn()
        elif choice == "sp":
            call_and_process_task_projects_fn()
        elif choice == "sa":
            new_task = console.input("Enter the IDs of the new task to load:\n")
            tasks = get_tasks_fn(new_task)
            if not tasks:
                console.print(
                    Panel(
                        "No tasks found with the provided UUID.", style="bold red"
                    )
                )
                return
            current_task = tasks[0]
        elif choice == "":
            console.print(Panel("Exiting task manager.", style="bold green"))
            break
        else:
            console.print(
                Panel("Invalid choice. Please try again.", style="bold red")
            )

        # Refresh the task details after each operation
        task_uuid = current_task["uuid"]
