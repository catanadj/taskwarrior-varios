"""Context management commands for TaskVarios."""

import subprocess

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

try:
    import ujson as json
except ImportError:
    import json


def get_task_selection_for_context():
    """Helper function to get task selection for context operations."""
    console = Console()

    console.print("\nTask Selection Options:")
    console.print("1. All pending tasks")
    console.print("2. Tasks by filter (e.g., project:work)")
    console.print("3. Specific task IDs")

    choice = console.input("Choose selection method (1-3): ")

    if choice == "1":
        command = ["task", "status:pending", "export"]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    if choice == "2":
        filter_str = console.input("Enter task filter: ")
        command = ["task", filter_str, "export"]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError:
            console.print(Panel("Invalid filter.", style="bold red"))
            return []
    if choice == "3":
        ids_str = console.input("Enter task IDs (comma-separated): ")
        task_ids = [task_id.strip() for task_id in ids_str.split(",")]
        tasks = []
        for task_id in task_ids:
            try:
                command = ["task", f"id:{task_id}", "export"]
                result = subprocess.run(command, capture_output=True, text=True, check=True)
                task_data = json.loads(result.stdout)
                if task_data:
                    tasks.extend(task_data)
            except subprocess.CalledProcessError:
                console.print(f"Task ID {task_id} not found.", style="bold yellow")
        return tasks

    console.print(Panel("Invalid choice.", style="bold red"))
    return []


def get_all_unique_contexts():
    """Get all unique contexts from all tasks."""
    command = ["task", "status:pending", "export"]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    tasks = json.loads(result.stdout)

    contexts = set()
    for task in tasks:
        task_contexts = task.get("ctx", "").split(",")
        for context in task_contexts:
            context = context.strip()
            if context:
                contexts.add(context)

    return sorted(list(contexts))


def remove_context_from_all_tasks(context_to_remove):
    """Remove a specific context from all tasks that have it."""
    command = ["task", "status:pending", "export"]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    tasks = json.loads(result.stdout)

    removed_count = 0
    for task in tasks:
        current_context = task.get("ctx", "")
        if context_to_remove in current_context:
            existing_contexts = [
                ctx.strip() for ctx in current_context.split(",") if ctx.strip()
            ]
            if context_to_remove in existing_contexts:
                existing_contexts.remove(context_to_remove)
                new_context_string = ",".join(existing_contexts)
                command = ["task", task["uuid"], "modify", f"ctx:{new_context_string}"]
                subprocess.run(command, check=True)
                removed_count += 1

    return removed_count


def rename_context_across_tasks():
    """Rename a context across all tasks."""
    console = Console()
    all_contexts = get_all_unique_contexts()

    if not all_contexts:
        console.print(Panel("No contexts found.", style="bold yellow"))
        return

    console.print("Available contexts:")
    for index, ctx in enumerate(all_contexts, 1):
        console.print(f"{index}. {ctx}")

    old_choice = console.input("Enter the number or name of the context to rename: ")

    old_context = None
    if old_choice.isdigit() and 1 <= int(old_choice) <= len(all_contexts):
        old_context = all_contexts[int(old_choice) - 1]
    elif old_choice in all_contexts:
        old_context = old_choice
    else:
        console.print(Panel("Invalid choice.", style="bold red"))
        return

    new_context = console.input(f"Enter new name for '{old_context}': ").strip()
    if not new_context:
        console.print(Panel("No new name entered.", style="bold yellow"))
        return

    command = ["task", "status:pending", "export"]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    tasks = json.loads(result.stdout)

    renamed_count = 0
    for task in tasks:
        current_context = task.get("ctx", "")
        if old_context in current_context:
            existing_contexts = [
                ctx.strip() for ctx in current_context.split(",") if ctx.strip()
            ]
            if old_context in existing_contexts:
                idx = existing_contexts.index(old_context)
                existing_contexts[idx] = new_context
                new_context_string = ",".join(existing_contexts)
                command = ["task", task["uuid"], "modify", f"ctx:{new_context_string}"]
                subprocess.run(command, check=True)
                renamed_count += 1

    console.print(
        Panel(
            f"Renamed '{old_context}' to '{new_context}' in {renamed_count} task(s).",
            style="bold green",
        )
    )


