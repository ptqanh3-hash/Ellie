# TaskMNG Desktop App Spec

## 1. Product Overview

### 1.1 Working Name
- `TaskMNG Desktop`

### 1.2 Background
- Current task management is maintained in Excel sheet `Opt Manage_Task List`.
- The sheet mixes opportunity tracking, phase breakdown, and actionable tasks in the same grid.
- Adding, removing, or restructuring phases and tasks is slow and fragile because the data depends on merged cells, manual fill-down patterns, and spreadsheet formulas.
- The goal is to replace that Excel-driven workflow with a dedicated local-first desktop application that is easier to update, clearer to navigate, and visually modern.

### 1.3 Product Vision
- A private desktop app for managing opportunities, phases, and tasks with a clean, modern interface.
- Data is stored locally and controlled by the user.
- The app should feel faster and safer than Excel for daily operations while preserving the practical workflow already used by the team.

### 1.4 Target Users
- Primary user: account manager / delivery coordinator maintaining opportunities and internal follow-up tasks.
- Secondary users: internal teammates who may be assigned as owner or PIC on tasks.

### 1.5 Design Principles
- Local first: app works fully offline with local storage.
- Structured over freeform: separate business entities instead of overloading a spreadsheet row.
- Fast task editing: common updates should take 1 to 3 clicks.
- Clear hierarchy: opportunity -> phase -> task.
- Modern but calm: visual system should feel premium, clean, and work-focused.

## 2. Problem Statement

### 2.1 Current Pain Points
- Excel rows represent mixed concepts: customer context, opportunity context, phase context, and task context.
- Reordering tasks or inserting a new phase breaks visual grouping.
- Status logic is partly manual and partly formula-based, which is hard to trust over time.
- Tracking overdue items depends on spreadsheet formulas and visual scanning.
- Historical updates are mixed into cells instead of being treated as activity records.
- Filtering, grouping, and seeing work by owner or due date is limited.

### 2.2 Opportunity for the App
- Normalize the data model.
- Make task updates fast and safe.
- Surface overdue and at-risk work automatically.
- Keep a clear audit trail of changes and updates.
- Provide a modern dashboard for daily follow-up.

## 3. Product Goals And Scope

### 3.1 Goals
- Replace Excel as the primary daily workspace for task tracking.
- Support opportunity management with nested phases and tasks.
- Store all data locally in a robust, queryable format.
- Allow importing the current Excel source as a starting point.
- Provide dashboard, list, detail, and board views.
- Provide strong filtering, search, and deadline visibility.

### 3.2 Non-Goals For V1
- Multi-user real-time collaboration.
- Cloud sync.
- Mobile app.
- Deep integration with email, Teams, or calendar.
- Full enterprise workflow or approval engine.

### 3.3 Success Criteria
- Adding a new task under an existing phase takes under 15 seconds.
- Finding overdue items takes under 5 seconds from app launch.
- Editing a phase structure does not require manual row maintenance.
- Imported Excel data is understandable and usable without extensive cleanup.

## 4. Core Domain Model

### 4.1 Entities

#### Workspace
- Local database instance for one user or one local team setup.

#### Contact PIC
- External contact or counterpart being tracked for an opportunity.
- Fields:
  - `id`
  - `name`
  - `department_name`
  - `company_name`
  - `notes`

#### Opportunity
- Top-level business item currently represented by the Excel group row.
- Fields:
  - `id`
  - `title`
  - `department_name`
  - `external_pic_id`
  - `pipeline_status`
  - `priority_stage`
  - `detail`
  - `account_year`
  - `tags`
  - `created_at`
  - `updated_at`
  - `archived_at`

#### Phase
- Structured subdivision of an opportunity.
- Fields:
  - `id`
  - `opportunity_id`
  - `name`
  - `description`
  - `order_index`
  - `phase_status`
  - `planned_start_date`
  - `planned_end_date`
  - `actual_end_date`

