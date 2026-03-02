"""Interactive prompt workflow extracted from TaskVarios."""

import inquirer
import questionary
from questionary import Style


def interactive_prompt(
    file_path,
    aors,
    projects,
    sync_with_taskwarrior_fn,
    update_item_fn,
    get_tags_for_item_fn,
    view_data_fn,
    search_data_fn,
    call_and_process_task_projects_fn,
    search_task_fn,
    clear_data_fn,
    basic_summary_fn,
    detailed_summary_fn,
    display_inbox_tasks_fn,
    display_due_tasks_fn,
    handle_task_fn,
    print_tasks_for_selected_day_fn,
    display_overdue_tasks_fn,
    recurrent_report_fn,
    eisenhower_fn,
    task_control_center_fn,
):
    # Load from SultanDB
    # aors, projects = load_sultandb(file_path)

    # Sync with TaskWarrior to update projects and AoRs
    active_aors, inactive_aors, active_projects, inactive_projects = (
        sync_with_taskwarrior_fn(aors, projects, file_path)
    )

    commands = {
        "ua": ("Update AoRs", ""),
        "up": ("Update Projects", ""),
        "e": ("Exit", ""),
        "s": ("Search", ""),
        "c": ("Clear Data", ""),
        "b": ("Basic summary", ""),
        "d": ("Detailed summary", ""),
        "tc": ("Task centre", ""),
        "ht": ("Handle Task", ""),
        "o": ("Overdue tasks list", ""),
        "td": ("Daily tasks", ""),
        "rr": ("Recurrent tasks report", ""),
        "z": ("Process or Value assignment", ""),
    }

    custom_style = Style(
        [
            ("qmark", "fg:#673ab7 bold"),
            ("question", "bold"),
            ("answer", "fg:#f44336 bold"),
            ("pointer", "fg:#673ab7 bold"),
            ("highlighted", "fg:#673ab7 bold"),
            ("selected", "fg:#cc5454"),
            ("separator", "fg:#cc5454"),
            ("instruction", ""),
            ("text", ""),
            ("disabled", "fg:#858585 italic"),
        ]
    )

    while True:
        print("\nPlease select a command:")
        for short, (full, emoji) in commands.items():
            print(f"{short:<2}: {emoji} {full:<18}")
        print("type command or press Enter to select a command from list.")

        command = input()
        if command:
            command = commands.get(command)[0] if commands.get(command) else None
            if not command:
                print("Invalid command.")
                continue
        else:
            command = questionary.select(
                "Please select a command",
                choices=[full for full, emoji in commands.values()],
                style=custom_style,
            ).ask()

        if command == "Update AoRs":
            all_aors = active_aors + inactive_aors
            # Sort AoRs alphabetically
            all_aors.sort(key=lambda aor: aor["name"])

            # Group AoRs by prefix
            aor_groups = {}
            for aor in all_aors:
                prefix = aor["name"].split(".")[0]
                if prefix not in aor_groups:
                    aor_groups[prefix] = []
                aor_groups[prefix].append(aor)

            # Prompt to select an AoR group
            aor_group_choices = list(aor_groups.keys()) + ["Back"]
            questions = [
                inquirer.List(
                    "aor_group",
                    message="Please select an Area of Responsibility Group",
                    choices=aor_group_choices,
                ),
            ]
            aor_group_answers = inquirer.prompt(questions)
            if aor_group_answers["aor_group"] == "Back":
                continue

            selected_aor_group = aor_groups[aor_group_answers["aor_group"]]

            # Now prompt to select a specific AoR
            aor_choices = [aor["name"] for aor in selected_aor_group] + ["Back"]
            questions = [
                inquirer.List(
                    "aor",
                    message="Please select an Area of Responsibility",
                    choices=aor_choices,
                ),
            ]
            aor_answers = inquirer.prompt(questions)
            if aor_answers["aor"] == "Back":
                continue

            selected_aor = next(
                (
                    aor
                    for aor in selected_aor_group
                    if aor["name"] == aor_answers["aor"]
                ),
                None,
            )

            if selected_aor:
                # Find the index of the selected AoR
                item_index = all_aors.index(selected_aor)

                # Get tags for the selected AoR
                aor_tags = get_tags_for_item_fn(selected_aor["name"])

                # Prompt to view data or update
                options = ["Update", "View Data"]
                questions = [
                    inquirer.List(
                        "action",
                        message="Please select an action",
                        choices=options,
                    ),
                ]
                action_answers = inquirer.prompt(questions)

                if action_answers["action"] == "Update":
                    # Existing code to update the selected AoR
                    update_item_fn(
                        all_aors, item_index, file_path, "standard", aors, projects
                    )
                elif action_answers["action"] == "View Data":
                    view_data_fn(selected_aor, aor_tags)

        elif command == "Update Projects":
            all_projects = active_projects + inactive_projects
            # Sort projects alphabetically
            all_projects.sort(key=lambda project: project["name"])

            # Group projects by prefix
            project_groups = {}
            for project in all_projects:
                prefix = project["name"].split(".")[0]
                if prefix not in project_groups:
                    project_groups[prefix] = []
                project_groups[prefix].append(project)

            # Prompt to select a project group
            project_group_choices = list(project_groups.keys()) + ["Back"]
            questions = [
                inquirer.List(
                    "project_group",
                    message="Please select a Project Group",
                    choices=project_group_choices,
                ),
            ]
            project_group_answers = inquirer.prompt(questions)
            if project_group_answers["project_group"] == "Back":
                continue

            selected_project_group = project_groups[
                project_group_answers["project_group"]
            ]

            # Now prompt to select a specific project
            project_choices = [
                project["name"] for project in selected_project_group
            ] + ["Back"]
            questions = [
                inquirer.List(
                    "project",
                    message="Please select a Project",
                    choices=project_choices,
                ),
            ]
            project_answers = inquirer.prompt(questions)
            if project_answers["project"] == "Back":
                continue

            selected_project = next(
                (
                    project
                    for project in selected_project_group
                    if project["name"] == project_answers["project"]
                ),
                None,
            )

            if selected_project:
                # Find the index of the selected project
                item_index = all_projects.index(selected_project)

                # Get tags for the selected project
                project_tags = get_tags_for_item_fn(selected_project["name"])

                # Prompt to view data or update
                options = ["Update", "View Data"]
                questions = [
                    inquirer.List(
                        "action",
                        message="Please select an action",
                        choices=options,
                    ),
                ]
                action_answers = inquirer.prompt(questions)

                if action_answers["action"] == "Update":
                    # Existing code to update the selected project
                    update_item_fn(
                        all_projects,
                        item_index,
                        file_path,
                        "outcome",
                        aors,
                        projects,
                    )
                elif action_answers["action"] == "View Data":
                    view_data_fn(selected_project, project_tags)
        elif command == "Search":
            search_commands = [
                "Search Data",
                "Search Project",
                "Search Task",
                "Back",
            ]
            search_command = questionary.select(
                "Please select a search command",
                choices=search_commands,
                style=custom_style,
            ).ask()
            if search_command == "Search Data":
                search_data_fn(aors, projects)
            elif search_command == "Search Project":
                call_and_process_task_projects_fn()
            elif search_command == "Search Task":
                search_task_fn()
        elif command == "View Data":
            all_items = active_aors + active_projects
            all_items.sort(key=lambda x: x["name"])

            item_choices = [item["name"] for item in all_items] + ["Back"]
            questions = [
                inquirer.List(
                    "item",
                    message="Please select an item to view data",
                    choices=item_choices,
                ),
            ]
            answers = inquirer.prompt(questions)
            if answers["item"] == "Back":
                continue

            selected_item = next(
                (item for item in all_items if item["name"] == answers["item"]),
                None,
            )
            if selected_item:
                if selected_item in active_aors:
                    item_tags = get_tags_for_item_fn(selected_item["name"])
                elif selected_item in active_projects:
                    item_tags = get_tags_for_item_fn(selected_item["name"])
                view_data_fn(selected_item, item_tags)
            else:
                print("Invalid item selection.")

        elif command == "Exit":
            break

        elif command == "Clear Data":
            clear_data_fn(aors, projects, file_path)
        elif command == "Basic summary":
            basic_summary_fn()

        elif command == "Detailed summary":
            detailed_summary_fn()
        elif command == "Inbox":
            display_inbox_tasks_fn()
        elif command == "Task list":
            display_due_tasks_fn()
        elif command == "Handle Task":
            handle_task_fn()
        elif command == "Daily tasks":
            print_tasks_for_selected_day_fn()
        elif command == "Overdue tasks list":
            display_overdue_tasks_fn()
        elif command == "Recurrent tasks report":
            recurrent_report_fn()
        elif command == "Process or Value assignment":
            eisenhower_fn()
        elif command == "Task centre":
            task_control_center_fn()
