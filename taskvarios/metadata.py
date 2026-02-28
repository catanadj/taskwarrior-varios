"""Metadata update helpers extracted from TaskVarios."""

from datetime import datetime

import questionary
from rich.console import Console

from taskvarios.storage import load_sultandb, save_sultandb


def update_metadata_field(item_name, field_to_update, db_path):
    console = Console()

    aors, projects = load_sultandb(db_path)
    all_items = aors + projects

    selected_item = next((item for item in all_items if item["name"] == item_name), None)

    if not selected_item:
        if item_name.startswith("AoR."):
            item_name_no_prefix = item_name[4:]
            selected_item = next(
                (item for item in all_items if item["name"] == item_name_no_prefix),
                None,
            )
        else:
            item_name_with_prefix = "AoR." + item_name
            selected_item = next(
                (item for item in all_items if item["name"] == item_name_with_prefix),
                None,
            )

    if not selected_item:
        console.print(f"No metadata found for {item_name}.", style="bold red")
        return

    if field_to_update == "description":
        new_description = questionary.text(
            "Enter new description:", default=selected_item.get("description", "")
        ).ask()
        selected_item["description"] = new_description
        console.print("Description updated.", style="bold green")
    elif field_to_update == "standard_or_outcome":
        if selected_item["name"].startswith("AoR."):
            field_name = "standard"
        else:
            field_name = "outcome"
        new_value = questionary.text(
            f"Enter new {field_name}:", default=selected_item.get(field_name, "")
        ).ask()
        selected_item[field_name] = new_value
        console.print(f"{field_name.capitalize()} updated.", style="bold green")
    elif field_to_update == "annotations":
        timestamp = datetime.now().isoformat()
        content = questionary.text("Enter annotation content:").ask()
        annotation = {"timestamp": timestamp, "content": content}
        if "annotations" not in selected_item:
            selected_item["annotations"] = []
        selected_item["annotations"].append(annotation)
        console.print("Annotation added.", style="bold green")
    elif field_to_update == "workLogs":
        timestamp = datetime.now().isoformat()
        content = questionary.text("Enter work log content:").ask()
        work_log = {"timestamp": timestamp, "content": content}
        if "workLogs" not in selected_item:
            selected_item["workLogs"] = []
        selected_item["workLogs"].append(work_log)
        console.print("Work log added.", style="bold green")
    else:
        console.print("Invalid field to update.", style="bold red")
        return

    if selected_item in aors:
        for idx, aor in enumerate(aors):
            if aor["name"] == selected_item["name"]:
                aors[idx] = selected_item
                break
    elif selected_item in projects:
        for idx, project in enumerate(projects):
            if project["name"] == selected_item["name"]:
                projects[idx] = selected_item
                break

    save_sultandb(db_path, aors, projects)
    console.print("Changes saved to SultanDB.", style="bold green")
