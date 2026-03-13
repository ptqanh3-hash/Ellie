# TaskMNG MVP UAT Test Cases

## Scope
- This UAT set targets the first implementable MVP in this repository.
- Focus areas:
  - local workspace initialization
  - Excel import
  - opportunity / phase / task CRUD
  - dashboard visibility
  - task board updates
  - validation and unhappy paths

## Assumptions
- The app runs locally on Windows with Python installed.
- A SQLite database file is created automatically inside the project workspace.
- The workbook import source is the current Excel file used for task management.

## Test Data
- Source workbook:
  - `AM_Itouchu Techno- Solutions_CTC_2025~.xlsx`
- Example local users:
  - `Ptqanh3`
  - `Bqthanh`
  - `Trquyen`

## Happy Cases

### UAT-H01 - First Launch Creates Local Workspace
- Precondition:
  - no existing local database file
- Steps:
  1. Launch the app.
  2. Observe the initial landing state.
- Expected Result:
  - app starts successfully
  - SQLite database is created automatically
  - navigation and default empty-state UI load without crash

### UAT-H02 - Import Excel Workbook Into Local Database
- Precondition:
  - app is running
  - valid workbook path is available
- Steps:
  1. Start Excel import from the app or import service.
  2. Select the workbook.
  3. Confirm import.
- Expected Result:
  - opportunities, phases, and tasks are created in local DB
  - import report includes totals
  - app remains responsive

### UAT-H03 - Dashboard Shows Imported Metrics
- Precondition:
  - workbook import completed successfully
- Steps:
  1. Open dashboard.
  2. Review KPI cards and overdue list.
- Expected Result:
  - dashboard shows non-zero counts for imported data
  - overdue list and due-soon list populate correctly when matching tasks exist
  - counts are consistent with local DB state

### UAT-H04 - Create New Opportunity With Default Phase
- Precondition:
  - app is running
- Steps:
  1. Open opportunity creation form.
  2. Enter title, department, pipeline status, priority stage, detail.
  3. Save.
- Expected Result:
  - new opportunity is created
  - default phase `General` is created automatically
  - opportunity appears in list view immediately

### UAT-H05 - Add New Phase Under Existing Opportunity
- Precondition:
  - an opportunity already exists
- Steps:
  1. Open opportunity detail.
  2. Add a new phase.
  3. Save phase.
- Expected Result:
  - new phase appears in phase list
  - phase order is stored correctly
  - no existing task is lost

### UAT-H06 - Add Task Under Selected Phase
- Precondition:
  - an opportunity and phase already exist
- Steps:
  1. Open phase detail area.
  2. Add a task with owner, PIC, status, deadline, and next action.
  3. Save task.
- Expected Result:
  - task appears in phase task list
  - task appears in board column matching its manual status
  - deadline and owner are saved correctly

### UAT-H07 - Update Task Status From Board
- Precondition:
  - at least one task exists
- Steps:
  1. Open task board.
  2. Change a task status to another valid manual status.
- Expected Result:
  - task moves to the target board column
  - task manual status is updated in database
  - update is visible when reopening the opportunity detail view

### UAT-H08 - Dashboard Refresh Reflects Newly Added Task
- Precondition:
  - at least one new task was added or updated
- Steps:
  1. Return to dashboard.
  2. Refresh or reopen dashboard data.
- Expected Result:
  - KPI counts and recent tasks reflect the latest DB state
  - overdue and due-soon calculations remain correct

## Unhappy Cases

### UAT-U01 - Import Rejects Missing Workbook Path
- Precondition:
  - app is running
- Steps:
  1. Trigger import using a non-existent workbook path.
- Expected Result:
  - import fails gracefully
  - user receives readable error message
  - no partial records are written

### UAT-U02 - Opportunity Save Fails Without Required Fields
- Precondition:
  - app is running
- Steps:
  1. Open opportunity creation form.
  2. Leave title or status empty.
  3. Try to save.
- Expected Result:
  - form save is blocked
  - validation message is shown
  - no invalid opportunity is created

### UAT-U03 - Task Save Fails Without Title
- Precondition:
  - an opportunity and phase already exist
- Steps:
  1. Open add task form.
  2. Leave task title empty.
  3. Save.
- Expected Result:
  - validation blocks save
  - user sees clear message
  - no invalid task is inserted

### UAT-U04 - Invalid Status Update Is Rejected
- Precondition:
  - at least one task exists
- Steps:
  1. Attempt to update task status with a value not in the allowed status list.
- Expected Result:
  - update is rejected
  - database record remains unchanged
  - user sees readable feedback or logged validation failure

### UAT-U05 - Import Handles Ambiguous Rows Without Crash
- Precondition:
  - workbook contains blank / merged / inconsistent rows
- Steps:
  1. Run import on workbook containing mixed row structure.
- Expected Result:
  - importer skips or safely normalizes ambiguous rows
  - import completes without app crash
  - import report exposes what was ignored or normalized

## Exit Criteria
- All happy cases pass.
- All unhappy cases fail safely with controlled behavior.
- No test case produces uncaught exception or corrupt local DB state.

