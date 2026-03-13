- [x] Restate goal + acceptance criteria
- [x] Locate existing implementation / patterns
- [x] Design: minimal approach + key decisions
- [x] Implement service updates for stage-status management
- [x] Implement UI updates to manage tasks by stage instead of phase
- [x] Add/adjust regression checks
- [x] Run verification (compile/UAT/manual repro/build)
- [x] Summarize changes + verification story
- [x] Record lessons (if any)

Acceptance Criteria
- In `Opportunities`, tasks are grouped and managed by `stage + status`, not by `phase`.
- Each opportunity can contain multiple stage containers, and each stage container shows both `stage` and `status`.
- Creating and editing a stage lets the user choose both stage name and stage status.
- Creating and editing a task attaches it to a selected stage container.
- Existing imported data remains viewable by mapping old phases into stage containers without destructive migration.
- Existing flows still work: import, create opportunity/stage/task, dashboard, task board status update, local SQLite persistence.

Working Notes
- Keep changes incremental and avoid destructive schema changes if current `phases` table can serve as stage container.
- Reuse `phases.phase_status` as the status of each stage container.
- Treat old `phase.name` as `stage name` for backward compatibility.
- Build output should still end up outside the repo root at `..\\Ellie.exe`.

Results
- Reused the existing `phases` table as the opportunity stage container and activated `phase_status` as the per-stage status field.
- Updated the opportunities UI to manage tasks by `stage + status`, including create/edit/delete stage flows and stage-aware task assignment.
- Preserved backward compatibility for imported data by mapping old phases into stages rather than doing a destructive schema migration.
- Verified with `py_compile`, `tests/run_uat.py` (`19/19` pass), GUI smoke check, and a rebuilt external release at `..\\Ellie.exe`.
