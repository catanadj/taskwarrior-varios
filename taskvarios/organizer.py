"""Task organizer workflow extracted from TaskVarios."""

from collections import defaultdict
from datetime import datetime, timedelta
from itertools import groupby
import logging
import os
import re
import subprocess

import pytz
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from taskvarios.constants import colors, local_tz

try:
    import ujson as json
except ImportError:
    import json

logger = logging.getLogger(__name__)


def task_organizer(
    handle_task_fn, next_summary_fn, display_overdue_tasks_fn, base_dir=None
):
    from datetime import time

    task_id_pattern = re.compile(r"^\d+$")
    time_pattern = re.compile(r"^\d{2}:\d{2}$")
    shift_pattern = re.compile(r"^[+-]\d+[a-zA-Z]+$")

    def localize_time(value: datetime) -> datetime:
        if hasattr(local_tz, "localize"):
            return local_tz.localize(value)
        return value.replace(tzinfo=local_tz)

    def parse_export_stdout(stdout: str):
        try:
            return json.loads(stdout or "[]")
        except ValueError:
            return []

    def run_task_modify(task_id: str, *modifiers: str):
        result = subprocess.run(
            ["task", "rc.confirmation=off", task_id, "modify", *modifiers],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                "Task modify failed for task_id=%s modifiers=%s stderr=%s",
                task_id,
                modifiers,
                result.stderr.strip(),
            )
        return result

    def valid_task_id(value: str) -> bool:
        return bool(task_id_pattern.match(value.strip()))

    def valid_time(value: str) -> bool:
        if not time_pattern.match(value):
            return False
        try:
            datetime.strptime(value, "%H:%M")
        except ValueError:
            return False
        return True

    def get_tasks_for_day(date):
        result = subprocess.run(
            ["task", f"due:{date}", "status:pending", "export"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.warning("Task export failed for due:%s: %s", date, result.stderr.strip())
            return []
        tasks = parse_export_stdout(result.stdout)
        return sorted(tasks, key=lambda x: x.get("due", ""))

    def parse_duration(duration_str):
        total_minutes = 0.0
        if "Y" in duration_str:
            total_minutes += (
                float(re.search(r"(\d+)Y", duration_str).group(1)) * 525600
            )  # Approximate, doesn't account for leap years
        if "M" in duration_str and "T" not in duration_str:
            total_minutes += (
                float(re.search(r"(\d+)M", duration_str).group(1)) * 43800
            )  # Approximate, assumes 30-day months
        if "D" in duration_str:
            total_minutes += (
                float(re.search(r"(\d+)D", duration_str).group(1)) * 1440
            )
        if "H" in duration_str:
            total_minutes += float(re.search(r"(\d+)H", duration_str).group(1)) * 60
        if "M" in duration_str and "T" in duration_str:
            total_minutes += float(re.search(r"(\d+)M", duration_str).group(1))
        if "S" in duration_str:
            total_minutes += float(re.search(r"(\d+)S", duration_str).group(1)) / 60
        return total_minutes

    def format_duration(minutes):
        hours, mins = divmod(round(minutes), 60)
        return f"{int(hours):02d}:{int(mins):02d}"

    class TaskOrganizer:
        def __init__(self):
            self.console = Console()
            self.current_date = (datetime.now() + timedelta(days=1)).date()
            self.all_pending_tasks = []
            self.refresh_tasks()
            script_directory = base_dir or os.path.dirname(os.path.abspath(__file__))
            self.notes_file = os.path.join(script_directory, "daily_notes.jsonl")
            self.load_notes()

        def load_notes(self):
            self.notes = {}
            if os.path.exists(self.notes_file):
                with open(self.notes_file, "r") as f:
                    for line in f:
                        note = json.loads(line.strip())
                        date_str = note["date"]
                        if date_str not in self.notes:
                            self.notes[date_str] = []
                        if "color" not in note:
                            note["color"] = (
                                "cyan"  # Set default color for old notes
                            )
                        self.notes[date_str].append(note)

        def save_notes(self):
            with open(self.notes_file, "w") as f:
                for date_notes in self.notes.values():
                    for note in date_notes:
                        json.dump(note, f)
                        f.write("\n")

        def add_note(self, time, note, until="noend", color="cyan"):
            date_str = datetime.now().strftime("%Y-%m-%d")
            if date_str not in self.notes:
                self.notes[date_str] = []

            max_index = max(
                [
                    max([n["index"] for n in date_notes] + [-1])
                    for date_notes in self.notes.values()
                ]
                + [-1]
            )
            new_index = max_index + 1

            new_note = {
                "date": date_str,
                "index": new_index,
                "time": time,
                "content": note,
                "until": until,
                "color": color,
            }
            self.notes[date_str].append(new_note)
            self.save_notes()
            return new_index

        def create_compact_view(self):
            start_of_day = datetime.combine(self.current_date, datetime.min.time())
            start_of_day = localize_time(start_of_day)
            end_of_day = start_of_day.replace(hour=23, minute=59, second=59)
            project_counts = self.get_pending_counts("projects")
            tag_counts = self.get_pending_counts("tags")

            # Sort tasks by due time
            sorted_tasks = sorted(
                self.tasks,
                key=lambda x: datetime.strptime(x["due"], "%Y%m%dT%H%M%SZ"),
            )

            table = Table(
                title=f"Tasks for {self.current_date.strftime('%Y-%m-%d')}",
                expand=True,
            )
            table.add_column("Time", style="cyan", no_wrap=True)
            table.add_column("Duration", style="white")
            table.add_column("Task", style="white")
            table.add_column("Project", style="blue")
            table.add_column("Tags", style="yellow")

            current_time = start_of_day

            # Group tasks by their start time
            grouped_tasks = []
            for key, group in groupby(
                sorted_tasks,
                key=lambda x: datetime.strptime(x["due"], "%Y%m%dT%H%M%SZ")
                .replace(tzinfo=pytz.UTC)
                .astimezone(local_tz),
            ):
                group_list = list(group)
                total_duration = sum(
                    parse_duration(task.get("duration", "PT60M"))
                    for task in group_list
                )
                grouped_tasks.append((key, group_list, total_duration))

            for task_time, tasks, total_duration in grouped_tasks:
                # Add free time if there's a gap
                if task_time > current_time:
                    free_time = (task_time - current_time).total_seconds() / 60
                    if free_time > 0:
                        table.add_row(
                            current_time.strftime("%H:%M"),
                            format_duration(free_time),
                            "Free Time",
                            "",
                            "",
                            style="turquoise4",
                        )

                # Add each task in the group individually
                for i, task in enumerate(tasks):
                    task_duration = parse_duration(task.get("duration", "PT60M"))
                    task_description = f"{task['id']}, {task['description']}"
                    table.add_row(
                        (
                            task_time.strftime("%H:%M") if i == 0 else ""
                        ),  # Only show time for the first task in the group
                        format_duration(task_duration),
                        task_description,
                        task.get("project", ""),
                        ", ".join(task.get("tags", [])),
                    )

                current_time = task_time + timedelta(minutes=total_duration)

            # Add any remaining free time at the end of the day
            if current_time < end_of_day:
                final_free_time = (end_of_day - current_time).total_seconds() / 60
                if final_free_time > 0:
                    table.add_row(
                        current_time.strftime("%H:%M"),
                        format_duration(final_free_time),
                        "Free Time",
                        "",
                        "",
                        style="dim",
                    )

            return table

        def display_compact_view(self):
            date_panel = self.create_date_panel()
            self.console.print(date_panel)

            compact_view = self.create_compact_view()
            self.console.print(compact_view)

            notes_panel = self.create_notes_panel()
            self.console.print(notes_panel)

        def run(self):
            view_mode = "calendar"  # Default view mode
            while True:
                self.console.clear()
                if view_mode == "calendar":
                    self.display_calendar_view()
                else:
                    self.display_compact_view()
                self.display_menu()
                choice = self.console.input("[yellow]Enter your choice: ")
                self.process_command(choice)
                if choice.lower() == "v":
                    view_mode = "compact" if view_mode == "calendar" else "calendar"
                self.refresh_tasks()

        def remove_note(self, index):
            for date_str, date_notes in self.notes.items():
                self.notes[date_str] = [
                    note for note in date_notes if note["index"] != index
                ]
            self.save_notes()

        def edit_note(self, index, new_content, new_color=None):
            for date_notes in self.notes.values():
                for note in date_notes:
                    if note["index"] == index:
                        note["content"] = new_content
                        if new_color:
                            note["color"] = new_color
                        self.save_notes()
                        return

        def get_notes_for_day(self):
            all_notes = []
            for date_str, date_notes in self.notes.items():
                note_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                for note in date_notes:
                    if (
                        note["until"] == "noend"
                        or datetime.strptime(note["until"], "%Y-%m-%d").date()
                        >= self.current_date
                    ):
                        if note_date <= self.current_date:
                            all_notes.append(note)
            return sorted(all_notes, key=lambda x: (x["time"], x["index"]))

        # def run(self):
        # 	while True:
        # 		self.console.clear()
        # 		self.display_calendar_view()
        # 		self.display_menu()
        # 		choice = self.console.input("[yellow]Enter your choice: ")
        # 		self.process_command(choice)
        # 		self.display_notes_panel()
        # 		self.refresh_tasks()

        def display_calendar_view(self):
            calendar_view = self.create_calendar_view()
            for item in calendar_view:
                if isinstance(item, str):
                    self.console.print(item, end="")
                else:
                    self.console.print(item)

        def display_menu(self):
            table = Table(
                box=box.ROUNDED,
                expand=False,
                show_header=False,
                border_style="cyan",
            )
            table.add_column("Option", style="orange_red1")
            table.add_column("Description", style="turquoise2")

            table.add_row("MV", "Move task")
            table.add_row("D", "Change duration")
            table.add_row("R", "Refresh")
            table.add_row("S", "Shift task")
            table.add_row("CD", "Select day")
            table.add_row("AD", "Add task")
            table.add_row("AS", "Arrange tasks by duration or value")
            table.add_row("TW", "TW prompt")
            table.add_row("V", "Toggle view (Calendar/Compact)")
            table.add_row("B", "Go back one day")
            table.add_row("F", "Go forward one day")
            table.add_row("", "Exit")
            table.add_row("==", "Note Options:")
            table.add_row("AN", "Add note")
            table.add_row("RN", "Remove note")
            table.add_row("EN", "Edit note")

            title = f"{self.current_date.strftime('%Y-%m-%d')}"
            self.console.print(Panel(table, title=title, expand=False))

        def process_command(self, choice):
            choice = choice.strip().lower()

            if choice == "n":
                self.note_options()
            elif choice == "mv":
                task_ids = self.console.input(
                    "[yellow]Enter task ID(s) separated by commas: "
                ).split(",")
                new_time = self.console.input("[yellow]Enter new time (HH:MM): ")
                for task_id in task_ids:
                    self.move_task(task_id.strip(), new_time)
            elif choice == "v":
                pass  #
            elif choice == "d":
                task_ids = self.console.input(
                    "[yellow]Enter task ID(s) separated by commas: "
                ).split(",")
                new_duration = self.console.input(
                    "[yellow]Enter new duration (e.g., 1h30m): "
                )
                for task_id in task_ids:
                    self.change_duration(task_id.strip(), new_duration)
            elif choice == "r":
                self.refresh_tasks()
            elif choice == "s":
                shift_input = self.console.input(
                    "[yellow]Enter task ID(s) and shift duration (e.g., '321,322 +15min' or '321,322 -1h'): "
                )
                try:
                    task_ids, shift_duration = shift_input.split(maxsplit=1)
                except ValueError:
                    self.console.print(
                        "Invalid input format. Use '321,322 +15min'.", style="bold red"
                    )
                    return
                for task_id in task_ids.split(","):
                    self.shift_task(f"{task_id.strip()} {shift_duration}")
            elif choice == "cd":
                date = self.console.input(
                    "[yellow]Enter date (YYYY-MM-DD) or 'today' or 'tomorrow': "
                )
                self.select_day(date)
            elif choice == "ad":
                self.add_task()
            elif choice == "tw":
                handle_task_fn()
            elif choice == "b":
                self.current_date -= timedelta(days=1)
                self.refresh_tasks()
            elif choice == "f":
                self.current_date += timedelta(days=1)
                self.refresh_tasks()
            elif choice == "an":
                self.add_note_option()
            elif choice == "rn":
                self.remove_note_option()
            elif choice == "en":
                self.edit_note_option()
            elif choice == "as":
                self.arrange_tasks()
            elif choice == "":
                exit()
            else:
                self.console.print(f"Unknown command: {choice}", style="bold red")

        def arrange_tasks(self):
            sort_by = self.console.input(
                "[yellow]Sort tasks by (D)uration or (V)alue: "
            ).lower()
            if sort_by not in ["d", "v"]:
                self.console.print(
                    "Invalid choice. Task arrangement cancelled.", style="bold red"
                )
                return

            task_ids = self.console.input(
                "[yellow]Enter task IDs separated by commas (or 'all' for all tasks): "
            )
            if task_ids.lower() == "all":
                tasks_to_arrange = self.tasks
            else:
                task_id_list = [task_id.strip() for task_id in task_ids.split(",")]
                tasks_to_arrange = [
                    task for task in self.tasks if str(task["id"]) in task_id_list
                ]
            if not tasks_to_arrange:
                self.console.print("No tasks selected.", style="bold red")
                return

            start_time = self.console.input("[yellow]Enter start time (HH:MM): ")
            try:
                start_time_dt = datetime.strptime(start_time, "%H:%M").time()
            except ValueError:
                self.console.print(
                    "Invalid time format. Task arrangement cancelled.",
                    style="bold red",
                )
                return

            # Combine date and time, and then localize to the specified timezone
            current_time = datetime.combine(self.current_date, start_time_dt)
            current_time = localize_time(current_time)

            if sort_by == "d":
                sorted_tasks = sorted(
                    tasks_to_arrange,
                    key=lambda x: parse_duration(x.get("duration", "PT60M")),
                    reverse=True,
                )
            elif sort_by == "v":
                sorted_tasks = sorted(
                    tasks_to_arrange,
                    key=lambda x: float(x.get("value", 0)),
                    reverse=True,
                )

            for task in sorted_tasks:
                task_duration = parse_duration(task.get("duration", "PT60M"))
                due_time = current_time.astimezone(pytz.utc).strftime(
                    "%Y%m%dT%H%M%SZ"
                )  # Convert to UTC for taskwarrior
                run_task_modify(str(task["id"]), f"due:{due_time}")
                self.console.print(
                    f"Task {task['id']} arranged at {current_time.strftime('%H:%M %Z')}",
                    style="bold green",
                )
                current_time += timedelta(minutes=task_duration)

        def note_options(self):
            option = self.console.input(
                "[yellow]Choose note action (AN add, RN remove, EN edit): "
            ).strip().lower()
            if option == "an":
                self.add_note_option()
            elif option == "rn":
                self.remove_note_option()
            elif option == "en":
                self.edit_note_option()
            else:
                self.console.print("Unknown note option.", style="bold red")

        def add_note_option(self):
            time = self.console.input(
                "[yellow]Enter time for the note (HH:MM) or press Enter for current time: "
            )
            if not time:
                time = datetime.now().strftime("%H:%M")

            self.console.print("[yellow]Enter note (press Enter twice to finish):")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            note = "\n".join(lines)

            until = self.console.input(
                "[yellow]Enter 'until' date (YYYY-MM-DD) or press Enter for today's date: "
            )
            if not until:
                until = self.current_date.strftime("%Y-%m-%d")

            color = self.console.input(
                "[yellow]Enter note color (or press Enter for default cyan): "
            )
            if not color:
                color = "cyan"

            index = self.add_note(time, note, until, color)
            self.console.print(f"Note added with index {index}", style="bold green")

        def remove_note_option(self):
            index = int(self.console.input("[yellow]Enter note index to remove: "))
            self.remove_note(index)
            self.console.print(
                f"Note with index {index} removed", style="bold green"
            )

        def edit_note_option(self):
            index = int(self.console.input("[yellow]Enter note index to edit: "))
            self.console.print(
                "[yellow]Enter new note content (press Enter twice to finish):"
            )
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            new_content = "\n".join(lines)

            new_color = self.console.input(
                "[yellow]Enter new color (or press Enter to keep current color): "
            )

            self.edit_note(index, new_content, new_color if new_color else None)
            self.console.print(
                f"Note with index {index} edited", style="bold green"
            )

        def move_task(self, task_id, new_time):
            task_id = task_id.strip()
            if not valid_task_id(task_id):
                self.console.print(f"Invalid task id: {task_id}", style="bold red")
                return
            if not valid_time(new_time):
                self.console.print("Invalid time format (HH:MM).", style="bold red")
                return
            run_task_modify(task_id, f"due:{self.current_date}T{new_time}")
            self.console.print(
                f"Task {task_id} moved to {new_time}", style="bold green"
            )

        def change_duration(self, task_id, new_duration):
            task_id = task_id.strip()
            if not valid_task_id(task_id):
                self.console.print(f"Invalid task id: {task_id}", style="bold red")
                return
            run_task_modify(task_id, f"duration:{new_duration}")
            self.console.print(
                f"Duration for task {task_id} set to {new_duration}",
                style="bold green",
            )

        def shift_task(self, shift_input):
            try:
                task_id, shift_duration = shift_input.split(maxsplit=1)
                task_id = task_id.strip()
                shift_duration = shift_duration.strip()
                if not valid_task_id(task_id):
                    self.console.print(f"Invalid task id: {task_id}", style="bold red")
                    return
                if not shift_pattern.match(shift_duration):
                    self.console.print(
                        "Invalid shift duration. Use values like +15min or -1h.",
                        style="bold red",
                    )
                    return
                run_task_modify(task_id, f"due:due{shift_duration}")
                self.console.print(
                    f"Task {task_id} shifted by {shift_duration}",
                    style="bold green",
                )
            except ValueError:
                self.console.print(
                    "Invalid input format. Please use 'TASK_ID DURATION' (e.g., '321 +15min').",
                    style="bold red",
                )

        def select_day(self, date):
            if date.lower() == "today":
                self.current_date = datetime.now().date()
            elif date.lower() == "tomorrow":
                self.current_date = datetime.now().date() + timedelta(days=1)
            else:
                try:
                    self.current_date = datetime.strptime(date, "%Y-%m-%d").date()
                except ValueError:
                    self.console.print(
                        "Invalid date format. Please use YYYY-MM-DD.",
                        style="bold red",
                    )
                    return
            self.refresh_tasks()

        def add_task(self):
            option = self.console.input(
                "[yellow]Choose option (N: From Next list, O: From Overdue list): "
            )

            if option.lower() == "n":
                next_summary_fn()
                task_id = self.console.input("[yellow]Enter task ID: ")
                due_time = self.console.input("[yellow]Enter due time (HH:MM): ")
            elif option.lower() == "o":
                display_overdue_tasks_fn()
                task_id = self.console.input("[yellow]Enter task ID: ")
                due_time = self.console.input("[yellow]Enter due time (HH:MM): ")
            else:
                self.console.print(
                    "Invalid option. Task not added.", style="bold red"
                )
                return

            task_id = task_id.strip()
            due_time = due_time.strip()
            if not valid_task_id(task_id):
                self.console.print(f"Invalid task id: {task_id}", style="bold red")
                return
            if not valid_time(due_time):
                self.console.print("Invalid time format (HH:MM).", style="bold red")
                return

            run_task_modify(task_id, f"due:{self.current_date}T{due_time}", "status:pending")
            self.console.print(
                f"Task {task_id} added for {due_time}", style="bold green"
            )
            self.refresh_tasks()

        def refresh_tasks(self):
            self.tasks = get_tasks_for_day(self.current_date)
            result = subprocess.run(
                ["task", "status:pending", "export"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                self.all_pending_tasks = parse_export_stdout(result.stdout)
            else:
                self.all_pending_tasks = []

        def create_task_panel(
            self,
            tasks,
            start_time,
            project_counts,
            tag_counts,
            local_tz,
            time_range,
        ):
            output = []

            total_duration = sum(
                parse_duration(task.get("duration", "PT60M")) for task in tasks
            )
            new_end_time = start_time + timedelta(minutes=total_duration)

            task_content = Text()
            for task in tasks:
                task_duration = parse_duration(task.get("duration", "PT60M"))
                task_due_time = datetime.strptime(task["due"], "%Y%m%dT%H%M%SZ")
                task_due_time = pytz.utc.localize(task_due_time).astimezone(
                    local_tz
                )
                due_time_only = task_due_time.strftime(
                    "%H:%M"
                )  # Extract only the due time
                duration_symbols = "# " * (int(task_duration) // 15)
                text_padding = " " * (len(str(task["id"])) + 3)
                task_content.append(f"\n[{task['id']}] ", style="bold yellow")
                task_content.append(f"{task['description']}\n", style="white")
                task_content.append(
                    f"{text_padding}Due: {due_time_only}\n", style="white"
                )
                task_content.append(
                    f"{text_padding}Duration: {format_duration(task_duration)} {duration_symbols}\n",
                    style="italic cyan",
                )

                if task.get("project"):
                    count = project_counts.get(task["project"], 0)
                    task_content.append(
                        f"{text_padding}{task['project']} ({count})\n", style="blue"
                    )

                if task.get("tags"):
                    tags_str = ", ".join(
                        f"{tag} ({tag_counts.get(tag, 0)})" for tag in task["tags"]
                    )
                    task_content.append(
                        f"{text_padding}{tags_str}\n", style="magenta"
                    )

                if task.get("chained") == "on" and "chained_link" in task:
                    task_content.append(
                        f"{text_padding}Link #: {task['chained_link']}\n",
                        style="bold red",
                    )

                if task.get("value"):
                    task_content.append(
                        f"{text_padding}Value: {task['value']}\n",
                        style="bold light_sea_green",
                    )

                task_content.append("\n")

            if len(tasks) > 1:
                total_duration_symbols = ""
                full_hours = int(total_duration) // 60
                remaining_minutes = int(total_duration) % 60

                if full_hours > 0:
                    total_duration_symbols += "@ " * full_hours

                if remaining_minutes > 0:
                    total_duration_symbols += "# " * (remaining_minutes // 15)

                task_content.append(
                    f"{text_padding}Total Duration: {format_duration(total_duration)}\n{text_padding}{total_duration_symbols}\n",
                    style="bold cyan",
                )

            panel_padding = 1

            # Apply different panel styles based on the time range
            if time_range == "Morning":
                panel_style = "deep_pink2"
            elif time_range == "Daytime":
                panel_style = "steel_blue1"
            else:
                panel_style = "orange_red1"

            task_panel = Panel(
                task_content,
                title=f"[bold {panel_style}]{start_time.strftime('%H:%M')}[/bold {panel_style}]",
                expand=False,
                border_style=panel_style,
                padding=(panel_padding, 1),
            )

            output.append(task_panel)

            return output, new_end_time

        def create_calendar_view(self):
            start_of_day = datetime.combine(self.current_date, datetime.min.time())
            start_of_day = localize_time(start_of_day)
            end_of_day = start_of_day.replace(hour=23, minute=59, second=59)
            current_time = start_of_day
            project_counts = self.get_pending_counts("projects")
            tag_counts = self.get_pending_counts("tags")
            sorted_tasks = sorted(
                self.tasks,
                key=lambda x: datetime.strptime(x["due"], "%Y%m%dT%H%M%SZ"),
            )
            output = []
            all_items = []

            for task in sorted_tasks:
                due_time = datetime.strptime(task["due"], "%Y%m%dT%H%M%SZ")
                due_time = pytz.utc.localize(due_time).astimezone(local_tz)
                task_duration = parse_duration(task.get("duration", "PT60M"))
                task_end_time = due_time + timedelta(minutes=task_duration)
                all_items.append(("task", due_time, task, task_end_time))

            all_items.sort(key=lambda x: x[1])
            next_item = None

            while current_time < end_of_day:
                if next_item is None or next_item[1] < current_time:
                    next_item = next(
                        (item for item in all_items if item[1] >= current_time),
                        None,
                    )

                if next_item:
                    free_time = (next_item[1] - current_time).total_seconds() / 60
                    if free_time > 0:
                        output.append(
                            self.create_free_time_panel(free_time, current_time)
                        )
                    current_time = next_item[1]
                    grouped_tasks = [next_item[2]]
                    task_end_time = next_item[3]

                    while True:
                        overlapping_task = next(
                            (
                                item
                                for item in all_items
                                if item[1] < task_end_time
                                and item[2] not in grouped_tasks
                            ),
                            None,
                        )
                        if overlapping_task:
                            grouped_tasks.append(overlapping_task[2])
                            task_end_time = max(task_end_time, overlapping_task[3])
                        else:
                            break

                    if current_time.time() < time(9):
                        time_range = "Morning"
                    elif current_time.time() < time(17):
                        time_range = "Daytime"
                    else:
                        time_range = "Evening"

                    task_panel_output, new_end_time = self.create_task_panel(
                        grouped_tasks,
                        current_time,
                        project_counts,
                        tag_counts,
                        local_tz,
                        time_range,
                    )
                    output.extend(task_panel_output)
                    current_time = new_end_time

                    # Remove all grouped tasks from all_items
                    all_items = [
                        item for item in all_items if item[2] not in grouped_tasks
                    ]
                else:
                    free_time = (end_of_day - current_time).total_seconds() / 60
                    if free_time > 0:
                        output.append(
                            self.create_free_time_panel(free_time, current_time)
                        )
                    break

            return output

        # def create_notes_panel(self):
        # 	notes = self.get_notes_for_day()
        # 	notes_content = Text()

        # 	for note in notes:
        # 		notes_content.append(f"[{note['index']}] {note['time']}:\n", style="italic yellow")
        # 		for line in note['content'].split('\n'):
        # 			notes_content.append(f"  \n{line}", style="cyan")
        # 		notes_content.append("\n")

        # 	if not notes_content:
        # 		notes_content.append("No notes for today.\n", style="italic yellow")

        # 	notes_panel = Panel(
        # 		notes_content,
        # 		title="Notes",
        # 		border_style="steel_blue1",
        # 		padding=(1, 1)
        # 	)

        # 	return notes_panel

        def create_date_panel(self):
            from pyfiglet import Figlet
            import random

            formatted_date = self.current_date.strftime("%A       %B %d %Y")
            f = Figlet(font="doom")
            rendered_text = f.renderText(formatted_date)

            pending_count = self.get_pending_counts("pending")
            completed_count = self.get_pending_counts("completed")

            # Create the full text to display
            full_text = f"{rendered_text}\nPending: {pending_count}\nCompleted: {completed_count}"

            # Calculate the width of the panel based on the longest line in full_text
            max_line_length = max(len(line) for line in full_text.split("\n"))

            # Adjust the panel width to be slightly larger than the longest line
            panel_width = max_line_length + 4  # Adding a buffer for padding
            random_color = random.choice(colors)
            # Generate the panel
            return Panel(
                Text(full_text, style=random_color),
                border_style=random_color,
                width=panel_width,
            )

        def display_calendar_view(self):
            # Create the date panel
            date_panel = self.create_date_panel()

            # Print the date panel
            self.console.print(date_panel)

            # Generate and print the calendar view
            calendar_view = self.create_calendar_view()
            for item in calendar_view:
                self.console.print(item)

            # Print the notes panel
            self.console.print(self.create_notes_panel())

        def create_free_time_panel(self, free_time, start_time):
            free_panel_padding = 1
            return Panel(
                Text(
                    f"Free Time: {format_duration(free_time)}",
                    style="bold chartreuse1",
                ),
                title=f"{start_time.strftime('%H:%M')}",
                expand=False,
                border_style="gray89",
                padding=(free_panel_padding, 1),
            )

        def display_notes_panel(self):
            notes_panel = self.create_notes_panel()
            self.console.print(notes_panel)

        def create_notes_panel(self):
            notes = self.get_notes_for_day()
            notes_content = Text()

            for note in notes:
                notes_content.append(
                    f"\n[{note['index']}] {note['time']}: \n", style="bold white"
                )
                if self.current_date.strftime("%Y-%m-%d") != note["until"]:
                    if note["until"] == "noend":
                        notes_content.append(
                            "Forever note!\n", style="italic white"
                        )
                    else:
                        notes_content.append(
                            f"Until:{note['until']}\n", style="italic white"
                        )
                notes_content.append(
                    f"{note['content']}\n", style=f"italic {note['color']}"
                )

            if not notes:
                notes_content.append("No notes for today.\n", style="italic yellow")

            notes_panel = Panel(
                notes_content,
                title="[bold magenta]Notes[/bold magenta]",
                border_style="bright_cyan",
                padding=(1, 1),
            )

            return notes_panel

        def get_pending_counts(self, attribute):
            counts = defaultdict(int)

            if attribute == "tags":
                unique_tags = set(
                    tag for task in self.tasks for tag in task.get("tags", [])
                )
                if not unique_tags:
                    return counts
                for task in self.all_pending_tasks:
                    for tag in task.get("tags", []):
                        if tag in unique_tags:
                            counts[tag] += 1
            elif attribute == "projects":
                unique_projects = set(
                    task.get("project")
                    for task in self.tasks
                    if task.get("project")
                )
                if not unique_projects:
                    return counts
                for task in self.all_pending_tasks:
                    project_name = task.get("project")
                    if project_name in unique_projects:
                        counts[project_name] += 1
            elif attribute == "pending":
                result = subprocess.run(
                    ["task", f"due:{self.current_date}", "status:pending", "count"],
                    capture_output=True,
                    text=True,
                )
                try:
                    counts = int(result.stdout.strip())
                except ValueError:
                    counts = 0
            elif attribute == "completed":
                result = subprocess.run(
                    ["task", f"due:{self.current_date}", "status:completed", "count"],
                    capture_output=True,
                    text=True,
                )
                try:
                    counts = int(result.stdout.strip())
                except ValueError:
                    counts = 0

            return counts

    TaskOrganizer().run()
