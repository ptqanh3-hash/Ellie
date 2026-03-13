- [x] Restate goal + acceptance criteria
- [x] Locate existing implementation / patterns
- [x] Design: minimal approach + key decisions
- [x] Implement Opportunities multi-stage-status view
- [x] Add/adjust regression checks
- [x] Run verification (compile/UAT/manual repro/build)
- [x] Summarize changes + verification story
- [x] Record lessons (if any)

Acceptance Criteria
- In `Opportunities`, users can view multiple `stage-status` pairs at the same time under a single opportunity.
- Each `stage-status` pair renders as its own task cluster, all under the same parent opportunity.
- There is a clear `Add Stage-Status` flow.
- Existing stage/task CRUD still works and tasks remain attached to exactly one stage-status pair.
- Existing flows still work: import, create opportunity/stage/task, dashboard, task board status update, local SQLite persistence.

Working Notes
- Keep the data model unchanged from the previous stage-container implementation.
- Change only Opportunities rendering/interaction from single-stage selector to multi-stage sections.
- Keep `selected_stage_id` for actions, but remove the UI dependency on viewing one stage at a time.
- Build output should still end up outside the repo root at `..\\Ellie.exe`.

Results
- Reworked `Opportunities` so all stage-status pairs render together as separate task clusters under one opportunity instead of a single-stage selector.
- Added clearer `Add Stage-Status` wording while keeping existing stage/task CRUD behavior intact.
- Kept the current data model and selection logic, using `selected_stage_id` only for actions and highlight state.
- Verified with `py_compile`, `tests/run_uat.py` (`19/19` pass), GUI smoke check, and a rebuilt external release at `..\\Ellie.exe`.