def merge_contexts():
    """Merge two contexts into one."""
    console = Console()
    all_contexts = get_all_unique_contexts()

    if len(all_contexts) < 2:
        console.print(Panel("Need at least 2 contexts to merge.", style="bold yellow"))
        return

    console.print("Available contexts:")
    for index, ctx in enumerate(all_contexts, 1):
        console.print(f"{index}. {ctx}")

    source_choice = console.input(
        "Enter the number or name of the context to merge FROM: "
    )
    source_context = None
    if source_choice.isdigit() and 1 <= int(source_choice) <= len(all_contexts):
        source_context = all_contexts[int(source_choice) - 1]
    elif source_choice in all_contexts:
        source_context = source_choice
    else:
        console.print(Panel("Invalid choice.", style="bold red"))
        return

    target_choice = console.input("Enter the number or name of the context to merge TO: ")
    target_context = None
    if target_choice.isdigit() and 1 <= int(target_choice) <= len(all_contexts):
        target_context = all_contexts[int(target_choice) - 1]
    elif target_choice in all_contexts:
        target_context = target_choice
    else:
        console.print(Panel("Invalid choice.", style="bold red"))
        return

    if source_context == target_context:
        console.print(Panel("Cannot merge a context with itself.", style="bold red"))
        return

    command = ["task", "status:pending", "export"]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    tasks = json.loads(result.stdout)

    merged_count = 0
    for task in tasks:
        current_context = task.get("ctx", "")
        if source_context in current_context:
            existing_contexts = [
                ctx.strip() for ctx in current_context.split(",") if ctx.strip()
            ]
            if source_context in existing_contexts:
                existing_contexts.remove(source_context)
                if target_context not in existing_contexts:
                    existing_contexts.append(target_context)
                new_context_string = ",".join(existing_contexts)
                command = ["task", task["uuid"], "modify", f"ctx:{new_context_string}"]
                subprocess.run(command, check=True)
                merged_count += 1

    console.print(
        Panel(
            f"Merged '{source_context}' into '{target_context}' for {merged_count} task(s).",
            style="bold green",
        )
    )


def remove_context_from_all_tasks_interactive():
    """Interactive version of removing context from all tasks."""
    console = Console()
    all_contexts = get_all_unique_contexts()

    if not all_contexts:
        console.print(Panel("No contexts found.", style="bold yellow"))
        return

    console.print("Available contexts:")
    for index, ctx in enumerate(all_contexts, 1):
        console.print(f"{index}. {ctx}")

    choice = console.input(
        "Enter the number or name of the context to remove from all tasks: "
    )

    context_to_remove = None
    if choice.isdigit() and 1 <= int(choice) <= len(all_contexts):
        context_to_remove = all_contexts[int(choice) - 1]
    elif choice in all_contexts:
        context_to_remove = choice
    else:
        console.print(Panel("Invalid choice.", style="bold red"))
        return

    confirm = console.input(
        f"Are you sure you want to remove '{context_to_remove}' from ALL tasks? (y/N): "
    )
    if confirm.lower() != "y":
        console.print(Panel("Operation cancelled.", style="bold yellow"))
        return

    removed_count = remove_context_from_all_tasks(context_to_remove)
    console.print(
        Panel(
            f"Removed '{context_to_remove}' from {removed_count} task(s).",
            style="bold green",
        )
    )


def add_context_to_multiple_tasks():
    """Add a context to multiple selected tasks."""
    console = Console()

    new_context = console.input("Enter the context to add: ").strip()
    if not new_context:
        console.print(Panel("No context entered.", style="bold yellow"))
        return

    task_selection = get_task_selection_for_context()
    if not task_selection:
        return

    added_count = 0
    for task in task_selection:
        current_context = task.get("ctx", "")
        existing_contexts = current_context.split(",") if current_context else []
        existing_contexts = [ctx.strip() for ctx in existing_contexts if ctx.strip()]

        if new_context not in existing_contexts:
            existing_contexts.append(new_context)
            new_context_string = ",".join(existing_contexts)
            command = ["task", task["uuid"], "modify", f"ctx:{new_context_string}"]
            subprocess.run(command, check=True)
            added_count += 1

    console.print(
        Panel(f"Added '{new_context}' to {added_count} task(s).", style="bold green")
    )


def view_task_contexts(task):
    """View contexts for a specific task."""
    console = Console()
    current_context = task.get("ctx", "")

    if current_context:
        contexts = [ctx.strip() for ctx in current_context.split(",") if ctx.strip()]
        console.print(
            f"\nContexts for task {task.get('id', task.get('uuid'))}: "
            f"{task.get('description', 'No description')}"
        )
        for index, ctx in enumerate(contexts, 1):
            console.print(f"  {index}. {ctx}")
    else:
        console.print(
            f"\nTask {task.get('id', task.get('uuid'))} has no contexts assigned."
        )

    console.input("\nPress Enter to continue...")