#### Task
- Actionable unit of work inside a phase.
- Fields:
  - `id`
  - `opportunity_id`
  - `phase_id`
  - `title`
  - `description`
  - `owner_user_id`
  - `pic_user_id`
  - `manual_status`
  - `health_status`
  - `priority`
  - `deadline`
  - `completed_at`
  - `next_action`
  - `latest_update_summary`
  - `sort_order`
  - `created_at`
  - `updated_at`
  - `archived_at`

#### Task Update Log
- Immutable activity entries to replace freeform cell updates.
- Fields:
  - `id`
  - `task_id`
  - `author_user_id`
  - `entry_type`
  - `content`
  - `created_at`

#### User
- Local user directory for assignees.
- Fields:
  - `id`
  - `display_name`
  - `email`
  - `is_active`
  - `color_seed`

### 4.2 Relationship Model
- One `Opportunity` has many `Phase`.
- One `Phase` has many `Task`.
- One `Task` has many `Task Update Log`.
- One `Opportunity` may optionally link to one external `Contact PIC`.
- A `User` can be owner or PIC for many tasks.

## 5. Status Model

### 5.1 Opportunity Pipeline Status
- Example values:
  - `TT`
  - `Contract`
  - `KT3`
- Requirement:
  - Values must be configurable in settings because business labels may evolve.

### 5.2 Opportunity Priority Stage
- Example values from Excel:
  - `Approach`
  - `PoC`
  - `Bidding`
  - `Pending`
  - `Cancel`
- Requirement:
  - Stored as configurable taxonomy, not hard-coded constants.

### 5.3 Task Manual Status
- Default set:
  - `Not Started`
  - `In Progress`
  - `Blocked`
  - `Completed`
  - `Cancelled`

### 5.4 Task Health Status
- Computed status, read-only in UI.
- Default logic:
  - `Completed` when `manual_status = Completed`
  - `Delayed` when `deadline < today` and task is not completed
  - `Due Soon` when deadline is within configurable threshold, default 3 days
  - `On Track` otherwise
  - `No Deadline` when no deadline is set and task is not completed

### 5.5 Important Decision
- `manual_status` and `health_status` must be separate.
- This avoids the Excel problem where one displayed status is partly typed by hand and partly generated by formulas.

## 6. Key User Flows

### 6.1 First-Time Setup
1. User opens app.
2. User sees onboarding screen with options:
   - create empty workspace
   - import from Excel
3. If importing, user selects workbook and target sheet.
4. App previews mapped records.
5. User confirms import.
6. App lands on dashboard.

### 6.2 Create Opportunity
1. User clicks `New Opportunity`.
2. User enters title, department, external PIC, pipeline status, priority stage, detail.
3. App creates default phase `General`.
4. User may add more phases immediately.

### 6.3 Manage Phases
1. User opens opportunity detail.
2. User sees phases in left rail or vertical timeline.
3. User adds, renames, reorders, or archives phases.
4. Tasks inside each phase retain position and relationships.

### 6.4 Create And Update Task
1. User opens a phase.
2. User clicks `Add Task`.
3. User enters title, owner, PIC, deadline, manual status, next action.
4. User saves.
5. Later updates are added as log entries and summarized into latest update summary.

### 6.5 Daily Review
1. User opens dashboard.
2. User reviews overdue tasks, due soon tasks, tasks by owner, and stalled opportunities.
3. User clicks into opportunity or task and updates status inline.

### 6.6 Board Workflow
1. User opens task board.
2. User filters by owner, department, or opportunity.
3. User drags tasks between manual status columns.
4. App writes status change to update log automatically.

## 7. Functional Requirements

### 7.1 Opportunity Management
- Create, edit, archive, and restore opportunities.
- Assign department and external PIC.
- Maintain detail, pipeline status, and priority stage.
- Search opportunities by title, PIC name, department, or tag.
- Filter by status, stage, archived state, and owner activity.

