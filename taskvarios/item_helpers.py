"""Item/tag metadata helper UI extracted from TaskVarios."""

from datetime import datetime, timedelta

import inquirer
from colorama import Back, Fore
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from taskw import TaskWarrior as Warrior

from taskvarios.storage import save_sultandb


warrior = Warrior()


def get_tags_for_item(item_name, pending_tasks=None):
    if pending_tasks is None:
        pending_tasks = warrior.load_tasks()["pending"]
    tags = {}
    for task in pending_tasks:
        project = task.get("project")
        if project and (
            project == item_name or project.startswith("AoR." + item_name)
        ):
            for tag in task.get("tags", []):
                if not tag.startswith("project:") and tag != item_name:
                    tags[tag] = tags.get(tag, 0) + 1
    return tags


def view_data(item, tags, get_creation_date_fn, get_last_modified_date_fn):
    print(f"{Fore.BLUE}Name: {Fore.YELLOW}{item['name']}{Fore.RESET}")
    print(
        f"{Fore.BLUE}Description: {Fore.YELLOW}{item.get('description', '')}{Fore.RESET}"
    )

    pending_tasks = 0
    for tag, count in tags.items():
        if tag != "Completed":
            pending_tasks += count

    completed_tasks = tags.get("Completed", 0)

    print(
        f"{Fore.BLUE}Pending: {Fore.YELLOW}{pending_tasks}{Fore.RESET} | "
        f"{Fore.BLUE}Completed: {Fore.YELLOW}{completed_tasks}{Fore.RESET}"
    )

    if "standard" in item:
        field_name = "Standard" if "outcome" not in item else "Outcome"
        field_value = (
            item.get("standard") if "outcome" not in item else item.get("outcome")
        )
        print(f"{Fore.BLUE}{field_name}: {Fore.YELLOW}{field_value}{Fore.RESET}")
        if field_name == "Outcome":
            print("Defining what 'DONE' means.")

    all_pending_tasks = warrior.load_tasks()["pending"]
    item_name = item["name"]
    item_aor_prefix = "AoR." + item_name
    relevant_tasks = [
        task
        for task in all_pending_tasks
        if task.get("project")
        and (
            task.get("project") == item_name
            or task.get("project").startswith(item_aor_prefix)
        )
    ]

    try:
        creation_date = get_creation_date_fn(item_name, relevant_tasks)
    except TypeError:
        creation_date = get_creation_date_fn(item_name)
    if creation_date:
        current_datetime = datetime.now()
        creation_time_difference = current_datetime - creation_date
        creation_days_remaining = creation_time_difference.days
        creation_time_remaining = creation_time_difference.seconds
        creation_time_prefix = "-" if creation_days_remaining > 0 else "+"
        creation_time_remaining_formatted = str(
            timedelta(seconds=abs(creation_time_remaining))
        )
        creation_time_difference_formatted = (
            f"({creation_time_prefix}{abs(creation_days_remaining)} days, "
            f"{creation_time_remaining_formatted})"
        )
        print(
            f"{Fore.BLUE}Creation Date: {Fore.YELLOW}{creation_date} "
            f"{creation_time_difference_formatted}{Fore.RESET}"
        )

    try:
        last_modified_date = get_last_modified_date_fn(item_name, relevant_tasks)
    except TypeError:
        last_modified_date = get_last_modified_date_fn(item_name)
    if last_modified_date:
        current_datetime = datetime.now()
        last_modified_time_difference = current_datetime - last_modified_date
        last_modified_days_remaining = last_modified_time_difference.days
        last_modified_time_remaining = last_modified_time_difference.seconds
        last_modified_time_prefix = "-" if last_modified_days_remaining > 0 else "+"
        last_modified_time_remaining_formatted = str(
            timedelta(seconds=abs(last_modified_time_remaining))
        )
        last_modified_time_difference_formatted = (
            f"({last_modified_time_prefix}{abs(last_modified_days_remaining)} days, "
            f"{last_modified_time_remaining_formatted})"
        )
        print(
            f"{Fore.BLUE}Last Modified Date: {Fore.YELLOW}{last_modified_date} "
            f"{last_modified_time_difference_formatted}{Fore.RESET}"
        )

    if "outcome" in item:
        print(f"{Fore.BLUE}Outcome: {Fore.YELLOW}{item['outcome']}{Fore.RESET}")

    print(f"{Fore.BLUE}Tags:{Fore.RESET}")
    tasks_by_tag = {}
    no_tag_tasks = []
    for task in relevant_tasks:
        task_tags = task.get("tags", [])
        if not task_tags:
            no_tag_tasks.append(task)
            continue
        for tag in task_tags:
            tasks_by_tag.setdefault(tag, []).append(task)

    now = datetime.now()
    for tag, count in tags.items():
        if tag != "Completed":
            print(
                f" - {Fore.BLACK}{Back.YELLOW}{tag}{Fore.RESET}{Back.RESET} "
                f"({count} task{'s' if count > 1 else ''})"
            )

            for task in tasks_by_tag.get(tag, []):
                task_id = task["id"]
                task_description = task.get("description", "")
                time_remaining = ""
                if "due" in task:
                    try:
                        due_date = datetime.strptime(task["due"], "%Y%m%dT%H%M%SZ")
                        time_remaining = str(due_date - now).split(".")[0]
                    except ValueError:
                        time_remaining = ""
                print(
                    f"\t{Fore.YELLOW}{task_id}{Fore.RESET}, "
                    f"{Fore.CYAN}{task_description}{Fore.RESET} {time_remaining}"
                )

    if no_tag_tasks:
        print(
            f" - \033[1;31m No Tag Tasks:\033[0m "
            f"({len(no_tag_tasks)} task{'s' if len(no_tag_tasks) > 1 else ''})"
        )
        for task in no_tag_tasks:
            task_id = task["id"]
            task_description = task.get("description", "")
            time_remaining = ""
            if "due" in task:
                try:
                    due_date = datetime.strptime(task["due"], "%Y%m%dT%H%M%SZ")
                    time_remaining = str(due_date - now).split(".")[0]
                except ValueError:
                    time_remaining = ""
            print(
                f"\t{Fore.RED}{task_id}{Fore.RESET}, "
                f"{Fore.CYAN}{task_description}{Fore.RESET} {time_remaining}"
            )
    else:
        print("No tags found.")

    if "annotations" in item:
        print(f"\n{Fore.BLUE}Annotations:{Fore.RESET}")
        for annotation in item["annotations"]:
            timestamp = annotation.get("timestamp")
            content = annotation.get("content", "")
            print(
                f" - {Fore.YELLOW}{timestamp}{Fore.RESET}: "
                f"{Fore.YELLOW}{content}{Fore.RESET}"
            )

    if "workLogs" in item:
        print(f"{Fore.BLUE}Work Logs:{Fore.RESET}")
        for work_log in item["workLogs"]:
            timestamp = work_log.get("timestamp")
            content = work_log.get("content", "")
            print(
                f" - {Fore.YELLOW}{timestamp}{Fore.RESET}: "
                f"{Fore.YELLOW}{content}{Fore.RESET}"
            )


