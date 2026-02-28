from tasklib import TaskWarrior, Task
from taskw import TaskWarrior as Warrior
from colorama import init, Fore, Back
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from termcolor import colored

# from itertools import zip_longest
# import textwrap
from dateutil.parser import parse
import pytz
import questionary
from questionary import Style
from prompt_toolkit import prompt
from prompt_toolkit.completion import FuzzyWordCompleter
from prompt_toolkit.completion import FuzzyCompleter, WordCompleter
import subprocess
import argparse
import os
import calendar
from datetime import date

# import texttable as tt
#import pandas as pd
from fuzzywuzzy import process
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

# from rich import print as rprint
from rich.panel import Panel
from rich.console import Group
from rich import box
import re
from enum import Enum
from rich.prompt import IntPrompt

from pathlib import Path
from typing import List, Optional
# from operator import itemgetter
import shlex

import logging

import sys

from taskvarios.constants import colors, guide_styles, level_colors, local_tz
from taskvarios.contexts import context_menu
from taskvarios.data_ops import (
    clear_data as run_clear_data,
    confirm_action as run_confirm_action,
    get_tags_for_aor as run_get_tags_for_aor,
    search_data as run_search_data,
    sync_with_taskwarrior as run_sync_with_taskwarrior,
)
from taskvarios.interactive import interactive_prompt as run_interactive_prompt
from taskvarios.item_helpers import (
    get_multiline_input as run_get_multiline_input,
    get_tags_for_item as run_get_tags_for_item,
    update_item as run_update_item,
    view_data as run_view_data,
)
from taskvarios.item_metadata import (
    get_creation_date as run_get_creation_date,
    get_last_modified_date as run_get_last_modified_date,
    view_project_metadata as run_view_project_metadata,
)
from taskvarios.organizer import task_organizer as run_task_organizer
from taskvarios.reports import (
    all_summary,
    basic_summary,
    detailed_summary,
    next_summary,
    recurrent_report,
)
from taskvarios.storage import get_default_db_path, load_sultandb
from taskvarios.metadata import update_metadata_field as run_update_metadata_field
from taskvarios.task_manager import task_manager as run_task_manager
from taskvarios.taskwarrior import run_taskwarrior_command
from taskvarios.task_views import (
    display_due_tasks as run_display_due_tasks,
    display_overdue_tasks as run_display_overdue_tasks,
)

try:
    import ujson as json
except ImportError:
    import json

import warnings

warnings.filterwarnings("ignore")

from questionary import Choice, checkbox





file_path = get_default_db_path(__file__)
aors, projects = load_sultandb(file_path)


warrior = Warrior()
console = Console()


def main():
    # Map each command to its corresponding function
    command_to_function = {
        "s": search_task,
        "c": clear_data,
        "b": basic_summary,
        "d": detailed_summary,
        "a": all_summary,
        "i": display_inbox_tasks,
        "tl": display_due_tasks,
        "ht": handle_task,
        "tc": task_control_center,
        "td": print_tasks_for_selected_day,
        "sp": call_and_process_task_projects,
        "o": display_overdue_tasks,
        "rr": recurrent_report,  # includes only the period type recurrent tasks
        "z": eisenhower,
        "pi": greeting_pi,
        "tm": task_manager,
        "cm": context_menu,
        "n": next_summary,
        "rp": review_projects,
        "to": task_organizer,
        "mp": multiple_projects_view,
    }

    parser = argparse.ArgumentParser(description="Process some commands.")
    parser.add_argument(
        "command",
        metavar="CMD",
        type=str,
        nargs="?",
        default="",
        help="A command to run",
    )
    parser.add_argument(
        "arg",
        metavar="ARG",
        type=str,
        nargs="?",
        default=None,
        help="Optional argument for the command",
    )

    args = parser.parse_args()

    if args.command:
        if args.command in command_to_function:
            if args.arg:
                # If a secondary argument is provided, pass it to the function
                command_to_function[args.command](args.arg)
            else:
                # Call the corresponding function if no secondary argument is provided
                command_to_function[args.command]()
        else:
            print("Invalid command provided.")
    else:
        # Continue to the interactive prompt if no command argument is provided
        script_directory = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_directory, "variosdb.json")
        interactive_prompt(file_path)