### 7.2 Phase Management
- Create multiple phases per opportunity.
- Reorder phases.
- Archive phases without deleting historical tasks.
- Show phase progress based on child tasks.

### 7.3 Task Management
- Create, edit, duplicate, archive, and restore tasks.
- Assign owner and PIC separately.
- Set deadline, manual status, and priority.
- Add next action and description.
- Support inline editing from table and board views.
- Support bulk status update for selected tasks.

### 7.4 Update History
- Every meaningful task update can create a log entry.
- Show activity timeline in task detail.
- Allow pinning one entry as `latest update summary` or auto-fill it from newest entry.

### 7.5 Dashboard
- Show:
  - overdue tasks
  - due soon tasks
  - recently updated tasks
  - tasks by owner
  - opportunities with no updates in X days
  - counts by pipeline stage

### 7.6 Search And Filters
- Global quick search.
- Filter chips for owner, PIC, department, pipeline status, priority stage, manual status, health status, deadline range.
- Saved views for frequently used filters.

### 7.7 Import / Export
- Import initial dataset from Excel workbook.
- Map merged-cell layout into normalized entities.
- Export opportunities and tasks back to Excel or CSV in later phase.
- Preserve source file path metadata for reference.

### 7.8 Settings
- Manage taxonomy values:
  - pipeline status
  - priority stage
  - task priority
  - due soon threshold
- Manage local users.
- Select default startup screen.

## 8. Information Architecture

### 8.1 Primary Navigation
- MVP navigation:
  - `Dashboard`
  - `Opportunities`
  - `Task Board`
  - `Settings`
- Post-MVP navigation candidate:
  - `Calendar`

### 8.2 Secondary Navigation
- Within opportunity detail:
  - overview
  - phases
  - tasks
  - activity

## 9. Screen Specifications

### 9.1 Dashboard
- Purpose:
  - daily control center
- Layout:
  - left sidebar navigation
  - top header with search and quick actions
  - main area with summary cards, owner workload, due list, and recent activity
- Key modules:
  - KPI cards
  - overdue list
  - due soon list
  - workload by owner
  - opportunities lacking updates

### 9.2 Opportunity List
- Purpose:
  - browse and filter all opportunities
- Layout:
  - list/table with sticky filters and sorting
- Required columns:
  - title
  - department
  - external PIC
  - pipeline status
  - priority stage
  - open task count
  - delayed task count
  - latest update date

### 9.3 Opportunity Detail
- Purpose:
  - manage one opportunity in depth
- Layout:
  - hero header with summary
  - phase rail or segmented tabs
  - task list per selected phase
  - right-side context panel for notes or activity
- Key actions:
  - add phase
  - add task
  - reorder phases
  - update detail
  - archive opportunity

### 9.4 Task Board
- Purpose:
  - status-focused execution view
- Layout:
  - kanban columns by manual status
  - optional swimlanes by owner or phase
- Card content:
  - task title
  - opportunity name
  - phase name
  - owner
  - deadline
  - health badge

### 9.5 Calendar
- Release target:
  - post-MVP
- Purpose:
  - visualize deadlines
- Layout:
  - month and agenda views
- Required behavior:
  - click item opens task detail
  - color by health or owner

### 9.6 Task Detail Drawer
- Purpose:
  - edit without losing context
- Sections:
  - summary
  - assignees
  - status and dates
  - update history
  - next action

### 9.7 Settings
- Sections:
  - users
  - taxonomies
  - import / export
  - appearance
  - data backup

## 10. UI/UX Theme Specification

### 10.1 Visual Direction
- Mood:
  - modern, composed, soft-premium, focused
- Style:
  - rounded surfaces, layered translucent panels, soft gradients, low-noise shadows
- The UI should avoid generic project-management visuals and instead feel like a custom internal tool.

