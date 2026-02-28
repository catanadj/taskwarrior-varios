------------
# TaskVarios


## An Enhanced Utility Suite for TaskWarrior

### Overview:
TaskSultan has been crafted to enhance the management of 'Areas of Responsibility' (AoRs) and projects within TaskWarrior. It not only offers auxiliary reports but streamlines tasks associated with AoRs and projects.

### Functionality:
Upon execution, TaskSultan generates a JSON file in its directory detailing every AoR and Project within TaskWarrior.

Projects: Each project can be enriched with metadata such as worklogs, annotations, descriptions, and outcomes.

AoRs: Unlike projects which culminate in outcomes, AoRs maintain standards. While a project like "Buy Car X" targets owning the car as its outcome, once achieved, the car transitions to an AoR where standards like maintenance, revision dates, and care are tracked.

### Technical Details:
TaskVarios identifies AoRs and projects based on their nomenclature in TaskWarrior. AoRs are prefixed with 'AoR' (e.g., AoR.cars.carX). TaskVarios then differentiates and categorizes them, offering customized outcome/standard fields, visual distinctions via color-coding, and menu separation.

### Getting Started:
    Clone the repository.
    Execute the script for an interactive menu or use menu shortcuts as command-line arguments.

### Detailed information about each of the reports
  #### (sp) Search project
Using this report you can search for project/AoRs with fuzzy name completion. Once an item has been selected, a detailed view is going to be displayed including a tree structure of that individual item and options to search another/update/handle tasks or exit.
  #### (b) Basic summary
This is going to display a tree of the AoRs/Projects that you have with only a minimum of information - only the tags of each and count of the tasks for each tag of the item.
  #### (d) Detailed summary
This builds on the basic report, the most relavant task for each tag is shown.
  #### (a) All-inclusive 
This will display in tree form all the items with each task of each tag.

**Auxiliary reports**:
  #### (tl) Task list
  Will display a list of task sorted by due date up to 20 years.
  #### (td) Daily tasks
  A report that is displaying tasks due yesterday, today and tomorrow.
  #### (i) Inbox tasks
  All the inbox tasks (the tag +in) sorted by entry time.
  #### (o) Overdue
  Overdue tasks sorted by due time.
  #### (rr) Recurring tasks status - command line argument option only
  A table is displayed with the status of the recurring tasks from the last seven days. It is useful for habit tracking overview.
 #### Clear data - this option is going to clear only the metadata stored in the json file, not the TaskWarrior database.
      
      