try:

    def print_calendar_with_marked_day(year, month, day):
        cal = calendar.TextCalendar(firstweekday=calendar.MONDAY)
        today = date.today()  # Today's date

        month_name = calendar.month_name[month]
        year_text = str(year)

        print(f"{delimiter}\033[1;31m{month_name} {year_text}\033[0m{delimiter}")

        line = ""
        for week in cal.monthdayscalendar(year, month):
            for weekday in week:
                current_day = date(year, month, weekday) if weekday != 0 else None

                if weekday == day:
                    line += f"{Back.GREEN}{Fore.BLACK}{weekday:02d}{Fore.RESET}{Back.RESET} "
                elif weekday == 0:
                    line += "   "
                else:
                    if current_day < today:  # Dates before today
                        line += f"{Fore.BLACK}{Back.YELLOW}{weekday:02d}{Fore.RESET}{Back.RESET} "
                    elif current_day > today:  # Dates after today
                        line += f"{Fore.CYAN}{weekday:02d}{Fore.RESET} "
                    else:  # Today
                        line += f"{weekday:02d} "
        print(line)

    def sync_sultandb_with_taskwarrior(file_path):
        # import os
        # import json
        # import subprocess

        # Load existing data from variosdb.json
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                sultandb = json.load(file)
        except FileNotFoundError:
            sultandb = {"aors": [], "projects": []}

        aors = sultandb.get("aors", [])
        projects = sultandb.get("projects", [])

        # Fetch projects from Taskwarrior
        command = ["task", "_projects"]
        result = subprocess.run(command, stdout=subprocess.PIPE)
        task_projects = result.stdout.decode("utf-8").splitlines()

        # Separate AoRs and normal projects
        task_aors = [p for p in task_projects if p.startswith("AoR.")]
        task_projects = [p for p in task_projects if not p.startswith("AoR.")]

        # Create sets for fast lookup
        existing_aor_names = set(aor["name"] for aor in aors)
        existing_project_names = set(project["name"] for project in projects)

        # Add new AoRs from Taskwarrior
        new_aors = []
        for aor_name in task_aors:
            aor_name_without_prefix = aor_name[4:]  # Remove "AoR." prefix
            if aor_name_without_prefix not in existing_aor_names:
                new_aor = {
                    "name": aor_name_without_prefix,
                    "description": "",
                    "standard": "",
                    "annotations": [],
                    "workLogs": [],
                    "status": "Active",
                }
                aors.append(new_aor)
                new_aors.append(aor_name_without_prefix)

        # Add new projects from Taskwarrior
        new_projects = []
        for project_name in task_projects:
            if project_name not in existing_project_names:
                new_project = {
                    "name": project_name,
                    "description": "",
                    "outcome": "",
                    "annotations": [],
                    "workLogs": [],
                    "status": "Active",
                }
                projects.append(new_project)
                new_projects.append(project_name)

        # Update status of existing AoRs
        task_aor_names = set(aor[4:] for aor in task_aors)  # Remove "AoR." prefix
        for aor in aors:
            if aor["name"] in task_aor_names:
                if aor.get("status") != "Active":
                    aor["status"] = "Active"
            else:
                if aor.get("status") != "Completed":
                    aor["status"] = "Completed"

        # Update status of existing projects
        task_project_names = set(task_projects)
        for project in projects:
            if project["name"] in task_project_names:
                if project.get("status") != "Active":
                    project["status"] = "Active"
            else:
                if project.get("status") != "Completed":
                    project["status"] = "Completed"

        # Save the updated sultandb data
        sultandb["aors"] = aors
        sultandb["projects"] = projects

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(sultandb, file, indent=4)

        # Print status message
        print("Synchronization complete.")
        if new_aors:
            print(f"Added new AoRs: {', '.join(new_aors)}")
        if new_projects:
            print(f"\nAdded new projects: {', '.join(new_projects)}\n")
        if not new_aors and not new_projects:
            print("\nNo new AoRs or projects were added.\n")

    def display_overdue_tasks():
        return run_display_overdue_tasks(warrior, local_tz)

    def print_tasks_for_selected_day():
        # Initialize colorama
        init(autoreset=True)

        def get_deleted_tasks_due_today(date):
            # Run the 'task export' command and get the output
            result = subprocess.run(["task", "export"], stdout=subprocess.PIPE)

            # Load the output into Python as JSON
            all_tasks = json.loads(result.stdout)

            # Prepare a list to store tasks
            deleted_tasks_due_today = []

            # Iterate over all tasks
            for task in all_tasks:
                # Check if task status is 'deleted' and if it's due date is today
                if (
                    task["status"] == "deleted"
                    and "due" in task
                    and datetime.strptime(task["due"], "%Y%m%dT%H%M%SZ").date() == date
                ):
                    deleted_tasks_due_today.append(task)

            # Return the list of tasks
            return deleted_tasks_due_today

        def parse_date(date_str):
            utc_time = datetime.strptime(date_str, "%Y%m%dT%H%M%SZ")
            return utc_time.replace(tzinfo=timezone.utc).astimezone(tz=None)

        user_choice = (
            input(
                "Do you want to display tasks for yesterday (y), today (t), or tomorrow (tm)? (y/t/tm): "
            )
            .strip()
            .lower()
        )
        if user_choice not in (
            "yesterday",
            "yd",
            "y",
            "today",
            "td",
            "t",
            "tomorrow",
            "tm",
        ):
            print("Default choice, today tasks displayed.")
            user_choice = "today"

        if user_choice in ("today", "td", "t"):
            date = datetime.now().date()
            print(f"Selected tasks for {date}")
        elif user_choice in ("tomorrow", "tm"):
            date = datetime.now().date() + timedelta(days=1)
            print(f"Selected tasks for {date}")
        elif user_choice in ("yesterday", "yd", "y"):
            date = datetime.now().date() - timedelta(days=1)
            print(f"Selected tasks for {date}")
        else:
            date = datetime.now().date()
            print(f"Selected tasks for {date}")

        w = Warrior()
        task_snapshot = w.load_tasks()
        pending_tasks = task_snapshot["pending"]
        completed_tasks = task_snapshot["completed"]
        deleted_tasks = get_deleted_tasks_due_today(date)

        due_tasks = sorted(
            (
                task
                for task in pending_tasks
                if task.get("due") and parse_date(task["due"]).date() == date
            ),
            key=lambda task: parse_date(task["due"]),
        )

        completed_tasks = sorted(
            (
                task
                for task in completed_tasks
                if task.get("end") and parse_date(task["end"]).date() == date
            ),
            key=lambda task: parse_date(task["end"]),
        )

        tasks_dict = {}
        for task_list in [due_tasks, completed_tasks, deleted_tasks]:
            for task in task_list:
                local_time = (
                    parse_date(task["due"])
                    if task.get("due")
                    else parse_date(task["end"])
                )
                hour = local_time.hour
                minute = local_time.minute
                time_key = (hour, minute)
                task_status = task.get("status")
                task_id_or_deleted = (
                    "[DELETED]" if task in deleted_tasks else task.get("id")
                )
                task_info = (
                    task["description"],
                    task.get("duration", 0),
                    task_id_or_deleted,
                    task.get("project"),
                    task.get("tags"),
                    task_status,
                    task.get("annotations"),
                )
                if time_key not in tasks_dict:
                    tasks_dict[time_key] = [task_info]
                else:
                    tasks_dict[time_key].append(task_info)

        current_time = datetime.now(timezone.utc).astimezone()

        for hour in range(24):
            hour_printed = False
            for minute in range(60):
                time_key = (hour, minute)
                if time_key in tasks_dict:
                    if minute == 0 or not hour_printed:
                        print(f"{Fore.YELLOW}{hour:02d}:00")
                        hour_printed = True

                    for (
                        task,
                        duration,
                        task_id,
                        project,
                        tags,
                        status,
                        annotations,
                    ) in tasks_dict[time_key]:
                        project_color = (
                            Fore.GREEN
                            if project and project.startswith("AoR.")
                            else Fore.BLUE
                        )
                        task_id_or_completed = (
                            f"{Fore.GREEN}[COMPLETED]{Fore.RESET}"
                            if status == "completed"
                            else f"{Fore.RED} {task_id}"
                        )
                        task_details = f"{Fore.YELLOW}{hour:02d}:{minute:02d} {task_id_or_completed}, {Fore.RESET}{task} [{duration} mins], {project_color}Pro:{project}, {Fore.RED}{tags}"
                        print(task_details)
                        if annotations:
                            # print(f"{Fore.MAGENTA}Annotations:")
                            for annotation in annotations:
                                entry_date = parse_date(annotation["entry"]).date()
                                print(
                                    f"\t{Fore.CYAN}{entry_date}{Fore.YELLOW}: {annotation['description']}"
                                )

                if (
                    user_choice in ("today", "td")
                    and hour == current_time.hour
                    and minute == current_time.minute
                ):
                    print(
                        f"{Fore.CYAN}{current_time.strftime('%H:%M')}{'=' * 25} {Fore.WHITE}Present Moment {Fore.RESET}{Fore.CYAN}{'=' * 25}{Fore.RESET}"
                    )

            if not hour_printed:
                print(f"{Fore.BLUE}{hour:02d}:00")

        if (
            user_choice in ("today", "td")
            and current_time.hour == 23
            and current_time.minute == 59
        ):
            print(f"{'=' * 25} {Fore.WHITE}Present Moment {Fore.RESET}{'=' * 25}")

        if len(due_tasks) == 0:
            print(
                f"\n\t{Fore.BLACK}{Back.LIGHTCYAN_EX}  No pending tasks!{Fore.RESET}{Back.RESET}"
            )
        else:
            print(
                f"\n\t\033[1m{len(due_tasks)} pending tasks out of {len(due_tasks) + len(completed_tasks)} total. {len(completed_tasks)} completed and {len(deleted_tasks)} deleted!"
            )

        print_calendar_with_marked_day(date.year, date.month, date.day)
        while True:
            action = questionary.select(
                "What do you want to do next?", choices=["Refresh", "Exit"]
            ).ask()

            # CTRL+C actionx
            action = "Exit" if action is None else action

            if action == "Refresh":
                print_tasks_for_selected_day()  # Refresh and show data again
            elif action == "Exit":
                print("Exit")
                break

    def search_task():
        tasks = warrior.load_tasks()

        include_completed = questionary.confirm(
            "Include completed tasks in the search?", default=False
        ).ask()
        if include_completed:
            tasks = tasks["pending"] + tasks["completed"]
        else:
            tasks = tasks["pending"]

        task_descriptions = [task.get("description") for task in tasks]
        completer = FuzzyWordCompleter(task_descriptions)

        task_description = prompt("Enter a task description: ", completer=completer)

        selected_task = next(
            (task for task in tasks if task.get("description") == task_description),
            None,
        )

        if selected_task:
            print(
                f"{Fore.BLUE}ID:{Fore.RESET} {Fore.RED}{selected_task.get('id')}{Fore.RESET}"
            )
            print(
                f"{Fore.BLUE}Description:{Fore.RESET} {Fore.YELLOW}{selected_task.get('description')}{Fore.RESET}"
            )
            print(
                f"{Fore.BLUE}Project:{Fore.RESET} {Fore.YELLOW}{selected_task.get('project')}{Fore.RESET}"
            )
            print(
                f"{Fore.BLUE}Tags:{Fore.RESET} {Fore.YELLOW}{', '.join(selected_task.get('tags', []))}{Fore.RESET}"
            )
            due_date_str = selected_task.get("due")
            due_date = (
                parse(due_date_str).replace(tzinfo=timezone.utc)
                if due_date_str
                else None
            )
            if due_date:
                now = datetime.now(timezone.utc)
                time_remaining = due_date - now
                print(
                    f"{Fore.BLUE}Due:{Fore.RESET} {Fore.YELLOW}{due_date}{Fore.RESET}\n{Fore.BLUE}Time Remaining:{Fore.RESET} {Fore.YELLOW}{time_remaining.days} days, {time_remaining.seconds // 3600}:{time_remaining.seconds % 3600 // 60}{Fore.RESET}"
                )
        else:
            print("No task found with that description.")

    def display_inbox_tasks():
        tasks = warrior.load_tasks()["pending"]
        delimiter = "-" * 40
        # Filter tasks with the tag "in"
        inbox_tasks = [task for task in tasks if "in" in task.get("tags", [])]

        # Parse entry dates and calculate time deltas
        for task in inbox_tasks:
            entry_date = (
                datetime.strptime(task["entry"], "%Y%m%dT%H%M%SZ")
                .replace(tzinfo=timezone.utc)
                .astimezone(tz=None)
            )
            task["time_delta"] = (
                datetime.now(timezone.utc).astimezone(tz=None) - entry_date
            )

        # Sort tasks by their time deltas
        inbox_tasks.sort(key=lambda task: task["time_delta"])

        # Print tasks
        print(f"{Fore.RED}{delimiter}{Fore.RESET}")
        for task in inbox_tasks:
            # Format time delta as days
            days = task["time_delta"].days
            formatted_days = f"-{days:02d}d"  # Adds leading zero if days < 10
            print(
                f"{Fore.CYAN}{task['id']}{Fore.RESET}, {Fore.GREEN}{formatted_days}{Fore.RESET}, {Fore.YELLOW}{task['description']}{Fore.RESET}"
            )
        print(f"{Fore.BLUE}{delimiter}{Fore.RESET}")

    def handle_task():
        print("Please enter the task command:")
        print("Examples:")
        print("'223,114,187 done' - Marks tasks 223, 114, and 187 as done.")
        # print("!!!! The operation will be done without asking for confirmation!.")
        print("To return to the main menu, press 'Enter'.\n")
        print("----------------------------------------------\n")

        while True:
            task_command = input()
            if task_command.lower() == "":
                return
            else:
                subprocess.run(f"task {task_command}", shell=True)

    def display_due_tasks():
        return run_display_due_tasks(warrior, local_tz)

    def get_item_info(user_input):
        print(user_input + "this needs work")

    def mark_item_inactive(item_name, aors, projects):
        for item in aors:
            if item["name"] == item_name:
                item["status"] = "Completed"

        for item in projects:
            if item["name"] == item_name:
                item["status"] = "Completed"

    def get_creation_date(item_name, pending_tasks=None):
        return run_get_creation_date(item_name, pending_tasks)


    def get_last_modified_date(item_name, pending_tasks=None):
        return run_get_last_modified_date(item_name, pending_tasks)


    def get_tags_for_item(item_name):
        return run_get_tags_for_item(item_name)


    def view_data(item, tags):
        return run_view_data(item, tags, get_creation_date, get_last_modified_date)


    def execute_taskwarrior_command(command):
        """Execute a TaskWarrior command and return its output."""
        try:
            # Start the process
            proc = subprocess.Popen(
                command,
                shell=True,
                text=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            while True:
                # Read from stdout and stderr
                stdout_line = proc.stdout.readline()
                stderr_line = proc.stderr.readline()

                # Display stdout and stderr to the user
                if stdout_line:
                    sys.stdout.write(stdout_line)
                    sys.stdout.flush()
                if stderr_line:
                    sys.stderr.write(stderr_line)
                    sys.stderr.flush()

                # Check if there's a prompt in stderr for user input
                if stderr_line and "prompt" in stderr_line.lower():
                    user_input = input("Please provide input: ")
                    proc.stdin.write(user_input + "\n")
                    proc.stdin.flush()

                # Check if process is still running
                if proc.poll() is not None:
                    break

            # Get the final output
            stdout, stderr = proc.communicate()

            if stdout:
                return stdout.strip()  # Remove extra whitespace
            if stderr:
                print(f"Error: {stderr.strip()}")

        except Exception as e:
            print(f"An error occurred while executing the TaskWarrior command: {e}")

        return ""

    # def get_task_count(item_name, status):
    # 	"""Get the count of tasks by status for a specific project."""
    # 	command = f"task count project:{item_name} status:{status}"
    # 	return execute_taskwarrior_command(command)

    def view_project_metadata(item, tags, item_name):
        return run_view_project_metadata(item, tags, item_name)


    def get_multiline_input(prompt_message):
        return run_get_multiline_input(prompt_message)


    def update_item(items, item_index, file_path, specific_field, aors, projects):
        return run_update_item(items, item_index, file_path, specific_field, aors, projects)




    def call_and_process_task_projects():
        """Main function to call task projects and process the output."""
        try:
            result = subprocess.run(
                ["task", "projects"], 
                capture_output=True, 
                text=True, 
                timeout=30,
                check=True
            )
            
            if not result.stdout.strip():
                logging.warning("No output received from 'task projects'")
                return
                
            lines = result.stdout.splitlines()
            project_list = process_input(lines)
            
            if project_list:
                search_project(project_list)
            else:
                logging.info("No projects found to process")
                
        except subprocess.TimeoutExpired:
            logging.error("Task projects command timed out")
        except subprocess.CalledProcessError as e:
            logging.error(f"Task projects command failed: {e}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")

    def process_input(lines):
        """Process task projects output into hierarchical project names."""
        if not lines:
            return []
        
        # Find data section
        data_start = None
        for i, line in enumerate(lines):
            if line.startswith('---'):
                data_start = i + 1
                break
        
        if data_start is None:
            logging.error("No data separator found")
            return []
        
        # Extract data lines
        data_lines = []
        for line in lines[data_start:]:
            if line.strip() and not (line.endswith('tasks)') or line.endswith('task)')):
                data_lines.append(line)
            else:
                break
        
        if not data_lines:
            return []
        
        # Detect indentation
        indent_unit = detect_indentation(data_lines)
        if not indent_unit:
            logging.error("Could not detect indentation pattern")
            return []
        
        # Parse hierarchy
        stack = []
        output = []
        for line in data_lines:
            indent = len(line) - len(line.lstrip())
            level = indent // indent_unit
            
            # Trim stack to current level
            del stack[level:]
            
            # Extract project name
            project = line.strip().split()[0]
            stack.append(project)
            
            output.append('.'.join(stack))
        
        return output

    def detect_indentation(lines):
        """Detect indentation unit using most common difference."""
        indents = []
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                if indent > 0:
                    indents.append(indent)
        
        if not indents:
            return 2  # Default fallback
        
        # Find most common indentation difference
        diffs = {}
        for i in range(1, len(indents)):
            diff = abs(indents[i] - indents[i-1])
            if diff > 0:
                diffs[diff] = diffs.get(diff, 0) + 1
        
        if diffs:
            return max(diffs.items(), key=lambda x: x[1])[0]
        
        return min(indents) if indents else 2



    def dependency_tree(selected_item):


        from datetime import datetime
        import pytz
        from dateutil.parser import parse

        tasks = warrior.load_tasks()
        selected_project = selected_item

        task_dict = {}
        now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        all_tasks = {task["uuid"]: task for task in tasks["pending"]}
        uuid_to_real_id = {task["uuid"]: task["id"] for task in tasks["pending"]}

        def is_relevant(task):
            project = task.get("project")
            return project and (
                project == selected_project
                or project.startswith(selected_project + ".")
            )

        def collect_tasks(task_uuid, visited=set()):
            if task_uuid in visited or task_uuid not in all_tasks:
                return
            visited.add(task_uuid)
            task = all_tasks[task_uuid]
            dependencies = task.get("depends", [])

            task_dict[task_uuid] = {
                "project": task.get("project"),
                "description": task.get("description", ""),
                "due_date": task.get("due"),
                "time_remaining": calculate_time_remaining(task.get("due"), now),
                "annotations": task.get("annotations", []),
                "tags": task.get("tags", []),
                "dependencies": dependencies,
            }

            for dep_uuid in dependencies:
                collect_tasks(dep_uuid, visited)

        for task_uuid, task in all_tasks.items():
            if is_relevant(task):
                collect_tasks(task_uuid)

        tree = Tree(f"Dependency Tree: {selected_project}", style="green")
        # local_tz = datetime.now().astimezone().tzinfo

        def add_task_to_tree(task_uuid, parent_branch):
            if task_uuid not in task_dict:
                return
            task = task_dict[task_uuid]
            real_id = uuid_to_real_id[task_uuid]
            task_description = task["description"]
            task_id_text = Text(f"[{real_id}] ", style="red")
            task_description_text = Text(task_description, style="white")
            task_id_text.append(task_description_text)

            due_date = task.get("due_date")
            if due_date:
                formatted_due_date = parse(due_date).strftime("%Y-%m-%d")
                time_remaining, time_style = calculate_time_remaining(due_date, now)
                due_text = Text(f" {formatted_due_date} ", style="blue")
                time_remaining_text = Text(time_remaining, style=time_style)
                due_text.append(time_remaining_text)
                task_id_text.append(due_text)

            # Display tags in red bold
            if task.get("tags"):
                tags_text = Text(f" +{', '.join(task['tags'])} ", style="bold red")
                task_id_text.append(tags_text)

            # Display project in blue bold if different from the selected or if no project is assigned
            if task.get("project") != selected_project:
                project_text = Text(
                    f" {task.get('project', 'No Project')} ", style="magenta"
                )
                task_id_text.append(project_text)

            task_branch = parent_branch.add(task_id_text)

            annotations = task.get("annotations", [])
            if annotations:
                annotation_branch = task_branch.add(Text("Annotations:", style="white"))
                for annotation in annotations:
                    entry_datetime = parse(annotation["entry"])
                    if (
                        entry_datetime.tzinfo is None
                        or entry_datetime.tzinfo.utcoffset(entry_datetime) is None
                    ):
                        entry_datetime = entry_datetime.replace(tzinfo=local_tz)
                    else:
                        entry_datetime = entry_datetime.astimezone(local_tz)
                    annotation_text = Text(
                        f"{entry_datetime.strftime('%Y-%m-%d %H:%M:%S')} - {annotation['description']}",
                        style="dim white",
                    )
                    annotation_branch.add(annotation_text)

            for dep_uuid in task["dependencies"]:
                add_task_to_tree(dep_uuid, task_branch)

        for task_uuid in task_dict:
            if not any(
                task_uuid in task_dict[dep_uuid]["dependencies"]
                for dep_uuid in task_dict
            ):
                add_task_to_tree(task_uuid, tree)

        console.print(tree)

    def calculate_time_remaining(due_date_str, now):
        if due_date_str:
            due_date = parse(due_date_str)
            time_remaining = due_date - now
            if time_remaining.total_seconds() >= 0:
                time_style = "green"
            else:
                time_style = "red"

            # Formatted string to include days, hours, and minutes
            days = time_remaining.days
            seconds = time_remaining.seconds
            hours, remainder = divmod(seconds, 3600)
            minutes = remainder // 60

            if days or hours or minutes:
                formatted_time = (
                    f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m"
                )
            else:
                formatted_time = "0m"  # Show 0 minutes if time remaining is very short

            return formatted_time, time_style
        return None  # Return None when no due date


    def get_additional_filters():
        """
        Prompt the user to add additional filters to the query.
        Returns the additional filter string or an empty string if no filters are added.
        """
        additional_filters = Prompt.ask(
            "[bold cyan]Do you want to add additional filters? (e.g., '+OVERDUE due:today')[/bold cyan]",
            default="",
        )
        return additional_filters.strip()  # Remove any leading/trailing whitespace

    def combine_filters(base_filter, additional_filters):
        """
        Combine the base filter with additional filters.
        """
        if additional_filters:
            return f"{base_filter} {additional_filters}"
        return base_filter

    def _tw_run(cmd_list):
        try:
            res = subprocess.run(cmd_list, capture_output=True, text=True, check=False)
            ok = (res.returncode == 0)
            return ok, (res.stdout.strip() if ok else res.stderr.strip())
        except Exception as e:
            return False, f"Error executing {' '.join(shlex.quote(c) for c in cmd_list)} :: {e}"

    def _normalize_project_component(name: str) -> str:
        s = name.strip()
        if not s:
            return ""
        s = re.sub(r"\s+", "-", s)
        s = re.sub(r"[\\/,:;]", "-", s)
        return s.strip(".")

    def add_subproject_and_tasks(parent_project: str):
        """
        Interactive helper:
        1) Ask for a sub-project name
        2) Build full path: parent.SUB
        3) Loop: single-line input per task where the user can include any TW details inline.
            Example input:
            Fix login bug due:tomorrow +work pri:H
            Press ENTER on an empty line to finish.
        """
        print(f"\n➕ Add a sub-project under: {parent_project}")

        while True:
            raw = input("Sub-project name → ").strip()
            sub_component = _normalize_project_component(raw)
            if not sub_component:
                print("Please provide a non-empty name.")
                continue
            break

        full_project = f"{parent_project}.{sub_component}"
        print(f"Creating tasks for project: {full_project}\n")
        print("One line per task. Include any TW details inline (e.g., +tag due:2025-09-05 pri:H rec:weekly).")
        print("Press ENTER on an empty line to finish.\n")

        while True:
            line = input("Task line → ").strip()
            if not line:
                print("Done adding tasks.\n")
                break

            # Build command: keep project fixed, pass the entire line split by shell rules
            cmd = ["task", "add", f"project:{full_project}"]
            cmd.extend(shlex.split(line))

            ok, out = _tw_run(cmd)
            if ok:
                print(f"✔ Added\n{out}\n")
            else:
                print(f"✖ Could not add task:\n{out}\n")

        ok, out = _tw_run(["task", f"project:{full_project}", "count"])
        if ok:
            print(f"📊 {full_project} now has {out} task(s).")
        else:
            print(f"Note: couldn’t count tasks in {full_project}. {out}")

    def parent_project_path(project: str) -> str | None:
        """Return parent of dotted project path, or None if already top-level."""
        if "." not in project:
            return None
        return ".".join(project.split(".")[:-1])


    def search_project(project_list):
        completer = FuzzyWordCompleter(project_list)

        # Define the style for the completer
        style = Style.from_dict(
            {
                "completion-menu.completion": "bg:black black green",
            }
        )

        # Prompt the user for a project or AoR name with custom styles
        item_name = prompt(
            "Enter a project or AoR name: ", completer=completer, style=style
        )

        # Run the dependency_tree with the selected project
        console = Console()
        
        # Default sorting
        current_sort = "alpha"

        if item_name == "mp":
            print("Right, lets get to work and getting things done!")
            multiple_projects_view()
        else:
            display_tasks(f"task project:{item_name} +PENDING export", sort_by=current_sort)

        while True:
            console.print("\n" + "-:" * 40)
            print("You can't do a project -- you can only do action steps. Do enough of the appropriate actions, over time, and you make the world resemble the image you've commited to in your mind.")
            print("What is the successful outcome?")
            print("What is the next action?\n")
            # Create a table for menu options
            table = Table(
                box=box.ROUNDED, expand=False, show_header=False, border_style="cyan"
            )
            table.add_column("Option", style="orange_red1", no_wrap=True)
            table.add_column("Description", style="light_sea_green")

            # Project Management options
            table.add_row("", "[bold underline]Project Management:[/bold underline]")
            table.add_row("R", "Refresh")
            table.add_row("DT", "Display dependency tree")
            table.add_row("SD", "Set dependencies")
            table.add_row("RD", "Remove dependencies")
            table.add_row("DE", "Show Details")
            table.add_row("SP", "Search another project")
            table.add_row("ASP","Add Sub-Project")
            table.add_row("MP", "Display multiple projects")
            table.add_row("MA", "Main menu")
            if "." in item_name:
                table.add_row("..", "Go up one project")
            table.add_row("", "")  # Separator

            # Sorting options
            table.add_row("", "[bold underline]Sorting Options:[/bold underline]")
            table.add_row("SA", f"Sort Alphabetically {'[green]✓[/green]' if current_sort == 'alpha' else ''}")
            table.add_row("SV", f"Sort by Value {'[green]✓[/green]' if current_sort == 'value' else ''}")
            table.add_row("", "")  # Separator

            # Update Metadata options
            table.add_row("", "[bold underline]Update Metadata:[/bold underline]")
            table.add_row("UD", "Update Description")
            table.add_row("UO", "Update Standard/Outcome")
            table.add_row("AA", "Add Annotation")
            table.add_row("AW", "Add Work Log")
            table.add_row("SYDB", "Sync variosDB to TW DB")
            table.add_row("", "")  # Separator

            # Task Management options
            table.add_row("", "[bold underline]Task Management:[/bold underline]")
            table.add_row("TW", "TW prompt")
            table.add_row("TM", "Task Manager")
            table.add_row("NT", "Add new task")
            table.add_row("AN", "Annotate task")
            table.add_row("TD", "Mark task as completed")
            table.add_row("DD", "Assign due date")
            table.add_row("PV", "Process Value/Priority")
            table.add_row("", "")  # Separator

            # Exit option
            table.add_row("", "[bold underline]Exit:[/bold underline]")
            table.add_row("", "|_>")

            console.print(
                Panel(table, title="Project Management Options", expand=False)
            )

            choice = console.input("[yellow]Enter your choice: ").upper()

            if choice == "R":
                console.clear()
                display_tasks(f"task project:{item_name} +PENDING export", sort_by=current_sort)
            elif choice == "SA":
                current_sort = "alpha"
                console.clear()
                display_tasks(f"task project:{item_name} +PENDING export", sort_by=current_sort)
            elif choice == "SV":
                current_sort = "value"
                console.clear()
                display_tasks(f"task project:{item_name} +PENDING export", sort_by=current_sort)
            elif choice == "DT":
                dependency_tree(item_name)
            elif choice == "SD":
                dependency_input = ""
                manual_sort_dependencies(dependency_input)
                dependency_tree(item_name)
            elif choice == "DE":
                display_tasks(
                    f"task project:{item_name} +PENDING export", show_details=True, sort_by=current_sort
                )
            elif choice == "RD":
                task_ids_input = console.input(
                    "Enter the IDs of the tasks to remove dependencies (comma-separated):\n"
                )
                remove_task_dependencies(task_ids_input)
                dependency_tree(item_name)
            elif choice == "SP":
                call_and_process_task_projects()
            elif choice == "MP":
                multiple_projects_view()
            elif choice == "MA":
                main_menu()
            elif choice == "UD":
                update_metadata_field(item_name, "description")
            elif choice == "UO":
                update_metadata_field(item_name, "standard_or_outcome")
            elif choice == "AA":
                update_metadata_field(item_name, "annotations")
            elif choice == "AW":
                update_metadata_field(item_name, "workLogs")
            elif choice == "SYDB":
                sync_sultandb_with_taskwarrior(file_path)
                display_tasks(f"task project:{item_name} +PENDING export", sort_by=current_sort)
            elif choice == "TW":
                handle_task()
                display_tasks(f"task project:{item_name} +PENDING export", sort_by=current_sort)
            elif choice == "TM":
                task_ID = console.input("[cyan]Please enter the task ID: ")
                if task_ID:
                    console.clear()
                    task_manager(task_ID)
            elif choice == "NT":
                add_task_to_project(item_name)
                display_tasks(f"task project:{item_name} +PENDING export", sort_by=current_sort)
            elif choice == "AN":
                task_id = console.input("Enter the task ID to annotate: ")
                annotation = console.input("Enter the annotation: ")
                command = f"task {task_id} annotate {annotation}"
                execute_task_command(command)
                annotate_task(task_id, annotation)
            elif choice == "TD":
                task_id = console.input("Enter the task ID to mark as completed: ")
                command = f"task {task_id} done"
                execute_task_command(command)
            elif choice == "DD":
                task_id = console.input("Enter the task ID to assign a due date: ")
                due_date = console.input("Enter the due date (YYYY-MM-DD): ")
                command = f"task {task_id} modify due:{due_date}"
                execute_task_command(command)
            elif choice == "PV":
                base_filter = f"project:{item_name}"
                additional_filters = get_additional_filters()
                combined_filter = combine_filters(base_filter, additional_filters)
                eisenhower(combined_filter)
            elif choice == "ASP":
                try:
                    add_subproject_and_tasks(item_name)
                except KeyboardInterrupt:
                    print("\nCancelled.")
                except Exception as e:
                    print(f"Unexpected error: {e}")
            elif choice == "..":
                parent = parent_project_path(item_name)
                if parent:
                    # rerun search_project starting from parent
                    item_name = parent
                    print(f"Going to {item_name}..")
                    display_tasks(f"task project:{item_name} +PENDING export", sort_by=current_sort)
                else:
                    print("Already at top-level project.")
            elif choice == "":
                console.print("Exiting project management.")
                break
            else:
                console.print(
                    Panel("Invalid choice. Please try again.", style="bold red")
                )

    # x_x

    def load_project_metadata(file_path):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
        # Combine 'aors' and 'projects'
        aors = data.get("aors", [])
        projects = data.get("projects", [])

        # Add 'AoR.' prefix to AoR names
        for aor in aors:
            aor["name"] = "AoR." + aor["name"]

        items = aors + projects
        # Create a dictionary mapping project names to metadata
        project_metadata = {item["name"]: item for item in items}
        return project_metadata

    # x_x

    def multiple_projects_view():
        # Define your list of projects
        project_list = ["CN", "Biz", "ukNI"]

        # Define the list of tags to exclude
        excluded_tags = ["bean", "maybe", "docs", "domains", "grooming"]

        # Call the function to display tasks from these projects, excluding specified tags
        display_multiple_projects(project_list, excluded_tags)

    def display_multiple_projects(project_list, excluded_tags=None):
        if excluded_tags is None:
            excluded_tags = []
        console = Console()
        all_tasks = []

        # Load project metadata
        script_directory = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_directory, "variosdb.json")
        project_metadata = load_project_metadata(file_path)

        # Fetch tasks for each project
        for project in project_list:
            # Build the command for each project, including excluded tags
            command = ["task", f'project:"{project}"', "+PENDING"]

            # Add excluded tags to the command
            for tag in excluded_tags:
                command.append(f"-{tag}")  # Use -{tag} as per your practice

            command.append("export")

            # Debug: Print the command being executed
            # print(f"Executing command: {' '.join(command)}")

            result = subprocess.run(command, capture_output=True, text=True)
            if result.stdout:
                try:
                    tasks = json.loads(result.stdout)
                    if not tasks:
                        console.print(
                            f"No tasks found for project {project}.",
                            style="bold yellow",
                        )
                    else:
                        all_tasks.extend(tasks)
                except json.JSONDecodeError as e:
                    console.print(
                        f"Error decoding JSON for project {project}: {e}",
                        style="bold red",
                    )
            else:
                console.print(
                    f"No tasks found for project {project}.", style="bold yellow"
                )

        if not all_tasks:
            console.print("No tasks found for the provided projects.", style="bold red")
            return

        # Now process the combined list of tasks
        project_tag_map = defaultdict(lambda: defaultdict(list))
        now = datetime.now(timezone.utc).astimezone()

        for task in all_tasks:
            project = task.get("project", "No Project")
            tags = task.get("tags", ["No Tag"])

            description = task["description"]
            task_id = str(task["id"])

            due_date_str = task.get("due")
            due_date = parse_datetime(due_date_str) if due_date_str else None

            annotations = task.get("annotations", [])
            duration = task.get("duration", "")
            original_priority = task.get("priority")
            value = task.get("value")

            # Convert value to float if possible
            try:
                value = float(value) if value is not None else None
            except ValueError:
                value = None

            # Determine the priority level
            if original_priority:
                priority_level = original_priority.upper()
            elif value is not None:
                if value >= 2500:
                    priority_level = "H"
                elif value >= 700:
                    priority_level = "M"
                else:
                    priority_level = "L"
            else:
                priority_level = None

            # Assign colors based on priority level
            if priority_level == "H":
                priority_color = "bold red"
            elif priority_level == "M":
                priority_color = "bold yellow"
            elif priority_level == "L":
                priority_color = "bold green"
            else:
                priority_color = "bold magenta"

            # Initialize color to a default value
            color = "default_color"
            delta_text = ""
            if due_date:
                delta = due_date - now
                if delta.total_seconds() < 0:
                    color = "red"
                elif delta.days >= 365:
                    color = "steel_blue"
                elif delta.days >= 90:
                    color = "light_slate_blue"
                elif delta.days >= 30:
                    color = "green_yellow"
                elif delta.days >= 7:
                    color = "thistle3"
                elif delta.days >= 3:
                    color = "yellow1"
                elif delta.days == 0:
                    color = "bold turquoise2"
                else:
                    color = "bold orange1"
                delta_text = format_timedelta(delta)

            for tag in tags:
                project_tag_map[project][tag].append(
                    (
                        task_id,
                        description,
                        due_date,
                        annotations,
                        delta_text,
                        color,
                        duration,
                        priority_level,
                        priority_color,
                        value,
                    )
                )

        # Define lists of colors for levels and guide styles
        # level_colors = ['bright_red', 'bright_green', 'bright_yellow', 'bright_blue',
        # 				'bright_magenta', 'bright_cyan', 'bright_white']
        # guide_styles = ['red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']

        # Build the tree with different colors and guide styles for each level
        tree = Tree("Task Overview", style="green", guide_style="green")
        for project, tags in project_tag_map.items():
            if project == "No Project" and not any(tags.values()):
                continue
            project_levels = project.split(".")
            current_branch = tree
            for i, level in enumerate(project_levels):
                # Adding or finding the branch for each project level
                found_branch = None
                for child in current_branch.children:
                    if child.label.plain == level:
                        found_branch = child
                        break
                if not found_branch:
                    color = level_colors[
                        i % len(level_colors)
                    ]  # Assign color based on level depth
                    guide_style = guide_styles[
                        i % len(guide_styles)
                    ]  # Assign guide style based on level depth
                    found_branch = current_branch.add(
                        Text(level, style=color), guide_style=guide_style
                    )
                current_branch = found_branch

            # Get the metadata for the project or its parent
            metadata = None
            project_hierarchy = project.split(".")
            for j in range(len(project_hierarchy), 0, -1):
                partial_project = ".".join(project_hierarchy[:j])
                metadata = project_metadata.get(partial_project)
                if metadata and any(metadata.values()):
                    break
                else:
                    metadata = None

            if metadata:
                add_project_metadata_to_tree(metadata, current_branch)

            for tag, tasks in tags.items():
                if not tasks:
                    continue
                tag_branch = current_branch.add(
                    Text(tag, style="blue"), guide_style="blue"
                )
                for task_info in sorted(tasks, key=lambda x: (x[2] is None, x[2])):
                    (
                        task_id,
                        description,
                        due_date,
                        annotations,
                        delta_text,
                        delta_color,
                        duration,
                        priority_level,
                        priority_color,
                        value,
                    ) = task_info
                    # Build task line as before
                    # Square brackets in red
                    left_bracket = Text("[", style="red")
                    right_bracket = Text("] ", style="red")
                    # Task ID in turquoise
                    task_id_text = Text(task_id, style="turquoise2")
                    # Priority in color based on priority level
                    if priority_level:
                        priority_text = Text(
                            f"[{priority_level}] ", style=priority_color
                        )
                    else:
                        priority_text = Text("")
                    # Value in bold cyan
                    if value is not None:
                        value_text = Text(f"[{value}] ", style="bold cyan")
                    else:
                        value_text = Text("")
                    # Duration in cyan
                    duration_text = Text(
                        f"({duration}) " if duration else "", style="cyan"
                    )
                    # Description in white
                    description_text = Text(description + " ", style="white")
                    # Due date in the color determined earlier
                    if due_date:
                        due_date_text = Text(
                            due_date.strftime("%Y-%m-%d"), style=delta_color
                        )
                    else:
                        due_date_text = Text("")
                    # Delta text in the same color
                    delta_text_output = Text(
                        f" ({delta_text})" if delta_text else "", style=delta_color
                    )
                    # Combine texts for one line
                    task_line = (
                        left_bracket
                        + task_id_text
                        + right_bracket
                        + priority_text
                        + value_text
                        + duration_text
                        + description_text
                        + due_date_text
                        + delta_text_output
                    )
                    task_branch = tag_branch.add(task_line, guide_style="dim")
                    if annotations:
                        annotation_branch = task_branch.add(
                            Text("Annotations:", style="italic white"),
                            guide_style="dim",
                        )
                        for annotation in annotations:
                            entry_datetime = datetime.strptime(
                                annotation["entry"], "%Y%m%dT%H%M%SZ"
                            ).strftime("%Y-%m-%d %H:%M:%S")
                            annotation_text = Text(
                                f"{entry_datetime} - {annotation['description']}",
                                style="dim white",
                            )
                            annotation_branch.add(annotation_text, guide_style="dim")

        console.print(tree)

    def add_project_metadata_to_tree_2(metadata, branch):
        """Add project metadata as styled sub-branches to the given branch"""
        # Check if there's any metadata to display
        has_metadata = any(
            [
                metadata.get("description"),
                metadata.get("standard"),
                metadata.get("outcome"),
                metadata.get("annotations"),
                metadata.get("workLogs"),
            ]
        )

        if not has_metadata:
            return
        metadata_branch = branch.add(
            Text("📋 Metadata", style="bold cyan"), guide_style="cyan"
        )

        # Description field
        if metadata.get("description"):
            metadata_branch.add(
                Text.from_markup(
                    f"[bold steel_blue]Description:[/bold steel_blue] [white]{metadata['description']}[/white]"
                ),
                guide_style="steel_blue",
            )

        # Standard (for AoRs) or Outcome (for Projects)
        if metadata.get("standard"):
            metadata_branch.add(
                Text.from_markup(
                    f"[bold cornflower_blue]Standard:[/bold cornflower_blue] [white]{metadata['standard']}[/white]"
                ),
                guide_style="cornflower_blue",
            )
        elif metadata.get("outcome"):
            metadata_branch.add(
                Text.from_markup(
                    f"[bold green_yellow]Outcome:[/bold green_yellow] [white]{metadata['outcome']}[/white]"
                ),
                guide_style="green_yellow",
            )

        # Annotations
        if metadata.get("annotations"):
            annotations_branch = metadata_branch.add(
                Text("📝 Annotations", style="bold orchid"), guide_style="orchid"
            )
            for annotation in metadata["annotations"]:
                timestamp = datetime.fromisoformat(annotation["timestamp"]).strftime(
                    "%Y-%m-%d %H:%M"
                )
                annotations_branch.add(
                    Text.from_markup(
                        f"[yellow]{timestamp}[/yellow] [white]{annotation['content']}[/white]"
                    ),
                    guide_style="dim orchid",
                )

        # Work Logs
        if metadata.get("workLogs"):
            worklogs_branch = metadata_branch.add(
                Text("📊 Work Logs", style="bold gold1"), guide_style="gold1"
            )
            for log in metadata["workLogs"]:
                timestamp = datetime.fromisoformat(log["timestamp"]).strftime(
                    "%Y-%m-%d %H:%M"
                )
                worklogs_branch.add(
                    Text.from_markup(
                        f"[indian_red]{timestamp}[/indian_red] [white]{log['content']}[/white]"
                    ),
                    guide_style="dim gold1",
                )

    def add_project_metadata_to_tree(metadata, parent_branch):
        # Determine if the project is an AoR project
        project_name = metadata.get("name", "")
        is_aor = project_name.startswith("AoR.")

        content_present = False  # Flag to check if any metadata content is present
        metadata_branch = None  # Initialize metadata_branch as None

        # Description
        description = metadata.get("description", "")
        if description:
            if not metadata_branch:
                metadata_branch = parent_branch.add(
                    Text("Metadata", style="bold light_steel_blue1"), guide_style="dim"
                )
            label_text = Text("Description: ", style="bold cyan")
            value_text = Text(description, style="white")
            metadata_branch.add(label_text + value_text, guide_style="dim")
            content_present = True

        # Display 'Standard' for AoR projects, 'Outcome' for normal projects
        if is_aor:
            standard = metadata.get("standard", "")
            if standard:
                if not metadata_branch:
                    metadata_branch = parent_branch.add(
                        Text("Metadata", style="bold light_steel_blue1"),
                        guide_style="dim",
                    )
                label_text = Text("Standard: ", style="bold cyan")
                value_text = Text(standard, style="white")
                metadata_branch.add(label_text + value_text, guide_style="dim")
                content_present = True
        else:
            outcome = metadata.get("outcome", "")
            if outcome:
                if not metadata_branch:
                    metadata_branch = parent_branch.add(
                        Text("Metadata", style="bold light_steel_blue1"),
                        guide_style="dim",
                    )
                label_text = Text("Outcome: ", style="bold cyan")
                value_text = Text(outcome, style="white")
                metadata_branch.add(label_text + value_text, guide_style="dim")
                content_present = True

        # Annotations
        annotations = metadata.get("annotations", [])
        if annotations:
            if not metadata_branch:
                metadata_branch = parent_branch.add(
                    Text("Metadata", style="bold light_steel_blue1"), guide_style="dim"
                )
            annotations_branch = metadata_branch.add(
                Text("Annotations", style="bold yellow"), guide_style="dim"
            )
            for annotation in annotations:
                timestamp_str = annotation.get("timestamp", "")
                content = annotation.get("content", "")
                label_text = Text(f"{timestamp_str} - ", style="dim green")
                value_text = Text(content, style="white")
                annotations_branch.add(label_text + value_text, guide_style="dim")
            content_present = True

        # Work Logs
        work_logs = metadata.get("workLogs", [])
        if work_logs:
            if not metadata_branch:
                metadata_branch = parent_branch.add(
                    Text("Metadata", style="bold light_steel_blue1"), guide_style="dim"
                )
            work_logs_branch = metadata_branch.add(
                Text("Work Logs", style="bold yellow"), guide_style="dim"
            )
            for work_log in work_logs:
                timestamp_str = work_log.get("timestamp", "")
                content = work_log.get("content", "")
                label_text = Text(f"{timestamp_str} - ", style="green")
                value_text = Text(content, style="white")
                work_logs_branch.add(label_text + value_text, guide_style="bright")
            content_present = True

        # # Creation Date
        # creation_date_str = metadata.get('creation_date', '')
        # if creation_date_str:
        # 	if not metadata_branch:
        # 		metadata_branch = parent_branch.add(Text("Metadata", style="bold light_steel_blue1"), guide_style="dim")
        # 	label_text = Text("Creation Date: ", style="bold cyan")
        # 	value_text = Text(creation_date_str, style="white")
        # 	metadata_branch.add(label_text + value_text, guide_style="dim")
        # 	content_present = True

        # # Last Modified Date
        # last_modified_date_str = metadata.get('last_modified_date', '')
        # if last_modified_date_str:
        # 	if not metadata_branch:
        # 		metadata_branch = parent_branch.add(Text("Metadata", style="bold light_steel_blue1"), guide_style="dim")
        # 	label_text = Text("Last Modified Date: ", style="bold cyan")
        # 	value_text = Text(last_modified_date_str, style="white")
        # 	metadata_branch.add(label_text + value_text, guide_style="dim")
        # 	content_present = True

        # If no content was added, remove the Metadata branch if it exists
        if not content_present and metadata_branch:
            parent_branch.children.remove(metadata_branch)

    # x_x

    def add_task_to_project(project_name):
        task_descriptions = questionary.text(
            "Enter the descriptions for the new tasks (one per line):", multiline=True
        ).ask()
        task_descriptions_list = task_descriptions.split("\n")

        tasks = []

        for task_description in task_descriptions_list:
            if not task_description.strip():
                continue

            create_command = f"task add proj:{project_name} {task_description}"
            execute_task_command(create_command)

            task_id = get_latest_task_id()
            tasks.append((task_id, task_description))

        print("\nAdded Tasks:")
        for task_id, task_description in tasks:
            print(f"Task ID: {task_id}, Description: {task_description}")

        sort_dependencies = questionary.confirm(
            "Do you want to sort the dependencies for the tasks?"
        ).ask()
        if sort_dependencies:
            action = questionary.select(
                "Individual processing or bulk?",
                choices=["1. Individual", "2. Bulk assignment"],
            ).ask()

            if action.startswith("1"):
                for task_id, task_description in tasks:
                    has_dependencies = questionary.confirm(
                        f"Does the task '{task_description}' have dependencies?"
                    ).ask()

                    if has_dependencies:
                        dependency_type = questionary.select(
                            "Is this a blocking task (secondary) or does it have dependent tasks (primary)?",
                            choices=["Secondary task", "Primary task"],
                        ).ask()

                        if dependency_type == "Secondary task":
                            blocking_task_id = questionary.text(
                                "Enter the ID of the task this is a sub-task of:"
                            ).ask()
                            modify_command = (
                                f"task {blocking_task_id} modify depends:{task_id}"
                            )
                            execute_task_command(modify_command)
                            print(
                                f"Task {task_id} is now a sub-task of {blocking_task_id}."
                            )
                        elif dependency_type == "Primary task":
                            dependent_task_ids = questionary.text(
                                "Enter the IDs of the tasks that depend on this (comma-separated):"
                            ).ask()
                            modify_dependent_tasks(task_id, dependent_task_ids)
            elif action.startswith("2"):
                manual_sort_dependencies("")

    def get_latest_task_id():
        export_command = "task +LATEST export"
        try:
            proc = subprocess.run(
                export_command, shell=True, text=True, capture_output=True
            )
            if proc.stdout:
                tasks = json.loads(proc.stdout)
                if tasks:
                    return str(tasks[0]["id"])
            if proc.stderr:
                print(proc.stderr)
        except Exception as e:
            print(f"An error occurred while exporting the latest task: {e}")
        return None

    def execute_task_command(command):
        try:
            proc = subprocess.run(command, shell=True, text=True, capture_output=True)
            if proc.stdout:
                print(proc.stdout)
            if proc.stderr:
                print(proc.stderr)
        except Exception as e:
            print(f"An error occurred while executing the task command: {e}")

    # def modify_dependent_tasks(dependent_ids, task_id):
    # 	ids = dependent_ids.split(',')
    # 	for id in ids:
    # 		modify_command = f"task {id.strip()} modify depends:{task_id}"
    # 		execute_task_command(modify_command)
    # 		print(f"Task {task_id} now depends on task {id.strip()}.")

    def manual_sort_dependencies(sub_task_ids):
        console.print("\n[bold cyan]Manual Sorting of Dependencies:[/bold cyan]")
        for sub_task_id in sub_task_ids:
            console.print(f"- Sub-task ID: {sub_task_id}")

        console.print(
            "\nEnter the dependencies in the format 'task_id>subtask1=subtask2=subtask3>further_subtask'."
        )
        console.print(
            "Use '>' for sequential dependencies and '=' for parallel subtasks."
        )
        console.print("You can enter multiple chains separated by commas.")
        console.print("Type 'done' when finished.\n")

        while True:
            dependency_input = Prompt.ask("> ").strip()
            if dependency_input.lower() == "done":
                break

            # Split the input into individual chains
            chains = dependency_input.split(",")

            with console.status(
                "[bold green]Setting dependencies...", spinner="dots"
            ) as status:
                for chain in chains:
                    if ">" in chain or "=" in chain:
                        # Split the chain into levels
                        levels = chain.split(">")

                        for i in range(len(levels) - 1):
                            parent_tasks = levels[i].split("=")
                            child_tasks = levels[i + 1].split("=")

                            # The last task in parent_tasks depends on all child_tasks
                            parent_task = parent_tasks[-1].strip()
                            for child_task in child_tasks:
                                modify_command = f"task {parent_task} modify depends:{child_task.strip()}"
                                execute_task_command(modify_command)
                                console.print(
                                    f"Task {parent_task} now depends on task {child_task.strip()}."
                                )
                    else:
                        console.print(
                            f"[bold yellow]Warning:[/bold yellow] Skipping invalid chain: {chain}"
                        )

        console.print("[bold green]Dependency setting completed.[/bold green]")

    def remove_task_dependencies(task_ids_input):
        console.print("\n[bold cyan]Removing Task Dependencies[/bold cyan]")

        # Split the input by commas
        id_groups = task_ids_input.split(",")

        all_ids = []

        # Process each group (single ID or range)
        for group in id_groups:
            group = group.strip()
            if "-" in group:
                # This is a range
                start, end = map(int, group.split("-"))
                all_ids.extend(range(start, end + 1))
            else:
                # This is a single ID
                all_ids.append(int(group))

        with console.status(
            "[bold green]Removing dependencies...", spinner="dots"
        ) as status:
            for id in all_ids:
                modify_command = f"task {id} modify depends:"
                execute_task_command(modify_command)
                console.print(f"Dependencies removed from task {id}.")

        console.print("[bold green]Dependency removal completed.[/bold green]")

    def interactive_prompt(file_path):
        run_interactive_prompt(
            file_path,
            aors,
            projects,
            sync_with_taskwarrior,
            update_item,
            get_tags_for_item,
            view_data,
            search_data,
            call_and_process_task_projects,
            search_task,
            clear_data,
            basic_summary,
            detailed_summary,
            display_inbox_tasks,
            display_due_tasks,
            handle_task,
            print_tasks_for_selected_day,
            display_overdue_tasks,
            recurrent_report,
            eisenhower,
            task_control_center,
        )

    def search_data(aors, projects):
        return run_search_data(aors, projects)

    def clear_data(aors, projects, file_path):
        return run_clear_data(aors, projects, file_path)

    def confirm_action(message):
        return run_confirm_action(message)

    def get_tags_for_aor(aor_name):
        return run_get_tags_for_aor(aor_name)

    def sync_with_taskwarrior(aors, projects, file_path):
        return run_sync_with_taskwarrior(aors, projects, file_path)


    def get_tasks(filter_query):
        command = f"task {filter_query} +PENDING export"
        output = run_taskwarrior_command(command)
        if output:
            # Parse the JSON output into Python objects
            tasks = json.loads(output)
            return tasks
        else:
            return []


    dimensions = [
        {
            "name": "Impact",
            "group": "1. Strategic Impact",
            "question": "How significant is this task to achieving your long-term strategic goals and overall impact?",
            "type": "benefit",
            "answers": [
                {"code": "Critical", "text": "Critical: indispensable for mission success", "value": 5},
                {"code": "Very Important", "text": "Very important: key strategic objective", "value": 4},
                {"code": "Moderately Important", "text": "Moderately important: contributes significantly", "value": 3},
                {"code": "Somewhat Important", "text": "Somewhat important: offers marginal gains", "value": 2},
                {"code": "Low Impact", "text": "Low impact: minimal contribution", "value": 1},
                {"code": "No Impact", "text": "No impact at all", "value": 0},
            ],
            "weight": 5,
        },
        {
            "name": "Urgency",
            "group": "2. Urgency",
            "question": "How soon does this task need to be completed?",
            "type": "benefit",
            "answers": [
                {"code": "Immediate", "text": "Must be done immediately/today", "value": 5},
                {"code": "This Week", "text": "Needed this week", "value": 4},
                {"code": "This Month", "text": "Needed this month", "value": 3},
                {"code": "This Quarter", "text": "Needed this quarter", "value": 2},
                {"code": "This Year", "text": "Needed this year", "value": 1},
                {"code": "No Pressure", "text": "No time pressure", "value": 0},
            ],
            "weight": 5,
        },
        {
            "name": "Consequences",
            "group": "3. Consequences",
            "question": "What are the long-term consequences or reach if this task is not completed?",
            "type": "benefit",
            "answers": [
                {"code": "Severe", "text": "Severe negative impact with far-reaching effects", "value": 5},
                {"code": "Major", "text": "Major problems with significant long-term issues", "value": 4},
                {"code": "Moderate", "text": "Moderate issues that could affect outcomes", "value": 3},
                {"code": "Minor", "text": "Minor inconveniences with limited impact", "value": 2},
                {"code": "Very Little", "text": "Very little impact on long-term goals", "value": 1},
                {"code": "None", "text": "No noticeable consequences", "value": 0},
            ],
            "weight": 5,
        },
        {
            "name": "Cost",
            "group": "4. Cost",
            "question": "How much cost (in time/resources) will this task require?",
            "type": "cost",
            "answers": [
                {"code": "Massive", "text": "Massive project: requires months of effort", "value": 5},
                {"code": "Large", "text": "Large project: requires weeks of effort", "value": 4},
                {"code": "Medium", "text": "Medium project: requires days of work", "value": 3},
                {"code": "Small", "text": "Small task: takes hours", "value": 2},
                {"code": "Quick", "text": "Quick task: less than 1 hour", "value": 1},
                {"code": "Minimal", "text": "Minimal effort: minutes", "value": 0},
            ],
            "weight": 5,
        },
        {
            "name": "Risk",
            "group": "5. Risk",
            "question": "How risky or uncertain is the outcome of this task?",
            "type": "cost",
            "answers": [
                {"code": "High", "text": "High risk: complete lack of clarity, major unknowns", "value": 5},
                {"code": "Significant", "text": "Significant risk: many uncertainties present", "value": 4},
                {"code": "Moderate", "text": "Moderate risk: several unclear aspects", "value": 3},
                {"code": "Low", "text": "Low risk: minor uncertainties", "value": 2},
                {"code": "Very Low", "text": "Very low risk: mostly clear", "value": 1},
                {"code": "None", "text": "No risk: crystal clear and well-defined", "value": 0},
            ],
            "weight": 3,
        },
    ]





    # Define a custom style for the prompt tokens.
    custom_style = Style.from_dict({
        "qmark": "fg:#e91e63 bold",         # Question mark (e.g., ❓)
        "question": "bold",                  # The question text
        "instruction": "fg:#ff9d00 italic",   # Instruction text (e.g., how to navigate)
        "pointer": "fg:#ef029a bold",         # Pointer that indicates the selected option
        "highlighted": "fg:#9aef02 bold",     # Highlighted option style
        "selected": "fg:#cc5454",             # Style for a selected item
        "separator": "fg:#cc5454",            # Separator style (if any)
        "disabled": "fg:#efce02 italic",      # Disabled items (e.g., question headers)
    })


    def get_task_value(dimensions):
        # Generate the list of choices
        choices = generate_choices(dimensions)

        # Present all questions and options in a single list
        selected_values = questionary.checkbox(
            message="Please answer the following questions (select one per question):",
            choices=choices,
            validate=lambda selected: (
                True if len(selected) <= len(dimensions) else "You can only select one answer per question."
            ),
            qmark="❓",  # Custom question mark
            instruction="(Use space to select, enter to confirm)",
        ).ask()

        # Map selected values back to their scores and calculate the total task value
        total_value = 0
        for selected in selected_values:
            question_idx, answer_code = selected.split("_")  # Extract question index and answer code
            question_idx = int(question_idx)
            for answer in dimensions[question_idx]["answers"]:
                if answer["code"] == answer_code:
                    total_value += answer["value"] * dimensions[question_idx]["weight"]
                    break

        return total_value


    def display_options(dimension_name, dimension_data):
        # Create a table with no header, simple box, and minimal styling
        table = Table(
            show_header=False,
            box=box.SIMPLE,
            show_edge=False,
            pad_edge=False,
            style="dim",
            padding=(0, 2),  # Add padding for better spacing
        )
        
        # Define a list of colors for the options
        colors = ["red", "orange3", "yellow", "green", "blue", "purple"]
        
        # Add rows to the table with colored values and descriptions
        for (description, value), color in zip(dimension_data["options"], colors):
            table.add_row(
                f"[bold {color}]{value}[/bold {color}]",
                "—",  # Use an em dash for a cleaner separator
                description,
            )
        
        # Calculate the maximum width needed for options
        max_option_width = max(len(desc) for desc, _ in dimension_data["options"])
        needed_width = max(80, max_option_width + 15)
        
        # Create a panel with just the table and title
        panel = Panel(
            table,
            title=f"[bold]{dimension_name}[/bold]",
            title_align="left",
            box=box.ROUNDED,
            expand=False,  # Ensure the panel does not expand to terminal width
            width=needed_width,  # Set explicit width based on content
            padding=(1, 2),  # Add padding around the panel content
            style="dim",  # Apply a subtle style to the panel
        )
        
        question_text = Text(f"\n{dimension_data['question']}", style="italic")
        result = Group(panel, question_text)
        
        return result

    def get_score(dimension_name, dimension_data):
        console.print()
        console.print(display_options(dimension_name, dimension_data))

        while True:
            try:
                value = IntPrompt.ask("[bold cyan]Enter rating (0-5)[/bold cyan]")
                if 0 <= value <= 5:
                    selected_description = next(
                        desc
                        for desc, val in dimension_data["options"]
                        if val == value
                    )
                    console.print(f"[dim]Selected: {selected_description}[/dim]")
                    return value
                console.print(
                    "[bold red]Please enter a value between 0 and 5[/bold red]"
                )
            except ValueError:
                console.print("[bold red]Please enter a valid number[/bold red]")


    def display_filter_options(filter_options):
        """
        Display the filter options in a formatted table using Rich.
        """
        table = Table(title="[bold cyan]Preset Filters[/bold cyan]", box=box.ROUNDED)
        table.add_column("Number", style="cyan", justify="center")
        table.add_column("Filter Name", style="green")
        table.add_column("Filter Query", style="dim")

        for key, (name, query) in filter_options.items():
            table.add_row(key, name, query)

        console.print(table)

    def get_filter_choice(filter_options):
        """
        Prompt the user to select a filter or enter a custom one.
        """
        display_filter_options(filter_options)

        filter_query = Prompt.ask(
            "[bold cyan]Enter your Taskwarrior filter or select a number:[/bold cyan]",
            choices=list(filter_options.keys()) + ["custom"],
            default="custom",
        )

        if filter_query in filter_options:
            selected_filter = filter_options[filter_query]
            console.print(
                f"[bold green]Using preset filter:[/bold green] [dim]{selected_filter[1]}[/dim]"
            )
            return selected_filter[1]
        else:
            custom_filter = Prompt.ask("[bold cyan]Enter your custom filter:[/bold cyan]")
            console.print(f"[bold green]Using custom filter:[/bold green] [dim]{custom_filter}[/dim]")
            return custom_filter

    def get_fork_choice():
        """
        Prompt the user to choose between priority assessment, processing, or Eisenhower matrix.
        Displays a description of each option.
        """
        # Create a table to display the options and their descriptions
        table = Table(title="[bold cyan]Choose an Action[/bold cyan]", box=box.ROUNDED)
        table.add_column("Option", style="cyan", justify="center")
        table.add_column("Description", style="green")

        # Add rows for each option
        table.add_row(
            "i",
            "Assess priority: Evaluate the task's priority based on importance, urgency, and other factors.",
        )
        table.add_row(
            "o",
            "Process: Mark tasks as done, delete them, or skip them without assessing priority.",
        )
        table.add_row(
            "e",
            "Eisenhower Matrix: Categorize tasks into the Eisenhower Matrix (Urgent/Important, Not Urgent/Important, etc.).",
        )

        # Display the table
        console.print(table)

        # Prompt the user to choose an option
        fork = Prompt.ask(
            "[bold cyan]Choose an action (i/o/e):[/bold cyan]",
            choices=["i", "o", "e"],
            default="i",
        )

        return fork



    def generate_choices(dimensions):
        """
        Create a list of Questionary choices.
        Each dimension header is disabled (and will use the 'disabled' style)
        and each answer option is displayed as a regular Choice.
        """
        choices = []
        for idx, dimension in enumerate(dimensions):
            # Add a question header (disabled)
            choices.append(
                Choice(
                    title=f"{dimension['group']}: {dimension['question']}",
                    disabled=True
                )
            )
            # Add answer options with a unique identifier as the value.
            for answer in dimension["answers"]:
                choices.append(
                    Choice(
                        title=f"{answer['code']}: {answer['text']}",
                        value=f"{idx}_{answer['code']}"
                    )
                )
        return choices

    def get_modular_scores(dimensions):
        """
        Use a single checkbox prompt to collect one answer per dimension.
        Returns a dictionary mapping each dimension name to its chosen answer value.
        """
        selected_values = checkbox(
            message="Please answer each question (select one answer per question):",
            choices=generate_choices(dimensions),
            validate=lambda selected: (
                True if len(selected) == len(dimensions)
                else f"You must select exactly one answer per question. (Selected {len(selected)} out of {len(dimensions)})"
            ),
            qmark="❓",
            instruction="(Use space to select, then Enter to confirm)",
            style=custom_style
        ).ask()

        scores = {}
        for selected in selected_values:
            # Expected format: "index_answerCode"
            question_idx, answer_code = selected.split("_")
            question_idx = int(question_idx)
            dimension = dimensions[question_idx]
            # Find and assign the answer value for the dimension.
            for answer in dimension["answers"]:
                if answer["code"] == answer_code:
                    scores[dimension["name"]] = answer["value"]
                    break
        return scores


   


    # 4. Process scores modularly (benefits vs. costs)
    def process_modular_scores(scores, dimensions):
        # Calculate benefit and cost scores dynamically based on dimension type.
        benefit_score = sum(
            scores[dim["name"]] * dim["weight"] for dim in dimensions if dim["type"] == "benefit"
        )
        cost_score = sum(
            scores[dim["name"]] * dim["weight"] for dim in dimensions if dim["type"] == "cost"
        )
        net_score = benefit_score - cost_score

        # Compute theoretical extremes for normalization:
        max_benefit = sum(
            max(answer["value"] for answer in dim["answers"]) * dim["weight"]
            for dim in dimensions if dim["type"] == "benefit"
        )
        max_cost = sum(
            max(answer["value"] for answer in dim["answers"]) * dim["weight"]
            for dim in dimensions if dim["type"] == "cost"
        )
        min_net = -max_cost  # worst-case net score
        max_net = max_benefit  # best-case net score

        # Normalize net_score to a percentage (0-100)
        normalized_value = round(((net_score - min_net) / (max_net - min_net)) * 100, 2)

        # Determine priority based on normalized value
        if normalized_value >= 70:
            priority = "H"  # High
        elif normalized_value >= 40:
            priority = "M"  # Medium
        else:
            priority = "L"  # Low

        return {
            "benefit_score": benefit_score,
            "cost_score": cost_score,
            "net_score": net_score,
            "normalized_value": normalized_value,
            "priority": priority,
        }

    def rate_task(task):
        scores = get_modular_scores(dimensions)
        results = process_modular_scores(scores, dimensions)
        
        console.print(f"[bold green]Calculated Benefit Score: {results['benefit_score']}[/bold green]")
        console.print(f"[bold green]Calculated Cost Score: {results['cost_score']}[/bold green]")
        console.print(f"[bold green]Net Score: {results['net_score']}[/bold green]")
        console.print(f"[bold green]Normalized Value: {results['normalized_value']}%[/bold green]")
        console.print(f"[bold green]Priority: {results['priority']}[/bold green]")
        
        update_command = f"task {task['uuid']} modify value:{results['normalized_value']:.2f} priority:{results['priority']}"
        run_taskwarrior_command(update_command)
        console.print(
            f"[bold green]Updated task {task['uuid']} with value: {results['normalized_value']:.2f} and priority: {results['priority']}[/bold green]"
        )

    def eisenhower(custom_filter=None):
        """
        Implements the Eisenhower routine:
        - Selects tasks based on a filter (preset or custom)
        - Presents the user with actions (rate, done, delete, skip)
        - Uses the modular rating functions if the user chooses to rate a task.
        """
        try:
            # Define filter options for Taskwarrior queries
            filter_options = {
                "1": ("Overdue", "+OVERDUE +PENDING"),
                "2": ("Due Today", "due:today"),
                "3": ("Due Tomorrow", "due:tomorrow"),
            }

            if custom_filter:
                filter_query = custom_filter
                console.print(f"[bold green]Using provided filter:[/bold green] [dim]{filter_query}[/dim]")
            else:
                filter_query = get_filter_choice(filter_options)

            # Prompt the user for the action mode (assessing priority, processing, or matrix categorization)
            fork = get_fork_choice()  # Assume this function displays options and returns "i" for assessment, etc.

            if fork == "i":
                tasks = get_tasks(filter_query)
                
                task_count = len(tasks)
                if task_count == 0:
                    console.print(f"[bold yellow]No tasks found matching the filter: {filter_query}[/bold yellow]")
                else:
                    console.print(
                        f"[bold green]Found {task_count} task{'s' if task_count != 1 else ''} matching the filter: {filter_query}[/bold green]"
                    )
                
                for task in tasks:
                    print(delimiter)
                    display_task_details(task["uuid"])
                    console.print(Fore.CYAN + f"\nProcessing task: {task['description']}")
                    
                    if task.get("value", 0) > 0:
                        console.print(f"Task already has a value of {task['value']}.")
                    
                    action = Prompt.ask(
                        "[bold cyan]Choose an action:[/bold cyan]",
                        choices=["rate", "done", "delete", "skip"],
                        default="skip",
                    )

                    if action == "done":
                        run_taskwarrior_command(f"task {task['uuid']} done")
                        console.print("[bold green]Task marked as done.[/bold green]")
                        continue
                    elif action == "delete":
                        run_taskwarrior_command(f"task {task['uuid']} delete -y")
                        console.print("[bold green]Task deleted.[/bold green]")
                        continue
                    elif action == "skip":
                        console.print("[bold blue]Skipping task.[/bold blue]")
                        continue
                    elif action == "rate":
                        rate_task(task)

            elif fork == "o":
                tasks = get_tasks(filter_query)
                for task in tasks:
                    
                    process_task(task)
            elif fork == "e":
                tasks = get_tasks(filter_query)
                for task in tasks:
                    print(delimiter)
                    display_task_details(task["uuid"])
                    print(
                        Fore.CYAN
                        + f"\nAssessing task using the Eisenhower matrix: {task['description']}"
                    )
                    matrix_section = ask_eisenhower_matrix()
                    if matrix_section in ["skip", "done", "del"]:
                        if matrix_section == "skip":
                            print(Fore.BLUE + "Skipping task.")
                        elif matrix_section == "done":
                            run_taskwarrior_command(f"task {task['uuid']} done")
                            print(Fore.GREEN + "Marked task as done.")
                        elif matrix_section == "del":
                            run_taskwarrior_command(f"task {task['uuid']} delete -y")
                            print(Fore.GREEN + f"Deleted task {task['uuid']}")
                        continue

                    # Assign attributes based on the Eisenhower matrix section
                    if matrix_section == 1:
                        update_command = (
                            f"task {task['uuid']} modify +IU-do-now priority:H"
                        )
                    elif matrix_section == 2:
                        update_command = (
                            f"task {task['uuid']} modify +INU-schedule priority:M"
                        )
                    elif matrix_section == 3:
                        update_command = (
                            f"task {task['uuid']} modify +UNI-delegate priority:L"
                        )
                    elif matrix_section == 4:
                        update_command = f"task {task['uuid']} modify +NINU-eliminate"
                    run_taskwarrior_command(update_command)
                    print(
                        Fore.GREEN
                        + "Updated task with Eisenhower matrix section attributes."
                    )
            else:
                print(Fore.RED + "Invalid option selected. Exiting.")
                return
        except KeyboardInterrupt:
            print(Fore.RED + "\nProcess interrupted. Exiting.")
            return

    def ask_eisenhower_matrix():
        while True:
            response = (
                input(
                    Fore.YELLOW
                    + "In which section of the Eisenhower matrix is this task?\n1 - Important and Urgent\n2 - Important and Not Urgent\n3 - Not Important and Urgent\n4 - Not Important and Not Urgent\n('skip', 'done', 'del'): \n:=> "
                )
                .strip()
                .lower()
            )
            if response in ["skip", "done", "del"]:
                return response
            try:
                response = int(response)
                if 1 <= response <= 4:
                    return response
                else:
                    print(Fore.RED + "Please enter a number between 1 and 4.")
            except ValueError:
                print(
                    Fore.RED
                    + "Invalid input. Please enter a number between 1 and 4, 'skip', 'done', or 'del'."
                )

    # =========================================================

    def short_uuid(uuid):
        """Return the short version of the UUID (up to the first dash)."""
        return uuid.split("-")[0]

    def get_inbox_tasks(filter):
        command = f"task {filter} +PENDING -CHILD export"
        output = run_taskwarrior_command(command)
        if output:
            tasks = json.loads(output)
            return tasks
        else:
            return []

    # def process_input(lines):
    #     #
    #     level_text = {0: ""}
    #     last_level = -1
    #     spaces_per_level = 2  # adjust this if needed

    #     # Ignore the first 4 and last 3 lines
    #     lines = lines[3:] if len(lines) <= 7 else lines[3:-2]
    #     output_lines = []  # Initialize the list to store all processed projects

    #     for i, line in enumerate(lines):
    #         stripped = line.lstrip()
    #         level = len(line) - len(stripped)
    #         print(level)

    #         # Split the line into text and number, and only keep the text
    #         parts = stripped.split()
    #         if len(parts) < 2:
    #             continue  # Skip lines that don't have both text and a number

    #         text = parts[0]

    #         if level % spaces_per_level != 0:
    #             raise ValueError(f"Invalid indentation level in input on line {i + 5}")

    #         level //= spaces_per_level

    #         if level > last_level + 1:
    #             raise ValueError(
    #                 f"Indentation level increased by more than 1 on line {i + 5}"
    #             )

    #         level_text[level] = text
    #         # Clear all deeper levels
    #         level_text = {k: v for k, v in level_text.items() if k <= level}

    #         output_line = ".".join(level_text[l] for l in range(level + 1))
    #         output_lines.append(output_line)  # Add each processed project to the list

    #         last_level = level

    #     return output_lines  # Return the list of all processed projects

    def call_and_process_task_projects2():
        result = subprocess.run(["task", "projects"], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        project_list = process_input(lines)
        # for project in project_list:
        # 	print(f"{project}\n")
        return project_list

    def review_projects():
        lines = call_and_process_task_projects2()

        # Ask user where they want to start
        start_choice = console.input(
            "[deep_sky_blue1]Do you want to start from the beginning (B), \nfrom a specific project (S), or \nskip to No Project / Overdue tasks (K)? "
        )

        if start_choice.lower() == "k":
            lines = []  # Skip all projects
        elif start_choice.lower() == "s":
            project_list = call_and_process_task_projects2()
            project_name = search_project3(project_list)
            try:
                start_index = lines.index(project_name)
                lines = lines[start_index:]
            except ValueError:
                console.print(
                    Panel(
                        f"Project '{project_name}' not found. Starting from the beginning.",
                        style="bold yellow",
                    )
                )
        # If 'B' or any other key, start from the beginning

        for project in lines:
            # Check if the project has pending tasks
            if not has_pending_tasks(project):
                continue  # Skip to the next project if there are no pending tasks

            while True:
                # Display tasks for the current project
                display_tasks(
                    f"task project:{project} project.not:{project}. +PENDING export"
                )
                print("\n")
                # Create a table for menu options
                table = Table(
                    box=box.ROUNDED,
                    expand=False,
                    show_header=False,
                    border_style="cyan",
                )
                table.add_column("Option", style="orange_red1")
                table.add_column("Description", style="deep_sky_blue1")

                table.add_row("TM", "Task Manager")
                table.add_row("NT", "Add new task")
                table.add_row("TW", "TW prompt")
                table.add_row("DT", "View Dependency Tree")
                table.add_row("AN", "Annotate task")
                table.add_row("DD", "Assign due date")
                table.add_row("PV", "Process Value/Priority")
                table.add_row("DE", "Show Details")
                table.add_row("TD", "Mark task as completed")
                table.add_row("NP", "Next project")
                table.add_row("SP", "Save progress and exit")
                table.add_row("Enter", "Exit review")
                table.add_row("R", "Refresh")

                console.print(
                    Panel(table, title=f"Reviewing project: {project}", expand=False)
                )

                choice = console.input("[deep_sky_blue1]Enter your choice: ")

                if choice.lower() == "tm":
                    task_ID = console.input("[cyan]Please enter the task ID: ")
                    if task_ID:
                        task_manager(task_ID)
                elif choice.lower() == "nt":
                    add_task_to_project(project)
                elif choice.lower() == "tw":
                    handle_task()
                elif choice.lower() == "dt":
                    dependency_tree(project)
                elif choice.lower() == "td":
                    task_id = console.input("Enter the task ID to mark as completed: ")
                    command = f"task {task_id} done"
                    execute_task_command(command)
                elif choice.lower() == "an":
                    task_ID = console.input("[cyan]Please enter the task ID: ")
                    if task_ID:
                        annotation = console.input("[cyan]Enter the annotation: ")
                        subprocess.run(["task", task_ID, "annotate", annotation])
                elif choice.lower() == "dd":
                    task_ID = console.input("[cyan]Please enter the task ID: ")
                    if task_ID:
                        due_date = console.input("[cyan]Enter the due date: ")
                        subprocess.run(["task", task_ID, "modify", f"due:{due_date}"])
                elif choice.lower() == "pv":
                    base_filter = (f"project:{project} project.not:{project}.")
                    additional_filters = get_additional_filters()
                    combined_filter = combine_filters(base_filter, additional_filters)
                    eisenhower(combined_filter)
                elif choice.lower() == "de":
                    display_tasks(f"task project:{project} project.not:{project}. +PENDING export", show_details=True)
                    prompt("Press enter when you finished analysing!")
                elif choice.lower() == "np":
                    break  # Move to the next project
                elif choice.lower() == "r":
                    console.clear()
                elif choice.lower() == "sp":
                    console.print(
                        Panel(
                            f"Progress saved. You can resume from project '{project}' next time.",
                            style="bold green",
                        )
                    )
                    return  # Exit the review process
                elif choice == "":
                    return  # Exit the entire review process
                else:
                    console.print(
                        Panel("Invalid choice. Please try again.", style="bold red")
                    )

        console.print(
            Panel(
                "All projects with pending tasks have been processed.",
                style="bold green",
            )
        )

        # Review tasks without a project
        while True:
            # Check if there are any tasks without a project
            try:
                result = subprocess.run(
                    ["task", "project:", "+PENDING", "count"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                task_count = int(result.stdout.strip())
            except subprocess.CalledProcessError as e:
                console.print(
                    Panel(f"Error running task command: {e}", style="bold red")
                )
                return
            except ValueError:
                console.print(Panel("Error parsing task count", style="bold red"))
                return

            if task_count == 0:
                console.print(
                    Panel(
                        "No tasks without a project. Moving to overdue tasks.",
                        style="bold green",
                    )
                )
                break

            console.print(
                Panel(
                    f"Found {task_count} tasks without a project. Starting review.",
                    style="bold green",
                )
            )

            # Display tasks without a project
            display_tasks("task project: +PENDING export")
            print("\n")
            # Create a table for menu options
            table = Table(
                box=box.ROUNDED, expand=False, show_header=False, border_style="cyan"
            )
            table.add_column("Option", style="orange_red1")
            table.add_column("Description", style="deep_sky_blue1")

            table.add_row("TM", "Task Manager")
            table.add_row("NT", "Add new task")
            table.add_row("TW", "TW prompt")
            table.add_row("AN", "Annotate task")
            table.add_row("DD", "Assign due date")
            table.add_row("DE", "Show Details")
            table.add_row("TD", "Mark task as completed")
            table.add_row("SP", "Save progress and exit")
            table.add_row("Enter", "Continue to overdue tasks")
            table.add_row("R", "Refresh")

            console.print(
                Panel(table, title="Reviewing tasks without a project", expand=False)
            )

            choice = console.input("[deep_sky_blue1]Enter your choice: ")

            if choice.lower() == "tm":
                task_ID = console.input("[cyan]Please enter the task ID: ")
                if task_ID:
                    task_manager(task_ID)
            elif choice.lower() == "nt":
                add_task_to_project(
                    ""
                )  # Assuming this function can handle empty project name
            elif choice.lower() == "tw":
                handle_task()
            elif choice.lower() == "de":
                display_tasks(f"task project: +PENDING export", show_details=True)
                prompt("\n\n\nPress enter when you finished analysing!")
            elif choice.lower() == "td":
                task_id = console.input("Enter the task ID to mark as completed: ")
                command = f"task {task_id} done"
                execute_task_command(command)
            elif choice.lower() == "an":
                task_ID = console.input("[cyan]Please enter the task ID: ")
                if task_ID:
                    annotation = console.input("[cyan]Enter the annotation: ")
                    subprocess.run(["task", task_ID, "annotate", annotation])
            elif choice.lower() == "dd":
                task_ID = console.input("[cyan]Please enter the task ID: ")
                if task_ID:
                    due_date = console.input("[cyan]Enter the due date: ")
                    subprocess.run(["task", task_ID, "modify", f"due:{due_date}"])
            elif choice.lower() == "r":
                console.clear()
            elif choice.lower() == "sp":
                console.print(
                    Panel("Progress saved. Exiting review.", style="bold green")
                )
                return  # Exit the review process
            elif choice == "":
                break  # Proceed to overdue tasks
            else:
                console.print(
                    Panel("Invalid choice. Please try again.", style="bold red")
                )

        # Review overdue tasks
        while True:
            # Check if there are any overdue tasks
            try:
                result = subprocess.run(
                    ["task", "due.before:today", "+PENDING", "count"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                overdue_count = int(result.stdout.strip())
            except subprocess.CalledProcessError as e:
                console.print(
                    Panel(f"Error running task command: {e}", style="bold red")
                )
                return
            except ValueError:
                console.print(
                    Panel("Error parsing overdue task count", style="bold red")
                )
                return

            if overdue_count == 0:
                console.print(
                    Panel("No overdue tasks. Review complete.", style="bold green")
                )
                break

            console.print(
                Panel(
                    f"Found {overdue_count} overdue tasks. Starting review.",
                    style="bold green",
                )
            )

            # Display overdue tasks
            display_tasks("task due.before:today +PENDING export")
            print("\n")
            # Create a table for menu options
            table = Table(
                box=box.ROUNDED, expand=False, show_header=False, border_style="cyan"
            )
            table.add_column("Option", style="orange_red1")
            table.add_column("Description", style="deep_sky_blue1")

            table.add_row("TM", "Task Manager")
            table.add_row("AN", "Annotate task")
            table.add_row("DD", "Change due date")
            table.add_row("DE", "Show Details")
            table.add_row("TD", "Mark task as completed")
            table.add_row("SP", "Save progress and exit")
            table.add_row("Enter", "Exit review")
            table.add_row("R", "Refresh")

            console.print(Panel(table, title="Reviewing overdue tasks", expand=False))

            choice = console.input("[deep_sky_blue1]Enter your choice: ")

            if choice.lower() == "tm":
                task_ID = console.input("[cyan]Please enter the task ID: ")
                if task_ID:
                    task_manager(task_ID)
            elif choice.lower() == "an":
                task_ID = console.input("[cyan]Please enter the task ID: ")
                if task_ID:
                    annotation = console.input("[cyan]Enter the annotation: ")
                    subprocess.run(["task", task_ID, "annotate", annotation])
            elif choice.lower() == "dd":
                task_ID = console.input("[cyan]Please enter the task ID: ")
                if task_ID:
                    new_due_date = console.input("[cyan]Enter the new due date: ")
                    subprocess.run(["task", task_ID, "modify", f"due:{new_due_date}"])
            elif choice.lower() == "de":
                display_tasks(f"task due.before:today +PENDING export", show_details=True)
                prompt("\n\n\nPress enter when you finished analysing!")

            elif choice.lower() == "td":
                task_id = console.input("Enter the task ID to mark as completed: ")
                command = f"task {task_id} done"
                execute_task_command(command)
            elif choice.lower() == "r":
                console.clear()
            elif choice.lower() == "sp":
                console.print(
                    Panel("Progress saved. Exiting review.", style="bold green")
                )
                return  # Exit the review process
            elif choice == "":
                break  # Exit the overdue tasks review
            else:
                console.print(
                    Panel("Invalid choice. Please try again.", style="bold red")
                )

        console.print(
            Panel(
                "Review complete. All projects, tasks without a project, and overdue tasks have been processed.",
                style="bold green",
            )
        )

    def has_pending_tasks(project):
        """Check if a project has pending tasks using Taskwarrior.
        
        Args:
            project (str): The project name to check
            
        Returns:
            bool: True if there are pending tasks, False otherwise
        """
        try:
            # Use Taskwarrior to get pending tasks for the project
            command = f"task project:{project} project.not:{project}. status:pending count"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            # Check if the command executed successfully
            if result.returncode != 0:
                print(f"Warning: Taskwarrior command failed with return code {result.returncode}")
                if result.stderr:
                    print(f"Error output: {result.stderr.strip()}")
                return False
            
            # Get the output and handle empty/invalid responses
            output = result.stdout.strip()
            
            if not output:
                # Empty output means no tasks found
                return False
            
            # Try to convert to integer
            try:
                count = int(output)
                return count > 0
            except ValueError:
                print(f"Warning: Could not parse task count from output: '{output}'")
                return False
                
        except Exception as e:
            print(f"Error checking pending tasks for project '{project}': {e}")
            return False

    def search_project2(project_list):
        completer = FuzzyWordCompleter(project_list)
        item_name = prompt("Enter a project name: ", completer=completer)
        closest_match, match_score = process.extractOne(item_name, project_list)

        # You can adjust the threshold based on how strict you want the matching to be
        MATCH_THRESHOLD = 100  # For example, 80 out of 100

        if match_score >= MATCH_THRESHOLD:
            return closest_match
        else:
            return item_name  # Use the new name entered by the user

    def display_task_details(task_uuid):
        """Display a task's details in a Rich-styled tree structure with time deltas for dates."""
        console = Console()

        # Retrieve the task details from Taskwarrior
        command = f"task {task_uuid} export"
        output = run_taskwarrior_command(command)

        if not output:
            console.print("[red]Failed to retrieve task details.[/red]")
            return

        task_details = json.loads(output)
        if not task_details:
            console.print("[red]No task details found.[/red]")
            return

        task = task_details[0]
        
        # Create the main tree
        main_tree = Tree(
            Text(f"Task {task_uuid}", style="bold cyan"),
            guide_style="cyan"
        )

        # Helper function to format date values with delta time
        def format_date_with_delta(date_str, date_type):
            from datetime import datetime
            import dateutil.parser
            
            # Make sure we're using timezone-aware datetime objects
            date_obj = dateutil.parser.parse(date_str)
            
            # If the date is timezone-aware, make sure now is also timezone-aware
            if date_obj.tzinfo is not None:
                from datetime import timezone
                now = datetime.now(timezone.utc)
            else:
                now = datetime.now()
            
            # Calculate delta
            delta = date_obj - now if date_type in ["due", "scheduled", "until"] else now - date_obj
            
            # Format delta in a human-readable way
            if abs(delta.days) > 365:
                years = abs(delta.days) // 365
                delta_str = f"{years} year{'s' if years != 1 else ''}"
            elif abs(delta.days) > 30:
                months = abs(delta.days) // 30
                delta_str = f"{months} month{'s' if months != 1 else ''}"
            elif abs(delta.days) > 0:
                delta_str = f"{abs(delta.days)} day{'s' if abs(delta.days) != 1 else ''}"
            elif abs(delta.seconds) >= 3600:
                hours = abs(delta.seconds) // 3600
                delta_str = f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                minutes = (abs(delta.seconds) // 60) or 1  # At least 1 minute
                delta_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
            
            # Different prefix depending on if it's in the past or future
            if date_type in ["due", "scheduled", "until"]:
                if delta.total_seconds() > 0:
                    prefix = "in"  # Future
                else:
                    prefix = "overdue by"  # Past
            else:
                if delta.total_seconds() > 0:
                    prefix = "ago"  # Past
                else:
                    prefix = "in"  # Future (shouldn't happen for entry/modified)
                    
            return f"{date_str} ({prefix} {delta_str})"

        # Helper function to format values appropriately
        def format_value(field, value):
            if isinstance(value, bool):
                return "✓" if value else "✗"
            elif isinstance(value, (int, float)):
                return str(value)
            elif isinstance(value, dict):
                return "nested dictionary"  # Placeholder for nested structures
            elif isinstance(value, list):
                return ", ".join(map(str, value))
            elif value is None:
                return "—"
            elif field in ["entry", "modified", "due", "scheduled", "until"]:
                try:
                    return format_date_with_delta(str(value), field)
                except (ValueError, TypeError) as e:
                    return f"{value} (error calculating delta: {str(e)})"
            return str(value)

        # Group related fields
        field_groups = {
            "Basic Information": ["description", "status", "project", "priority"],
            "Dates": ["entry", "modified", "due", "scheduled", "until"],
            "Tags and Dependencies": ["tags", "depends"],
            "Task Status": ["waiting", "recur", "parent"],
            "Metadata": ["uuid", "urgency", "id"]
        }

        # Create branches for each group
        for group_name, fields in field_groups.items():
            # Only create group if at least one field exists
            existing_fields = [f for f in fields if f in task]
            if existing_fields:
                group_branch = main_tree.add(Text(group_name, style="bold yellow"))
                
                for field in existing_fields:
                    value = format_value(field, task[field])
                    # Style based on field type
                    if field in ["due", "scheduled"] and task.get(field):
                        style = "red" if field == "due" else "green"
                    elif field == "priority":
                        style = {"H": "red", "M": "yellow", "L": "blue"}.get(str(task[field]), "white")
                    else:
                        style = "white"
                    
                    field_text = Text(f"{field}: ", style="blue")
                    field_text.append(value, style=style)
                    group_branch.add(field_text)

        # Add remaining fields that weren't in any group
        all_grouped_fields = [f for fields in field_groups.values() for f in fields]
        remaining_fields = [f for f in task.keys() if f not in all_grouped_fields]
        
        if remaining_fields:
            other_branch = main_tree.add(Text("Other Fields", style="bold yellow"))
            for field in remaining_fields:
                value = format_value(field, task[field])
                field_text = Text(f"{field}: ", style="blue")
                field_text.append(value, style="white")
                other_branch.add(field_text)

        # Print the tree
        console.print(main_tree)
        
    def add_new_task_to_project(project_name):
        while True:
            new_task_description = input(
                "Enter the description for the new task (or press Enter to stop adding tasks): "
            )
            if new_task_description.lower() in ["exit", ""]:
                break

            if new_task_description:
                command = f"task add {new_task_description} project:{project_name} -in"
                run_taskwarrior_command(command)
                print(Fore.GREEN + "New task added to the project.")

    def process_task(task):
        print(Fore.YELLOW + f"\nProcessing task: {task['description']}")
        display_task_details(task["uuid"])
        action = (
            input("Choose action: modify (mod) /skip (s) /delete (del) /done (d)):\n ")
            .strip()
            .lower()
        )

        if action == "mod":
            print(Fore.YELLOW + "Task details:")
        
            mod_confirm = (
                input("Do you want to modify this task? (yes/no):\n ").strip().lower()
            )
            if mod_confirm in ["yes", "y"]:
                modification = input(
                    "Enter modification (e.g., '+tag @context priority'):\n "
                )
                run_taskwarrior_command(
                    f"task {task['uuid']} modify {modification} -in"
                )

            pro_confirm = (
                input("Do you want to assign this task to a project? (yes/no):\n ")
                .strip()
                .lower()
            )
            if pro_confirm in ["yes", "y"]:
                project_list = call_and_process_task_projects2()
                selected_project = search_project2(project_list)
                run_taskwarrior_command(
                    f"task {task['uuid']} modify project:{selected_project} -in"
                )
                print(
                    Fore.GREEN + f"Task categorized under project: {selected_project}\n"
                )

                # Ask if user wants to add another task to the same project
                add_another = (
                    input("Do you want to add another task to this project? (yes/no): ")
                    .strip()
                    .lower()
                )
                if add_another in ["yes", "y"]:
                    add_new_task_to_project(selected_project)
        elif action == "skip":
            print(Fore.BLUE + "Skipping task.")
        elif action == "del":
            run_taskwarrior_command(f"task {task['uuid']} delete -y")
            print(Fore.RED + f"Deleted task {task['uuid']}")
        elif action == "d":
            run_taskwarrior_command(f"task {task['uuid']} done")
            print(Fore.GREEN + f"Marked = {task['uuid']} = as done.")

            # =========================================================

    def parse_datetime(due_date_str):
        try:
            return (
                datetime.strptime(due_date_str, "%Y%m%dT%H%M%SZ")
                if due_date_str
                else None
            )
        except ValueError:
            return None

    def parse_iso_duration(duration_str):
        """Convert ISO-8601 duration string to hours"""
        if not duration_str:
            return 0

        try:
            # Remove PT prefix
            duration = duration_str.replace("PT", "")
            hours = 0.0

            # Handle hours
            if "H" in duration:
                h_split = duration.split("H")
                hours += float(h_split[0])
                duration = h_split[1]

            # Handle minutes
            if "M" in duration:
                m_split = duration.split("M")
                hours += float(m_split[0]) / 60

            return hours
        except (ValueError, AttributeError):
            return 0

    def format_metrics_text(metrics):
        """Format metrics into aligned columns"""
        return (
            f"Tasks: {metrics['task_count']:,d} | "
            f"Value: {metrics['total_value']:,.0f} (avg: {metrics['avg_value']:,.0f}) | "
            f"Hours: {metrics['total_duration']:.1f}"
        )

    def display_tasks(command, show_details=False, sort_by="alpha"):
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        console = Console()

        if not result.stdout:
            console.print("No tasks found.", style="bold red")
            return

        tasks = json.loads(result.stdout)
        if not tasks:
            console.print("No tasks found.", style="bold red")
            return

        project_metadata = load_project_metadata(file_path)
        project_tag_map = defaultdict(lambda: defaultdict(list))
        project_values = defaultdict(list)
        project_durations = defaultdict(list)
        tag_values = defaultdict(lambda: defaultdict(float))  # Nested defaultdict for project-tag values
        project_tag_totals = defaultdict(float)  # New: Total value per project
        now = datetime.now(timezone.utc).astimezone()

        for task in tasks:
            project = task.get("project", "No Project")
            tags = task.get("tags", ["No Tag"])
            description = task["description"]
            task_id = str(task["id"])

            # Entry / creation date
            created_date = None
            delta_created_str = ""
            if "entry" in task:
                try:
                    created_date = datetime.strptime(task["entry"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                    delta_created = now - created_date
                    delta_created_str = f"{delta_created.days}d {delta_created.seconds // 3600}h"
                except ValueError:
                    created_date = task["entry"]

            # Due date processing
            due_date_str = task.get("due")
            due_date = parse_datetime(due_date_str) if due_date_str else None

            # Duration processing
            duration = task.get("duration", "")
            duration_hours = parse_iso_duration(duration)
            project_durations[project].append(duration_hours)

            # Value processing
            value = task.get("value")
            try:
                value = float(value) if value is not None else 0
                project_values[project].append(value)
            except ValueError:
                value = 0

            # Accumulate the value for each tag under the project
            for tag in tags:
                tag_values[project][tag] += value  # Update project-specific tag value

            # Priority level determination (only from the task's priority field)
            priority_level = task.get("priority")
            priority_color = {
                "H": "bold red",
                "M": "bold yellow",
                "L": "dim green",
            }.get(priority_level, "bold magenta") if priority_level else None

            # Due date color and text
            due_color = "default_color"
            delta_text = ""
            if due_date:
                delta = due_date - now
                if delta.total_seconds() < 0:
                    due_color = "red"
                elif delta.days >= 365:
                    due_color = "steel_blue"
                elif delta.days >= 90:
                    due_color = "light_slate_blue"
                elif delta.days >= 30:
                    due_color = "green_yellow"
                elif delta.days >= 7:
                    due_color = "thistle3"
                elif delta.days >= 3:
                    due_color = "yellow1"
                elif delta.days == 0:
                    due_color = "bold turquoise2"
                else:
                    due_color = "bold orange1"
                delta_text = format_timedelta(delta)

            # Map tasks to projects and tags
            for tag in tags:
                project_tag_map[project][tag].append(
                    (
                        task_id,
                        description,
                        due_date,
                        task.get("annotations", []),
                        delta_text,
                        due_color,
                        duration,
                        priority_level,
                        priority_color,
                        value,
                        created_date,
                        delta_created_str,
                    )
                )

        # Calculate recursive project totals including sub-projects
        def calculate_recursive_project_totals():
            """Calculate total values for each project including all sub-projects"""
            recursive_totals = {}
            
            def get_project_recursive_total(project_name):
                if project_name in recursive_totals:
                    return recursive_totals[project_name]
                
                # Start with direct project value
                direct_value = sum(project_values[project_name])
                total_value = direct_value
                
                # Add values from all sub-projects
                for other_project in project_values:
                    if other_project.startswith(project_name + "."):
                        sub_value = get_project_recursive_total(other_project)
                        total_value += sub_value
                
                recursive_totals[project_name] = total_value
                return total_value
            
            # Calculate for all projects
            for project in project_values:
                get_project_recursive_total(project)
            
            return recursive_totals
        
        project_recursive_totals = calculate_recursive_project_totals()

        def get_project_totals(project_name):
            total_value = sum(project_values[project_name])
            total_duration = sum(project_durations[project_name])
            task_count = len(project_values[project_name])
            for other_project in project_values:
                if other_project.startswith(project_name + "."):
                    sub_value, sub_duration, sub_count = get_project_totals(other_project)
                    total_value += sub_value
                    total_duration += sub_duration
                    task_count += sub_count
            return total_value, total_duration, task_count

        def create_task_details(task_info):
            (
                task_id,
                description,
                due_date,
                annotations,
                delta_text,
                due_color,
                duration,
                priority_level,
                priority_color,
                value,
                created_date,
                delta_created_str,
            ) = task_info

            details = []
            if priority_level:
                details.append(Text(f" [{priority_level}]", style=priority_color))
            if value:
                details.append(Text(f" ♦️ {value}", style="green"))
            if duration:
                details.append(Text(f" ⏳ {duration}", style="magenta"))
            if due_date:
                formatted_due = due_date.strftime("%Y-%m-%d")
                details.append(Text(f" 📅 {formatted_due} ({delta_text})", style=due_color))
            if created_date:
                created_str = (
                    created_date.strftime("%Y-%m-%d %H:%M:%S")
                    if isinstance(created_date, datetime)
                    else str(created_date)
                )
                details.append(Text(f" 🕒{delta_created_str}", style="blue"))

            # Add annotations
            if annotations:
                details.append(Text("\n📝", style="cyan bold"))
                for annotation in annotations:
                    entry_datetime = datetime.strptime(annotation["entry"], "%Y%m%dT%H%M%SZ").strftime("%Y-%m-%d %H:%M:%S")
                    entry_text = Text(f"\n  • {entry_datetime} - ", style="yellow")
                    description_text = Text(annotation["description"], style="white")
                    details.append(entry_text + description_text)

            return Text("").join(details)

        tree = Tree("Task Overview", style="blue", guide_style="grey50")
        
        # Sort projects based on sort_by parameter
        if sort_by.lower() == "value":
            sorted_projects = sorted(project_tag_map.items(), key=lambda x: project_recursive_totals.get(x[0], 0), reverse=True)
        else:  # default to alpha
            sorted_projects = sorted(project_tag_map.items())
        
        for project, tags in sorted_projects:
            if project == "No Project" and not any(tags.values()):
                continue

            project_levels = project.split(".")
            current_branch = tree
            current_path = []

            for i, level in enumerate(project_levels):
                current_path.append(level)
                current_project = ".".join(current_path)
                if show_details:
                    total_value, total_duration, task_count = get_project_totals(current_project)
                    metrics_summary = f"[grey70]({task_count} tasks"
                    if total_value > 0:
                        metrics_summary += f" | ♦️ {total_value:,.0f}"
                    if total_duration > 0:
                        metrics_summary += f" | {total_duration:.1f}h"
                    metrics_summary += ")[/grey70]"
                    branch_label = f"[cyan1]{level}[/cyan1] {metrics_summary}"
                else:
                    # Show project recursive total value even without details
                    project_total_value = project_recursive_totals.get(current_project, 0)
                    if project_total_value > 0:
                        branch_label = f"[cyan1]{level}[/cyan1] [green](♦️ {project_total_value:,.0f})[/green]"
                    else:
                        branch_label = f"[cyan1]{level}[/cyan1]"

                found_branch = next(
                    (child for child in current_branch.children if child.label.plain.startswith(level)),
                    None,
                )
                if not found_branch:
                    found_branch = current_branch.add(Text.from_markup(branch_label), guide_style="grey50")
                current_branch = found_branch

            metadata = None
            project_hierarchy = project.split(".")
            for j in range(len(project_hierarchy), 0, -1):
                partial_project = ".".join(project_hierarchy[:j])
                metadata = project_metadata.get(partial_project)
                if metadata and any(metadata.values()):
                    break
            if metadata:
                add_project_metadata_to_tree_2(metadata, current_branch)

            # Sort tags based on sort_by parameter
            if sort_by.lower() == "value":
                sorted_tags = sorted(tags.items(), key=lambda x: tag_values[project][x[0]], reverse=True)
            else:  # default to alpha
                sorted_tags = sorted(tags.items())

            for tag, task_list in sorted_tags:
                if not task_list:
                    continue

                # Get the project-specific tag value
                tag_value = tag_values[project][tag]
                tag_label = f"[yellow]🏷️  {tag}[/yellow] [green](♦️ {tag_value:,.0f})[/green]" if tag_value > 0 else tag
                tag_branch = current_branch.add(Text.from_markup(tag_label), guide_style="yellow")

                # Sort tasks based on sort_by parameter
                if sort_by.lower() == "value":
                    sorted_tasks = sorted(task_list, key=lambda x: (x[9] == 0, -x[9]))  # Sort by value (index 9), 0 values last
                else:  # default to alpha (by due date as before)
                    sorted_tasks = sorted(task_list, key=lambda x: (x[2] is None, x[2]))

                for task_info in sorted_tasks:
                    task_id, description, due_date, *_ = task_info
                    task_line = f"[red][[/red][medium_spring_green]{task_id}[/medium_spring_green][red]][/red] [white bold]{description}[/white bold]"
                    if due_date:
                        delta = due_date - now
                        total_seconds = delta.total_seconds()
                        
                        if total_seconds < 0:
                            # Task is overdue
                            overdue_hours = abs(total_seconds) / 3600
                            if overdue_hours < 24:
                                task_line += f" [yellow]{overdue_hours:.1f}h ⚠️[/yellow]"
                            else:
                                overdue_days = abs(delta.days)
                                task_line += f" [red]{overdue_days}d ⚠️[/red]"
                        elif total_seconds < 86400:  # Less than 24 hours
                            hours_left = total_seconds / 3600
                            if hours_left < 1:
                                minutes_left = total_seconds / 60
                                task_line += f" [red]({minutes_left:.0f}m left)[/red]"
                            else:
                                task_line += f" [green]{hours_left:.1f}h 🕐[/green]"
                        elif delta.days == 0:
                            task_line += " [green](Due today)[/green]"
                        elif delta.days > 0:
                            task_line += f" [turquoise2]{delta.days}d 🕐[/turquoise2]"

                    task_branch = tag_branch.add(Text.from_markup(task_line))
                    if show_details:
                        details_text = create_task_details(task_info)
                        task_branch.add(details_text, guide_style="grey50")

        console.print(tree)


    def parse_datetime(date_string):
        # Parse the UTC datetime
        utc_time = datetime.strptime(date_string, "%Y%m%dT%H%M%SZ")
        utc_time = utc_time.replace(tzinfo=timezone.utc)
        # Convert to local time
        local_time = utc_time.astimezone(local_tz)
        return local_time

    def format_timedelta(delta):
        is_overdue = delta.total_seconds() < 0
        if is_overdue:
            delta = abs(delta)  # Make delta positive for overdue tasks

        total_seconds = int(delta.total_seconds())
        years, remainder = divmod(total_seconds, 31536000)  # 365 days
        months, remainder = divmod(remainder, 2592000)  # 30 days
        weeks, remainder = divmod(remainder, 604800)  # 7 days
        days, remainder = divmod(remainder, 86400)  # 1 day
        hours, _ = divmod(remainder, 3600)  # 1 hour

        parts = []
        if years > 0:
            parts.append(f"{years} year{'s' if years != 1 else ''}")
        if months > 0:
            parts.append(f"{months} month{'s' if months != 1 else ''}")
        if weeks > 0:
            parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0 or (years == 0 and months == 0 and weeks == 0 and days == 0):
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")

        detailed_str = " ".join(parts)

        if is_overdue:
            if delta.days == 0:
                if hours == 0:
                    return "Due NOW!"
                else:
                    return f"Overdue by {hours} hour{'s' if hours != 1 else ''}"
            else:
                return (
                    f"Overdue by {delta.days} day{'s' if delta.days != 1 else ''}"
                    + (f" ~ {detailed_str}" if len(parts) > 1 else "")
                )
        else:
            if delta.days == 0:
                if hours == 0:
                    return "Due NOW!"
                else:
                    return f"Due in {hours} hour{'s' if hours != 1 else ''}"
            else:
                return f"Due in {delta.days} day{'s' if delta.days != 1 else ''}" + (
                    f" ~ {detailed_str}" if len(parts) > 1 else ""
                )

    def display_menu(console):
        # console = Console()
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("Key", style="dim", width=2)
        table.add_column("Action", min_width=20)
        table.add_row("d", "Today's Tasks")
        table.add_row("y", "Yesterday's Tasks")
        table.add_row("t", "Tomorrow's Tasks")
        table.add_row("w", "Current Week's Tasks")
        table.add_row("m", "Current Month's Tasks")
        table.add_row("l", "View Long-Term Plan")
        table.add_row("o", "Overdue Tasks")
        table.add_row("i", "Inbox Tasks")
        table.add_row("h", "Handle Tasks")
        table.add_row("b", "Back to main")
        table.add_row("Enter", "Exit")

        console.print(table)

    def task_control_center(choice=None):
        console = Console()
        scope_command_map = {
            "d": "task due:today +PENDING export",
            "y": "task due:yesterday +PENDING export",
            "t": "task due:tomorrow status:pending export",
            "w": "task +WEEK +PENDING export",
            "m": "task +MONTH +PENDING export",
            "o": "task due.before:today +PENDING export",
        }

        if choice is None:
            while True:
                console.print(
                    "[bold cyan]Task Control Center[/bold cyan]", justify="center"
                )
                display_menu(console)
                choice = Prompt.ask("[bold yellow]Enter your choice[/bold yellow]")

                if choice == "":
                    # console.clear()
                    break

                process_choice(choice, console, scope_command_map)
        else:
            process_choice(choice, console, scope_command_map)

    def process_choice(choice, console, scope_command_map):
        if choice in scope_command_map:
            # console.clear()
            display_tasks(scope_command_map[choice])
        elif choice == "l":
            # console.clear()
            display_due_tasks()
        elif choice == "i":
            # console.clear()
            display_inbox_tasks()
        elif choice == "h":
            handle_task()
        elif choice == "b":
            main_menu()
        else:
            console.print("Invalid choice. Please try again.", style="bold red")

    # ------------------------------------------------------------------------------------
    # Inbox Processing - GTD Style

    def greeting_pi():
        action = questionary.select(
            "What would you like to do?",
            choices=["Process inbox tasks", "Do a mind dump", "Both", "Exit"],
        ).ask()

        if action == "Do a mind dump" or action == "Both":
            lines = gtd_prompt()
            if lines:
                print("Adding the tasks to TaskWarrior database...")
                uuids = [add_task_to_taskwarrior(line) for line in lines]
                for uuid in uuids:
                    process_gtd(uuid)
            console.print("Mind dump completed.", style="bold green")

        if action == "Process inbox tasks" or action == "Both":
            process_inbox_tasks()
            console.print("Inbox tasks have been processed.", style="bold green")

        if action == "Exit":
            console.print("Goodbye!", style="bold blue")
            return

        console.print(
            "All selected tasks have been processed and stored in the database.",
            style="bold blue",
        )

    def gtd_prompt():
        console.print(Panel("Mind Dump (GTD Style)", style="bold magenta"))
        console.print(
            "Enter everything on your mind, line by line. When you're done, add empty line.",
            style="cyan",
        )
        lines = []
        while True:
            line = Prompt.ask("> ")
            if line.strip().lower() == "":
                break
            if line:
                lines.append(line)
        return lines

    def add_task_to_taskwarrior(description):
        tw = TaskWarrior()
        task = Task(tw, description=description, tags=["dump"])
        task.save()
        return task["uuid"]



    def search_project3(project_list):
        if callable(project_list):
            project_list = (
                project_list()
            )  # Ensure project_list is a list if it's a callable function

        if not project_list:
            print("No projects available.")
            return None, None  # Return None if project list is empty or invalid

        completer = FuzzyCompleter(WordCompleter(project_list, ignore_case=True))
        item_name = prompt("Enter a project name: ", completer=completer)
        closest_match, match_score = process.extractOne(item_name, project_list)

        MATCH_THRESHOLD = 100  # Adjust the threshold based on your preference

        if match_score >= MATCH_THRESHOLD:
            return closest_match
        else:
            return item_name  # Use the new name entered by the user if no close match found

    def add_task_to_project2(project_name):
        task_description = questionary.text(
            "Enter the description for the new task:"
        ).ask()

        create_command = f"task add proj:'{project_name}' {task_description}"
        execute_task_command(create_command)

        task_id = get_latest_task_id()
        if task_id:
            has_dependencies = questionary.confirm(
                "Does this task have dependencies?"
            ).ask()
            if has_dependencies:
                add_dependent_tasks(task_description, project_name, task_id)
        else:
            print("Failed to retrieve the task ID.")



    def modify_dependent_tasks(task_id, dependent_task_ids):
        tw = TaskWarrior()
        for dep_id in dependent_task_ids.split(","):
            try:
                dep_task = tw.tasks.get(id=dep_id)
                modify_command = f"task {task_id} modify depends:{dep_id}"
                execute_task_command(modify_command)
                print(f"Task {task_id} now depends on task {dep_id}.")
            except Task.DoesNotExist:
                print(f"Task with ID {dep_id} does not exist. Skipping.")

    def add_dependent_tasks(task_description, project_name, task_id):
        print("\nMain Task Description:")
        print(task_description)
        print("\nHelpful Questions:")
        print("What needs to happen for this to be possible?")
        print("What are the sub-tasks?")
        print("What are the consequences?\n")

        print("Enter each sub-task on a new line. Type 'done' when you are finished.\n")

        sub_tasks = []
        while True:
            sub_task = input("> ").strip()
            if sub_task.lower() == "done":
                break
            if sub_task:
                sub_tasks.append(sub_task)

        print("\nMain Task Description:")
        print(task_description)
        print("Sub-tasks entered:")

        sub_task_ids = []
        for sub_task in sub_tasks:
            print(f"- {sub_task}")
            create_command = f"task add proj:'{project_name}' {sub_task}"
            execute_task_command(create_command)
            sub_task_id = get_latest_task_id()
            if sub_task_id:
                sub_task_ids.append(sub_task_id)  # collect task IDs as strings
                print(f"  ID: {sub_task_id}")
            else:
                print("Failed to retrieve sub-task ID. Skipping.")

        if sub_task_ids:  # ensure we have valid IDs before proceeding
            action = questionary.select(
                "How would you like to handle these sub-tasks?",
                choices=[
                    "1. Add them as sub-tasks of the main task",
                    "2. Manual sort dependencies",
                ],
            ).ask()

            if action.startswith("1"):
                modify_dependent_tasks(
                    task_id, ",".join(map(str, sub_task_ids))
                )  # Convert IDs to strings
            elif action.startswith("2"):
                manual_sort_dependencies(sub_task_ids)
            else:
                print("No valid sub-tasks were added for processing.")



    def set_task_dependencies(dependency_input):
        chains = dependency_input.split(",")
        for chain in chains:
            tasks = chain.split(">")
            # Reverse to set up each as blocking the previous
            tasks.reverse()
            for i in range(len(tasks) - 1):
                dependent_id = tasks[i].strip()
                task_id = tasks[i + 1].strip()
                modify_command = f"task {task_id} modify depends:{dependent_id}"
                execute_task_command(modify_command)
                print(f"Task {dependent_id} now depends on task {task_id}.")

    # Constants
    TAG_DUMP = "dump"
    TAG_IN = "in"
    TAG_SOMEDAY = "someday"
    TAG_REFERENCE = "unsorted"
    TAG_NEXT = "next"
    PROJECT_MAYBE = "Maybe"
    PROJECT_RESOURCES = "Resources.References"
    PROJECT_WAITING_FOR = "WaitingFor"

    # Action Categories Enum for readability
    class ActionCategory(Enum):
        DELETE = "1"
        SOMEDAY = "2"
        REFERENCE = "3"
        COMPLETED = "4"

    def update_task_tags(task, add_tags, remove_tags):
        # Use set operations to optimize tag updates
        task["tags"].update(add_tags)
        task["tags"].difference_update(remove_tags)

    def ask_task_description(task):
        """Helper function to ask for task description."""
        task["description"] = Prompt.ask("Please provide a better description")
        task.save()

    def set_task_due_date(task):
        """Helper function to set due date."""
        due_date = console.input("Enter the due date: ")
        task["due"] = due_date
        task.save()

    def ask_project_selection(task):
        """Helper function for project selection."""
        project_list = call_and_process_task_projects2()
        project = search_project3(project_list)
        task["project"] = project
        update_task_tags(task, [], [TAG_IN, TAG_DUMP])
        return project

    def process_gtd(uuid):
        tw = TaskWarrior()
        task = tw.tasks.get(uuid=uuid)
        task["tags"].discard(TAG_DUMP)
        console.print(
            Panel(
                f"Processing: {task['description']} uuid:{short_uuid(task['uuid'])}",
                style="bold green",
            )
        )

        if Confirm.ask("Do you want to elaborate on this or proceed?", default=False):
            ask_task_description(task)

        if not Confirm.ask("Is this actionable?", default=False):
            process_non_actionable(task)
        else:
            process_actionable(task)


    # Optional: let the caller pass explicit paths; otherwise read from env or use fallback.
    DEFAULT_MD_PATHS: List[str] = [
    "/home/pooK/.sku/DB/Obsidian/Arcadia/03.Resources/gtd_referrences.md","/storage/emulated/0/Documents/.sku/DB/Obsidian/Arcadia/03.Resources/gtd_referrences.md"

    ]

    class ActionCategory:
        DELETE = "1"
        MARKDOWN = "2"
        COMPLETED = "3"

    def _choose_md_header(headers: List[str]) -> str:
        """
        Presents a questionary.select to choose an existing '##' header
        or create a new one. Returns the chosen/new header text (stripped).
        """
        NEW_HDR = "<Create new header…>"

        # No headers → force creation
        if not headers:
            console.print("No '##' headers found; please create one.", style="yellow")
            hdr = questionary.text("New header name (text after `## `):").ask()
            return (hdr or "").strip()

        # Make unique and stable
        seen = []
        for h in headers:
            if h not in seen:
                seen.append(h)

        choice = questionary.select(
            "Pick a '##' section (or create a new one):",
            choices=seen + [NEW_HDR],
            qmark="→",
            pointer="›",
            use_shortcuts=True,
        ).ask()

        if choice == NEW_HDR:
            hdr = questionary.text("New header name (text after `## `):").ask()
            return (hdr or "").strip()

        return (choice or "").strip()

    def _mark_done_if_needed(task) -> bool:
        status = str(_tw_get(task, "status", "")).lower()
        if status in ("completed", "deleted"):
            return False
        try:
            task.done()
            task.save()
            return True
        except Exception:
            return False


    def process_non_actionable(task, md_paths: Optional[List[str]] = None):
        console.print("Choose a category for this item:", style="yellow")
        choice = Prompt.ask(
            "1. Forget (delete)\n2. Add to markdown file\n3. Mark as completed",
            choices=[ActionCategory.DELETE, ActionCategory.MARKDOWN, ActionCategory.COMPLETED],
            default=ActionCategory.COMPLETED,
        )

        if choice == ActionCategory.DELETE:
            task.delete()
            # No task.save() after delete
            return  # ← ensure we don't fall through

        if choice == ActionCategory.MARKDOWN:
            candidates = _resolve_markdown_paths(md_paths)
            md_path = _first_existing(candidates)
            if not md_path:
                from rich.markup import escape
                console.print(
                    Panel(
                        f"Markdown file not found. Checked:\n" +
                        "\n".join(f"  - {escape(c)}" for c in (candidates or ["<none>"])),
                        title="Error",
                        style="bold red",
                    )
                )
                return

            headers = _read_markdown_h2_headers(md_path)
            selected_header = _choose_md_header(headers)
            if not selected_header:
                console.print("No header provided. Aborting.", style="bold red")
                return

            _ensure_h2_header_exists(md_path, selected_header)

            entry_time = _format_entry_time(task)
            description = str(_tw_get(task, "description", "")).strip()
            checklist_line = f"- [ ] {entry_time} {description}"

            if not _append_line_under_h2(md_path, selected_header, checklist_line):
                _ensure_h2_header_exists(md_path, selected_header)
                _append_line_under_h2(md_path, selected_header, checklist_line)

            _mark_done_if_needed(task)

            from rich.markup import escape
            safe_path = escape(str(md_path))
            safe_header = escape(str(selected_header))
            msg = Text(f"Filed to [{md_path}] → ## {selected_header}\nMarked task done.")
            console.print(Panel(msg, style="bold green"))
            return  # ← ensure we don't fall through

        # Option 3: Mark as completed (default)
        _mark_done_if_needed(task)
        return



    # ----------------- Helpers -----------------

    def _resolve_markdown_paths(md_paths: Optional[List[str]]) -> List[str]:
        """
        Priority:
        1) Explicit md_paths param
        2) GTD_MD_PATHS env var (colon-separated)
        3) DEFAULT_MD_PATHS constant
        """
        if md_paths:
            return md_paths
        env_val = os.environ.get("GTD_MD_PATHS", "").strip()
        if env_val:
            return [p for p in env_val.split(":") if p.strip()]
        return DEFAULT_MD_PATHS

    def _first_existing(paths: List[str]) -> Optional[Path]:
        for p in paths or []:
            path = Path(p).expanduser()
            if path.is_file():
                return path
        return None

    _H2_REGEX = re.compile(r"(?m)^\s*##\s+(.*\S)\s*$")

    def _read_markdown_h2_headers(md_path: Path) -> List[str]:
        text = md_path.read_text(encoding="utf-8")
        return [m.group(1).strip() for m in _H2_REGEX.finditer(text)]

    def _ensure_h2_header_exists(md_path: Path, header_text: str) -> None:
        """
        Appends a new '## {header_text}' at EOF if it doesn't exist already.
        Ensures a clean separation with a blank line above if needed.
        """
        text = md_path.read_text(encoding="utf-8")
        if not any(h.strip() == header_text for h in _H2_REGEX.findall(text)):
            # Ensure ending newline(s)
            append = ""
            if not text.endswith("\n"):
                append += "\n"
            # Add an extra blank line for readability, then the new header and a trailing newline
            append += f"\n## {header_text}\n\n"
            md_path.write_text(text + append, encoding="utf-8")

    def _append_line_under_h2(md_path: Path, header_text: str, line: str) -> bool:
        """
        Inserts `line` just before the next '##' or at the end of file, within the
        section starting at '## header_text'. Returns True if inserted; False if header not found.
        """
        text = md_path.read_text(encoding="utf-8")

        # Find the target header start
        start_match = None
        for m in _H2_REGEX.finditer(text):
            if m.group(1).strip() == header_text:
                start_match = m
                break
        if not start_match:
            return False

        # Find where the section ends (next H2 or EOF)
        section_start_idx = start_match.end()  # right after the header line
        next_match = _H2_REGEX.search(text, pos=section_start_idx)
        section_end_idx = next_match.start() if next_match else len(text)

        # Extract parts
        before = text[:section_start_idx]
        section = text[section_start_idx:section_end_idx]
        after = text[section_end_idx:]

        # Ensure section ends with exactly one newline before appending
        if not section.endswith("\n"):
            section += "\n"
        section += line.strip() + "\n"

        new_text = before + section + after
        md_path.write_text(new_text, encoding="utf-8")
        return True

    def _tw_get(task, key, default=None):
        """
        Safe getter for Taskwarrior Task objects that don't implement .get().
        Tries mapping-style access, then attribute access, then returns default.
        """
        try:
            return task[key]  # preferred for TaskWarrior Task
        except KeyError:
            return default
        except Exception:
            return getattr(task, key, default)


    def _format_entry_time(task) -> str:
        """
        Uses task['entry'] if present; otherwise local now.
        Formats as YYYY-MM-DD HH:MM (local).
        """
        raw = _tw_get(task, "entry")
        from datetime import datetime  # if not already imported

        if raw:
            try:
                # Typical TW format: 20250821T122043Z
                if isinstance(raw, str) and raw.endswith("Z") and "T" in raw and len(raw) >= 16:
                    dt = datetime.strptime(raw, "%Y%m%dT%H%M%SZ")
                    return dt.astimezone().strftime("%Y-%m-%d %H:%M")
                # ISO fallback
                try:
                    dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                except ValueError:
                    dt = datetime.fromisoformat(str(raw))
                return dt.astimezone().strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

        return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")


    def process_actionable(task):
        if Confirm.ask(
            "Is this a single-step task (Y) / part of a project (N)?", default=False
        ):
            process_single_step(task)
        else:
            process_project_task(task)

    def process_single_step(task):
        if Confirm.ask("Is this a 2 minute task?", default=False):
            if Confirm.ask("Do you want to do it now?", default=False):
                task.done()
                return

        if not Confirm.ask("For me?", default=False):
            to_whom = Prompt.ask("To whom?")
            update_task_tags(task, [to_whom], [TAG_IN, TAG_DUMP])
            task["project"] = PROJECT_WAITING_FOR
            follow_up_date = Prompt.ask("When should you follow up? (YYYY-MM-DD)")
            task["due"] = follow_up_date
        else:
            due_date = Prompt.ask("Assign due date (YYYY-MM-DD or leave blank)")
            update_task_tags(task, [TAG_NEXT], [TAG_IN, TAG_DUMP])
            if due_date:
                task["due"] = due_date

        task.save()

    def process_project_task(task):
        if Confirm.ask("See a basic project list before selecting?", default=False):
            basic_summary()

        project = ask_project_selection(task)

        if Confirm.ask("Do you want to set a due date to task?", default=False):
            set_task_due_date(task)

        console.print("Choose a category for this item:", style="yellow")
        choice = Prompt.ask(
            "1. Add dependent tasks\n2. Set dependency\nEnter.Continue\nEnter the number of your choice",
            choices=["1", "2", ""],
        )

        if choice == "1":
            display_tasks(f"task pro:{project} +PENDING export")
            add_dependent_tasks(task["description"], project, task["uuid"])
        elif choice == "2":
            dependency_tree(project)
            manual_sort_dependencies()
        else:
            while Confirm.ask(
                f"Do you want to add another task for project: {project}?",
                default=False,
            ):
                add_task_to_project2(project)
        task.save()

    def process_inbox_tasks():
        tw = TaskWarrior()

        # Process dumped tasks
        dump_tasks = tw.tasks.filter(status="pending", tags=[TAG_DUMP])
        if dump_tasks:
            console.print(Panel("Dumped tasks found.", style="bold yellow"))
            for task in dump_tasks:
                process_gtd(task["uuid"])

        # Process inbox tasks
        inbox_tasks = tw.tasks.filter(status="pending", tags=[TAG_IN])
        if inbox_tasks:
            console.print(
                Panel("Starting processing inbox tasks.", style="bold yellow")
            )
            for task in inbox_tasks:
                process_gtd(task["uuid"])

    # ------------------------------------------------------------------------------------
    # TASK MANAGER


    def task_manager(task_uuid):
        run_task_manager(
            task_uuid,
            get_tasks,
            context_menu,
            dependency_tree,
            call_and_process_task_projects2,
            search_project3,
            display_tasks,
            add_dependent_tasks,
            manual_sort_dependencies,
            remove_task_dependencies,
            handle_task,
            call_and_process_task_projects,
            short_uuid,
        )

    def task_organizer():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        run_task_organizer(
            handle_task,
            next_summary,
            display_overdue_tasks,
            base_dir=base_dir,
        )

    # x_x
    def update_metadata_field(item_name, field_to_update):
        run_update_metadata_field(item_name, field_to_update, file_path)

    # ------------------------------------------------------------------------------------

    def main_menu():
        interactive_prompt(file_path)

    # ==================

    delimiter = "-" * 40
    if __name__ == "__main__":
        main()

    # script_directory = os.path.dirname(os.path.abspath(__file__))
    # file_path = os.path.join(script_directory, "variosdb.json")

    # interactive_prompt(file_path)


except KeyboardInterrupt:
    print(
        "\nYou have to be your own hero.\n\nDo the impossible and you are never going to doubt yourself again!\n\n\nPractice so hard that winning becomes easy."
    )