### 10.2 Color Palette Based On Attached Image
- Primary 700: `#5C60E8`
- Primary 500: `#7B88F0`
- Secondary 300: `#B7AFE8`
- Accent 200: `#DFC2E2`
- Ink 900: `#1E2140`
- Ink 700: `#4B4F73`
- Surface 0: `#FCFBFF`
- Surface 1: `#F4F2FD`
- Surface 2: `#ECE8FA`
- Border Soft: `#D9D3F0`
- Success: `#2E9B72`
- Warning: `#F3A93B`
- Danger: `#D95F7A`

### 10.3 Color Usage
- Primary gradient:
  - `linear-gradient(180deg, #5C60E8 0%, #7B88F0 58%, #B7AFE8 82%, #DFC2E2 100%)`
- Use gradient for:
  - dashboard header
  - selected nav accents
  - empty states
  - subtle page hero panels
- Keep content surfaces light for readability.
- Avoid filling large work areas with saturated color.

### 10.4 Typography
- Preferred direction:
  - elegant sans-serif with some personality, not default system feeling
- Suggested families:
  - `Manrope` for UI
  - `Plus Jakarta Sans` as backup option
- Type scale:
  - page title: 28/36 semibold
  - section title: 20/28 semibold
  - card title: 16/24 semibold
  - body: 14/22 regular
  - caption: 12/18 medium

### 10.5 Shape And Spacing
- Global radius:
  - cards 20px
  - inputs 14px
  - pills 999px
- Spacing scale:
  - 4, 8, 12, 16, 24, 32

### 10.6 Component Style Rules
- Sidebar:
  - soft dark-on-light with active item glow and pill selection state
- Cards:
  - white or near-white background with subtle violet-tinted borders
- Tables:
  - compact but breathable row height
  - sticky header
  - zebra striping very subtle only
- Inputs:
  - soft borders, strong focus ring in primary 500
- Badges:
  - filled pills with low-saturation backgrounds
- Modals and drawers:
  - blurred backdrop
  - large radius

### 10.7 Status Badge Colors
- `Not Started`: neutral lavender gray
- `In Progress`: primary 500
- `Blocked`: danger
- `Completed`: success
- `Cancelled`: muted gray
- `Delayed`: danger tint
- `Due Soon`: warning tint
- `On Track`: soft primary tint

### 10.8 Motion
- Subtle page-load fade and upward drift.
- Staggered reveal on dashboard cards.
- Fast board card drag transitions.
- Motion should stay under 220ms for common interactions.

### 10.9 Accessibility
- Minimum contrast target:
  - WCAG AA for all text and interactive states
- Do not rely on color alone for status.
- Keyboard navigation required for:
  - sidebar
  - table rows
  - form controls
  - task board cards

## 11. Technical Architecture

### 11.1 Recommended Stack
- Desktop shell: `Tauri`
- Frontend: `React + TypeScript + Vite`
- UI styling: `Tailwind CSS + CSS variables` or `Tailwind + shadcn/ui as a foundation only`
- Local database: `SQLite`
- ORM / query layer: `Drizzle ORM`
- State management:
  - server-state-like query layer for DB reads
  - lightweight client state with `Zustand`
- Validation: `Zod`
- Charts:
  - `Recharts` or `Visx`

### 11.2 Rationale
- Tauri keeps the app lightweight and Windows-friendly.
- React allows building a polished modern UI quickly.
- SQLite is durable and ideal for a local-first single-user desktop tool.
- Drizzle provides typed schema and migrations.

### 11.3 Application Layers
- `UI Layer`
  - views, components, forms, navigation
- `Application Layer`
  - commands, use cases, import workflows, validation rules
- `Domain Layer`
  - entities, status computation, business logic
- `Persistence Layer`
  - SQLite tables, migrations, repository access

### 11.4 Suggested Project Structure
```text
src/
  app/
  features/
    dashboard/
    opportunities/
    phases/
    tasks/
    settings/
    import/
  components/
  lib/
  styles/
src-tauri/
  src/
  capabilities/
db/
  migrations/
docs/
```