def get_multiline_input(prompt_message):
    session = PromptSession()
    bindings = KeyBindings()

    @bindings.add("c-c")
    def _(event):
        event.app.exit()

    @bindings.add("c-s")
    def _(event):
        event.app.exit(result=event.app.current_buffer.text)

    return session.prompt(
        HTML(f"<skyblue>{prompt_message}</skyblue>\n> "),
        multiline=True,
        key_bindings=bindings,
        complete_while_typing=False,
        style=Style.from_dict({"prompt": "bg:#008800 #ffffff"}),
    )


def update_item(items, item_index, file_path, specific_field, aors, projects):
    commands = [
        "Add description",
        "Add annotation",
        "Add work log entry",
        f"Add {specific_field}",
        "Go back",
    ]
    print("Use CTRL+C to exit or CTRL+S to exit and save from edit screen.")
    while True:
        questions = [
            inquirer.List(
                "command",
                message="Please select a command",
                choices=commands,
            ),
        ]
        answers = inquirer.prompt(questions)

        if answers["command"] == "Add description":
            text = get_multiline_input("Enter Description: ")
            items[item_index]["description"] = text
            print(f"Added Description: {text}")
            save_sultandb(file_path, aors, projects)

        elif answers["command"] == "Add annotation":
            text = get_multiline_input("Enter Annotation: ")
            timestamp = datetime.now()
            entry = {"content": text, "timestamp": timestamp}
            if "annotations" not in items[item_index]:
                items[item_index]["annotations"] = []
            items[item_index]["annotations"].append(entry)
            print(f"Added Annotation: {text} at {timestamp}")
            save_sultandb(file_path, aors, projects)

        elif answers["command"] == "Add work log entry":
            text = get_multiline_input("Enter Work Log Entry: ")
            timestamp = datetime.now()
            entry = {"content": text, "timestamp": timestamp}
            if "workLogs" not in items[item_index]:
                items[item_index]["workLogs"] = []
            items[item_index]["workLogs"].append(entry)
            print(f"Added Work Log Entry: {text} at {timestamp}")
            save_sultandb(file_path, aors, projects)

        elif answers["command"] == f"Add {specific_field}":
            text = get_multiline_input(f"Enter {specific_field.capitalize()}: ")
            items[item_index][specific_field] = text
            print(f"Added {specific_field.capitalize()}: {text}")
            save_sultandb(file_path, aors, projects)

        elif answers["command"] == "Go back":
            break
