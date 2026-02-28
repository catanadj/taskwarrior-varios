"""Data operations extracted from TaskVarios."""

import inquirer
from colorama import Fore
from taskw import TaskWarrior as Warrior

from taskvarios.storage import save_sultandb


warrior = Warrior()


def search_data(aors, projects):
    search_term = input("Enter the search term: ")
    found_entries = []

    for aor in aors:
        entry = {"name": f"AoR: {aor['name']}", "matches": []}

        if search_term in aor["description"]:
            entry["matches"].append(("Description", aor["description"]))

        if search_term in aor["standard"]:
            entry["matches"].append(("Standard", aor["standard"]))

        for annotation in aor.get("annotations", []):
            if search_term in annotation["content"]:
                entry["matches"].append(("Annotation", annotation["content"]))

        for work_log in aor.get("workLogs", []):
            if search_term in work_log["content"]:
                entry["matches"].append(("Work Log Entry", work_log["content"]))

        if entry["matches"]:
            found_entries.append(entry)

    for project in projects:
        entry = {"name": f"Project: {project['name']}", "matches": []}

        if search_term in project["description"]:
            entry["matches"].append(("Description", project["description"]))

        if search_term in project["outcome"]:
            entry["matches"].append(("Outcome", project["outcome"]))

        for annotation in project.get("annotations", []):
            if search_term in annotation["content"]:
                entry["matches"].append(("Annotation", annotation["content"]))

        for work_log in project.get("workLogs", []):
            if search_term in work_log["content"]:
                entry["matches"].append(("Work Log Entry", work_log["content"]))

        if entry["matches"]:
            found_entries.append(entry)

    if found_entries:
        print(f"Search Results for '{search_term}':")
        for entry in found_entries:
            print(f"{Fore.BLUE}{entry['name']}{Fore.RESET}")
            for match in entry["matches"]:
                field_name, field_value = match
                field_value = field_value.replace(
                    search_term, f"{Fore.YELLOW}{search_term}{Fore.RESET}"
                )
                print(f" - {field_name}: {field_value}")
    else:
        print(f"No results found for '{search_term}'.")

def clear_data(aors, projects, file_path):
    while True:
        commands = [
            "All AoR data",
            "All Projects data",
            "Everything",
            "Individual AoR or Project",
            "Go back",
        ]
        questions = [
            inquirer.List(
                "command",
                message="Please select a command",
                choices=commands,
            ),
        ]
        answers = inquirer.prompt(questions)

        if answers["command"] == "All AoR data":
            confirmation = confirm_action(
                "Are you sure you want to clear all AoR data?"
            )
            if confirmation:
                for aor in aors:
                    aor["description"] = ""
                    aor["standard"] = ""
                    aor["annotations"] = []
                    aor["workLogs"] = []
                print("Cleared all AoR data.")
                save_sultandb(file_path, aors, projects)
            else:
                print("Action canceled.")

        elif answers["command"] == "All Projects data":
            confirmation = confirm_action(
                "Are you sure you want to clear all Projects data?"
            )
            if confirmation:
                for project in projects:
                    project["description"] = ""
                    project["outcome"] = ""
                    project["annotations"] = []
                    project["workLogs"] = []
                print("Cleared all Projects data.")
                save_sultandb(file_path, aors, projects)
            else:
                print("Action canceled.")

        elif answers["command"] == "Everything":
            confirmation = confirm_action(
                "Are you sure you want to clear everything?"
            )
            if confirmation:
                for aor in aors:
                    aor["description"] = ""
                    aor["standard"] = ""
                    aor["annotations"] = []
                    aor["workLogs"] = []
                for project in projects:
                    project["description"] = ""
                    project["outcome"] = ""
                    project["annotations"] = []
                    project["workLogs"] = []
                print("Cleared all AoR and Project data.")
                save_sultandb(file_path, aors, projects)
            else:
                print("Action canceled.")

        elif answers["command"] == "Individual AoR or Project":
            # Existing code for clearing individual AoR or Project
            commands = ["AoR", "Project", "Go back"]
            questions = [
                inquirer.List(
                    "command",
                    message="Would you like to clear an AoR or a Project?",
                    choices=commands,
                ),
            ]
            answers = inquirer.prompt(questions)

            if answers["command"] == "AoR":
                if len(aors) == 0:
                    print("No AoRs available.")
                else:
                    while True:
                        questions = [
                            inquirer.List(
                                "aor",
                                message="Please select an AoR",
                                choices=[aor["name"] for aor in aors] + ["Go back"],
                            ),
                        ]
                        answers = inquirer.prompt(questions)

                        if answers["aor"] == "Go back":
                            break

                        item_index = next(
                            index
                            for (index, d) in enumerate(aors)
                            if d["name"] == answers["aor"]
                        )
                        aor = aors[item_index]
                        aor["description"] = ""
                        aor["standard"] = ""
                        aor["annotations"] = []
                        aor["workLogs"] = []
                        print("Cleared selected AoR data.")
                        save_sultandb(file_path, aors, projects)

            elif answers["command"] == "Project":
                if len(projects) == 0:
                    print("No Projects available.")
                else:
                    while True:
                        questions = [
                            inquirer.List(
                                "project",
                                message="Please select a Project",
                                choices=[project["name"] for project in projects]
                                + ["Go back"],
                            ),
                        ]
                        answers = inquirer.prompt(questions)

                        if answers["project"] == "Go back":
                            break

                        item_index = next(
                            index
                            for (index, d) in enumerate(projects)
                            if d["name"] == answers["project"]
                        )
                        project = projects[item_index]
                        project["description"] = ""
                        project["outcome"] = ""
                        project["annotations"] = []
                        project["workLogs"] = []
                        print("Cleared selected Project data.")
                        save_sultandb(file_path, aors, projects)

        elif answers["command"] == "Go back":
            break