## 12. Data Schema Draft

### 12.1 Tables
- `users`
- `contacts`
- `opportunities`
- `phases`
- `tasks`
- `task_updates`
- `tags`
- `opportunity_tags`
- `app_settings`
- `imports`

### 12.2 Minimal Schema Notes
- `opportunities.external_pic_id` nullable FK to `contacts.id`
- `phases.opportunity_id` required FK
- `tasks.phase_id` required FK
- `tasks.opportunity_id` duplicated FK for simpler querying and denormalized read performance
- `task_updates.task_id` required FK

### 12.3 Derived Fields
- `health_status` may be:
  - computed at read time
  - or materialized and updated on write if performance becomes necessary
- V1 recommendation:
  - compute at read time to reduce sync bugs

## 13. Excel Import Specification

### 13.1 Input Source
- Existing workbook with sheet `Opt Manage_Task List`

### 13.2 Import Strategy
- Parse grouped rows and merged-cell ranges.
- Fill down parent context from repeated blank cells.
- Detect opportunity boundaries from changes in:
  - department
  - PIC name
  - pipeline title
  - pipeline status
  - priority stage
- Detect tasks from populated `Task` column.

### 13.3 Mapping Rules
- Excel `Department` -> `opportunities.department_name`
- Excel `Name PIC` -> `contacts.name`
- Excel `Pipeline` -> `opportunities.title` or `phase.name` depending on pattern
- Excel `Detail` -> `opportunities.detail`
- Excel `Status` -> `opportunities.pipeline_status`
- Excel `Prior` -> `opportunities.priority_stage`
- Excel `Task` -> `tasks.title`
- Excel `Owner` -> `tasks.owner_user_id`
- Excel `PIC` -> `tasks.pic_user_id`
- Excel `Deadline` -> `tasks.deadline`
- Excel `Status 1` -> `tasks.manual_status`
- Excel `Update Detail` -> latest `task_updates` entry or `tasks.latest_update_summary`
- Excel `Reason/Next Action` -> `tasks.next_action`

### 13.4 Phase Parsing Rule
- If pipeline title contains `Phase X`, split into:
  - base opportunity title
  - phase name
- Otherwise assign imported tasks into default phase `General`

### 13.5 Import Audit
- Save original row references for traceability.
- Surface unmapped or ambiguous rows in import report.

## 14. Non-Functional Requirements

### 14.1 Performance
- App cold start under 3 seconds on normal office laptop.
- Common filter response under 200 ms on dataset under 10,000 tasks.

### 14.2 Reliability
- Local autosave on every meaningful edit.
- Transactional writes for create/edit/import flows.
- Automatic backup snapshot on app version upgrade.

### 14.3 Security
- Data stored locally only by default.
- Optional local DB file encryption can be explored in future phase.
- No outbound network required for core operation.

### 14.4 Maintainability
- Typed schema and migrations required.
- Business rules isolated from UI components.
- Import logic covered by fixture-based tests.

## 15. Validation And Business Rules

### 15.1 Opportunity Rules
- Title is required.
- Pipeline status is required.
- Priority stage is required.

### 15.2 Phase Rules
- Phase name is required.
- Phase order must be unique within one opportunity.

### 15.3 Task Rules
- Title is required.
- Phase is required.
- Deadline may be blank.
- If manual status becomes `Completed`, set `completed_at`.
- If deadline is removed, recompute health status immediately.

## 16. Telemetry And Diagnostics

### 16.1 V1
- No external analytics by default.
- Local diagnostic log for import failures and unexpected app errors.

### 16.2 Error Handling
- User-friendly error banners.
- Recoverable actions should offer retry.
- Import failures should produce row-level explanation.

## 17. Testing Strategy

### 17.1 Unit Tests
- status computation
- phase parsing
- import mapping
- validation schemas