def view_all_contexts():
    """Show all contexts and associated tasks."""
    console = Console()

    command = ["task", "status:pending", "export"]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    tasks = json.loads(result.stdout)

    context_data = {}
    for task in tasks:
        contexts = task.get("ctx", "").split(",")
        for context in contexts:
            context = context.strip()
            if context:
                if context not in context_data:
                    context_data[context] = {"count": 0, "tasks": []}
                context_data[context]["count"] += 1
                context_data[context]["tasks"].append(
                    (task["id"], task.get("description", "No description"))
                )

    table = Table(title="All Contexts in Use", box=box.ROUNDED)
    table.add_column("Context", style="cyan")
    table.add_column("#", style="magenta")
    table.add_column("Task IDs and Descriptions", style="green")

    for context, data in sorted(
        context_data.items(), key=lambda item: item[1]["count"], reverse=True
    ):
        task_info = ", ".join([f"{task_id}, {desc}\n" for task_id, desc in data["tasks"]])
        table.add_row(context, str(data["count"]), task_info)

    console.print(table)
    console.input("\nPress Enter to return to the Context Menu...")


def add_context(task=None):
    """Add context to a single task or a selected set of tasks."""
    console = Console()

    if task:
        current_context = task.get("ctx", "")
        console.print(
            f"Current context for task {task.get('id', task.get('uuid'))}: "
            f"{current_context}"
        )

        new_context = console.input("Enter the context to add: ").strip()
        existing_contexts = current_context.split(",") if current_context else []

        if new_context and new_context not in existing_contexts:
            existing_contexts.append(new_context)
            new_context_string = ",".join(existing_contexts)
            command = ["task", task["uuid"], "modify", f"ctx:{new_context_string}"]
            subprocess.run(command, check=True)
            console.print(
                Panel(
                    f"Updated task context to: {new_context_string}", style="bold green"
                )
            )
        else:
            console.print(
                Panel(
                    "Context already exists or invalid input. No changes made.",
                    style="bold yellow",
                )
            )
        return

    new_context = console.input("Enter the context to add: ").strip()
    if not new_context:
        console.print(Panel("No context entered.", style="bold yellow"))
        return

    task_selection = get_task_selection_for_context()
    if not task_selection:
        return

    for selected_task in task_selection:
        current_context = selected_task.get("ctx", "")
        existing_contexts = current_context.split(",") if current_context else []

        if new_context not in existing_contexts:
            existing_contexts.append(new_context)
            new_context_string = ",".join(existing_contexts)
            command = ["task", selected_task["uuid"], "modify", f"ctx:{new_context_string}"]
            subprocess.run(command, check=True)
            console.print(
                Panel(
                    f"Added '{new_context}' to task {selected_task.get('id')}: "
                    f"{selected_task.get('description', 'No description')[:50]}...",
                    style="bold green",
                )
            )


def remove_context(task=None):
    """Remove context from a single task or from all tasks."""
    console = Console()

    if task:
        current_context = task.get("ctx", "")
        console.print(
            f"Current context for task {task.get('id', task.get('uuid'))}: "
            f"{current_context}"
        )

        existing_contexts = current_context.split(",") if current_context else []
        if not existing_contexts:
            console.print(Panel("No contexts to remove.", style="bold yellow"))
            return

        console.print("Existing contexts:")
        for index, ctx in enumerate(existing_contexts, 1):
            console.print(f"{index}. {ctx}")

        choice = console.input(
            "Enter the number of the context to remove or type the context name: "
        )
        if choice.isdigit() and 1 <= int(choice) <= len(existing_contexts):
            existing_contexts.pop(int(choice) - 1)
        elif choice in existing_contexts:
            existing_contexts.remove(choice)
        else:
            console.print(Panel("Invalid choice. No context removed.", style="bold red"))
            return

        new_context_string = ",".join(existing_contexts)
        command = ["task", task["uuid"], "modify", f"ctx:{new_context_string}"]
        subprocess.run(command, check=True)
        console.print(
            Panel(f"Updated task context to: {new_context_string}", style="bold green")
        )
        return

    all_contexts = get_all_unique_contexts()
    if not all_contexts:
        console.print(Panel("No contexts found.", style="bold yellow"))
        return

    console.print("Available contexts:")
    for index, ctx in enumerate(all_contexts, 1):
        console.print(f"{index}. {ctx}")

    choice = console.input("Enter the number or name of the context to remove: ")

    context_to_remove = None
    if choice.isdigit() and 1 <= int(choice) <= len(all_contexts):
        context_to_remove = all_contexts[int(choice) - 1]
    elif choice in all_contexts:
        context_to_remove = choice
    else:
        console.print(Panel("Invalid choice.", style="bold red"))
        return

    removed_count = remove_context_from_all_tasks(context_to_remove)
    console.print(
        Panel(
            f"Removed '{context_to_remove}' from {removed_count} task(s).",
            style="bold green",
        )
    )


