# DevApp Requirements Specification (Development Set)

> **Notice (Invariant D13):** This requirements document is strictly reserved for prompt tuning, ablation experiments, and few-shot calibration of Agent 1 and Agent 3 during development. It MUST NEVER be used for final benchmark evaluations, which run exclusively against `eval/ground_truth/requirements.md`.

---

## REQ-DEV-01: Task Creation
The user interface shall provide an input field with the accessible name "Task title" and an "Add Task" button. When the user enters a non-empty task description and activates the "Add Task" button, the system shall append the task to the active tasks list.

## REQ-DEV-02: Task Completion
Each task item in the active list shall display a "Complete Task" button. Activating this button shall transition the task status from "Active" to "Completed" and update its status badge text accordingly.

## REQ-DEV-03: Priority Filtering
The application shall provide a filter combobox with the accessible name "Filter by priority" containing options for "All", "High", "Medium", and "Low". Selecting a priority option shall restrict the visible task items to those matching the selected priority.

## REQ-DEV-04: Task Deletion
Each task item shall include a "Delete Task" button. Activating this button shall remove the item from the list and decrease the total task count displayed in the header.

## REQ-DEV-05: System Audit Archival (Backend Non-Observable)
The task management service shall transmit encrypted audit telemetry to an internal enterprise logging cluster upon every state change. This process executes entirely in background workers and does not alter the user interface.