def confirm_action(message):
    questions = [
        inquirer.Confirm(
            "confirmation",
            message=message,
        ),
    ]
    answers = inquirer.prompt(questions)
    return answers["confirmation"]

def get_tags_for_aor(aor_name):
    tasks = warrior.load_tasks()["pending"]
    aor_tasks = [
        task
        for task in tasks
        if "tags" in task and task.get("project") == f"AoR.{aor_name}"
    ]

    tag_counts = {}
    for task in aor_tasks:
        for tag in task["tags"]:
            if tag.startswith("AoR.") or tag.startswith("project:"):
                continue
            if tag not in tag_counts:
                tag_counts[tag] = 0
            tag_counts[tag] += 1

    return tag_counts

def sync_with_taskwarrior(aors, projects, file_path):
    tasks = warrior.load_tasks()

    task_projects = set()

    for task in tasks["pending"]:
        project = task.get("project")
        if project:
            task_projects.add(project)

    active_aors = []
    inactive_aors = []
    completed_aors = []
    active_projects = []
    inactive_projects = []
    completed_projects = []

    for aor in aors:
        if f"AoR.{aor['name']}" in task_projects:
            active_aors.append(aor)
        else:
            if aor["status"] != "Completed":
                aor["status"] = "Completed"
            completed_aors.append(aor)

    for project in projects:
        if project["name"] in task_projects:
            active_projects.append(project)
        else:
            if project["status"] != "Completed":
                project["status"] = "Completed"
            completed_projects.append(project)

    for task_project in task_projects:
        if task_project.startswith("AoR."):
            aor_name = task_project[4:]
            if aor_name not in [aor["name"] for aor in aors]:
                new_aor = {
                    "name": aor_name,
                    "description": "",
                    "standard": "",
                    "annotations": [],
                    "workLogs": [],
                    "status": "Active",
                }
                active_aors.append(new_aor)

        elif task_project not in [project["name"] for project in projects]:
            new_project = {
                "name": task_project,
                "description": "",
                "outcome": "",
                "annotations": [],
                "workLogs": [],
                "status": "Active",
            }
            active_projects.append(new_project)

    # Save variosdb.json
    save_sultandb(
        file_path,
        active_aors + completed_aors,
        active_projects + completed_projects,
    )

    return (
        active_aors,
        inactive_aors,
        active_projects,
        inactive_projects + completed_projects,
    )