def manage_contexts_across_tasks():
    """Advanced context management across multiple tasks."""
    console = Console()

    while True:
        console.print(Panel("Advanced Context Management", style="bold magenta"))
        table = Table(
            box=box.ROUNDED,
            expand=False,
            show_header=False,
            border_style="magenta",
        )
        table.add_column("Option", style="orange_red1")
        table.add_column("Description", style="cornflower_blue")
        table.add_row("1", "Rename Context Across All Tasks")
        table.add_row("2", "Merge Two Contexts")
        table.add_row("3", "Remove Context from All Tasks")
        table.add_row("4", "Add Context to Multiple Tasks")
        table.add_row("Enter", "Return to Context Menu")

        console.print(table)
        choice = console.input("[yellow]Enter your choice: ")

        if choice == "1":
            rename_context_across_tasks()
        elif choice == "2":
            merge_contexts()
        elif choice == "3":
            remove_context_from_all_tasks_interactive()
        elif choice == "4":
            add_context_to_multiple_tasks()
        elif choice == "":
            break
        else:
            console.print(Panel("Invalid choice. Please try again.", style="bold red"))


def display_context_overview():
    """Display an A-Z overview of all contexts with hierarchical grouping."""
    console = Console()

    command = ["task", "status:pending", "export"]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    tasks = json.loads(result.stdout)

    context_counts = {}
    for task in tasks:
        contexts = task.get("ctx", "").split(",")
        for context in contexts:
            context = context.strip()
            if context:
                context_counts[context] = context_counts.get(context, 0) + 1

    if not context_counts:
        console.print(Panel("No contexts found in any tasks.", style="bold yellow"))
        return

    hierarchical_contexts = {}
    standalone_contexts = {}

    for context, count in context_counts.items():
        if ":" in context:
            prefix, suffix = context.split(":", 1)
            if prefix not in hierarchical_contexts:
                hierarchical_contexts[prefix] = {}
            hierarchical_contexts[prefix][suffix] = count
        else:
            standalone_contexts[context] = count

    table = Table(title="🏷️  Context Overview (A-Z)", box=box.ROUNDED, expand=True)
    table.add_column("Context", style="cyan bold", width=25)
    table.add_column("Count", style="magenta", justify="center", width=8)
    table.add_column("Details", style="green")

    all_items = []

    for prefix, subcategories in hierarchical_contexts.items():
        total_count = sum(subcategories.values())
        subcategory_details = []
        for suffix, count in sorted(subcategories.items()):
            subcategory_details.append(f"{suffix} ({count})")

        details = f"├─ {' ├─ '.join(subcategory_details)}"
        all_items.append((prefix, total_count, details, True))

    for context, count in standalone_contexts.items():
        all_items.append((context, count, "─", False))

    all_items.sort(key=lambda item: item[0].lower())

    for context, count, details, is_hierarchical in all_items:
        if is_hierarchical:
            table.add_row(f"📁 [bold]{context}[/bold]", f"[bold]{count}[/bold]", details)
        else:
            table.add_row(f"📄 {context}", str(count), details)

    console.print(table)
    console.print()


def context_menu(task=None):
    """Main context menu entrypoint."""
    console = Console()
    while True:
        title = (
            f"Context Menu - Task {task.get('id', task.get('uuid', 'Unknown'))}"
            if task
            else "Context Menu - All Tasks"
        )
        console.print(Panel(title, style="bold cyan"))

        if not task:
            display_context_overview()

        table = Table(
            box=box.ROUNDED,
            expand=False,
            show_header=False,
            border_style="cyan",
        )
        table.add_column("Option", style="orange_red1")
        table.add_column("Description", style="cornflower_blue")

        if task:
            table.add_row("AC", "Add Context to This Task")
            table.add_row("RC", "Remove Context from This Task")
            table.add_row("VC", "View This Task's Contexts")
        else:
            table.add_row("AC", "Add Context to Task(s)")
            table.add_row("RC", "Remove Context from Task(s)")
            table.add_row("MC", "Manage Context Across Tasks")

        table.add_row("VAC", "View All Contexts")
        table.add_row("Enter", "Return to Main Menu")

        console.print(table)

        if not task:
            console.print(
                "\n[italic dim]When you're in a certain context, to be the most "
                "efficient, you need to see all the things that could be done in "
                "that context.[/italic dim]\n"
            )

        choice = console.input("[yellow]Enter your choice: ").upper()

        if choice == "AC":
            add_context(task)
        elif choice == "RC":
            remove_context(task)
        elif choice == "VC" and task:
            view_task_contexts(task)
        elif choice == "MC" and not task:
            manage_contexts_across_tasks()
        elif choice == "VAC":
            view_all_contexts()
        elif choice == "":
            break
        else:
            console.print(Panel("Invalid choice. Please try again.", style="bold red"))