### 17.2 Integration Tests
- create opportunity with default phase
- reorder phases
- create task and update status
- Excel import against sample workbook

### 17.3 End-To-End Tests
- first-run import flow
- dashboard overdue workflow
- drag task across board columns

## 18. MVP Definition

### 18.1 MVP In Scope
- local workspace
- user directory
- opportunity CRUD
- phase CRUD and reorder
- task CRUD
- dashboard
- opportunity list
- opportunity detail
- task board
- Excel import
- local settings for taxonomy

### 18.2 Post-MVP
- calendar enhancements
- export to formatted Excel
- reminders and notifications
- attachment support
- richer analytics
- optional sync

## 19. Delivery Roadmap

### Phase 1: Foundation
- set up Tauri app shell
- define database schema
- implement taxonomy and user settings
- seed design system tokens

### Phase 2: Core Workflow
- opportunity list
- opportunity detail
- phase management
- task CRUD
- health status logic

### Phase 3: Productivity
- dashboard
- task board
- saved filters
- activity timeline

### Phase 4: Migration And Hardening
- Excel import
- diagnostics
- backup flow
- test coverage and performance tuning

## 20. Risks And Mitigations

### 20.1 Import Ambiguity
- Risk:
  - Excel structure is inconsistent in blank/merged rows
- Mitigation:
  - build preview and import report instead of silent import

### 20.2 Over-Complex V1
- Risk:
  - too many views and features may delay a working release
- Mitigation:
  - strict MVP with dashboard, list, detail, board only

### 20.3 Taxonomy Drift
- Risk:
  - pipeline and stage labels may change over time
- Mitigation:
  - configurable lookup tables in settings

## 21. Internal Review: Technical Perspective

### 21.1 Findings
1. If `health_status` is stored directly as mutable data, it will drift from deadline and manual status over time.
2. Importing Excel without a preview step is too risky because merged-cell logic is inconsistent.
3. Hard-coding pipeline labels would create future migration pain.
4. Putting too much business logic in React components would make testing fragile.
5. Export should not be part of MVP if import and core CRUD are still new.
6. `Calendar` was originally described as core navigation but was not included in MVP scope.

### 21.2 Resolutions Applied To This Spec
- `health_status` defined as computed status.
- import preview and audit added as required flow.
- taxonomy moved to settings-driven model.
- layered architecture included.
- export moved to post-MVP or later-phase scope.
- calendar moved to explicit post-MVP status to keep scope consistent.

## 22. Internal Review: UI/UX Perspective

### 22.1 Findings
1. A gradient-heavy interface could hurt readability if used behind dense data tables.
2. A kanban board alone is not enough for this workflow because the user also needs hierarchical context by opportunity and phase.
3. Task detail should not force full-page navigation because frequent edits need low-friction context.
4. Color-only status communication would create accessibility and scan issues.
5. If the app uses too many modals, daily task updates will feel slower than Excel.

### 22.2 Resolutions Applied To This Spec
- gradients limited to hero/header/accent zones, not primary data surfaces.
- opportunity detail view remains the core screen, with board as secondary execution view.
- task detail specified as drawer for quick edits.
- badges require label + color.
- inline editing prioritized over modal-heavy flows.

## 23. Finalized Recommendations

### 23.1 Build Recommendation
- Proceed with `Tauri + React + TypeScript + SQLite + Drizzle`.

### 23.2 MVP Recommendation
- Start with:
  - Excel import
  - opportunity detail with phase/task hierarchy
  - dashboard for overdue follow-up
  - task board for execution

### 23.3 Design Recommendation
- Use the supplied purple-to-lilac palette as brand atmosphere, but keep data work surfaces bright and neutral.
- Make opportunity detail the signature screen of the product.

### 23.4 Implementation Recommendation
- Treat this document as the baseline build spec.
- Next deliverables should be:
  - wireframes
  - database ERD
  - implementation plan by milestone
