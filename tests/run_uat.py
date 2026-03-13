from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import DatabaseManager
from app.services.core import DashboardService, ExcelImportService, MasterDataService, OpportunityService, TaskService, ValidationError


def locate_workbook() -> Path:
    relative = Path(
        "1. WORK FY2026"
    ) / "1. ACCOUNT PLAN" / "FY2025" / "ITOUCHU TECHNO" / "1. BUSINESS PLAN" / "AM_Itouchu Techno- Solutions_CTC_2025~.xlsx"
    for base in Path.home().glob("OneDrive*"):
        candidate = base / relative
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Unable to locate source workbook in OneDrive.")


def run_case(case_id: str, title: str, fn):
    try:
        fn()
        print(f"[PASS] {case_id} - {title}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {case_id} - {title}: {exc}")
        return False


def assert_true(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def main():
    workbook_path = locate_workbook()
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "taskmng_uat.db"
        db = DatabaseManager(db_path)
        opportunity_service = OpportunityService(db)
        task_service = TaskService(db)
        dashboard_service = DashboardService(db)
        import_service = ExcelImportService(db)
        master_data_service = MasterDataService(db)

        state = {}

        def h01():
            db.initialize()
            assert_true(db.exists(), "Database file was not created.")

        def h02():
            report = import_service.import_workbook(workbook_path)
            state["import_report"] = report
            assert_true(report.opportunities_created > 0, "No opportunities were imported.")
            assert_true(report.phases_created > 0, "No stages were imported.")
            assert_true(report.tasks_created > 0, "No tasks were imported.")

        def h03():
            metrics = dashboard_service.metrics()
            state["baseline_metrics"] = metrics
            assert_true(metrics["opportunity_count"] > 0, "Dashboard opportunity count is empty after import.")
            assert_true(metrics["task_count"] > 0, "Dashboard task count is empty after import.")
            assert_true(metrics["overdue_count"] >= 0, "Overdue count should never be negative.")

        def h04():
            opportunity_id = opportunity_service.create_opportunity(
                title="UAT Opportunity",
                department_name="Delivery",
                pipeline_status="TT",
                priority_stage="Approach",
                detail="Created from UAT happy path.",
                external_pic_name="Demo PIC",
            )
            state["opportunity_id"] = opportunity_id
            detail = opportunity_service.get_opportunity_detail(opportunity_id)
            stage_names = [stage["stage_name"] for stage in detail["stages"]]
            assert_true("Approach" in stage_names, "Default stage was not created from the opportunity.")

        def h05():
            stage_id = opportunity_service.create_stage(state["opportunity_id"], "Phase UAT", "TT")
            state["phase_id"] = stage_id
            second_stage_id = opportunity_service.create_stage(state["opportunity_id"], "Phase UAT", "Contract")
            state["second_stage_id"] = second_stage_id
            detail = opportunity_service.get_opportunity_detail(state["opportunity_id"])
            stage_labels = {(stage["stage_name"], stage["stage_status"]) for stage in detail["stages"]}
            assert_true(("Phase UAT", "TT") in stage_labels, "New stage was not added.")
            assert_true(("Phase UAT", "Contract") in stage_labels, "Same stage name with a different status should be allowed.")

        def h06():
            task_id = task_service.create_task(
                opportunity_id=state["opportunity_id"],
                phase_id=state["phase_id"],
                title="Prepare proposal deck",
                owner_name="Ptqanh3",
                pic_name="Bqthanh",
                manual_status="In Progress",
                deadline="2099-12-31",
                next_action="Finalize customer-facing content",
                latest_update_summary="Task created during UAT run.",
            )
            state["task_id"] = task_id
            tasks = task_service.list_tasks()
            created = next((task for task in tasks if task["id"] == task_id), None)
            assert_true(created is not None, "New task was not created.")
            assert_true(created["manual_status"] == "In Progress", "Task status mismatch after creation.")

        def h07():
            task_service.update_task_status(state["task_id"], "Completed")
            tasks = task_service.list_tasks()
            updated = next(task for task in tasks if task["id"] == state["task_id"])
            assert_true(updated["manual_status"] == "Completed", "Task status did not change to Completed.")

        def h08():
            metrics = dashboard_service.metrics()
            assert_true(
                metrics["task_count"] >= state["baseline_metrics"]["task_count"] + 1,
                "Dashboard task count did not reflect newly added task.",
            )
            assert_true(any(task["id"] == state["task_id"] for task in metrics["recent_tasks"]), "Recent tasks did not refresh.")

        def h09():
            opportunity_service.update_opportunity(
                state["opportunity_id"],
                title="UAT Opportunity Updated",
                department_name="Delivery Excellence",
                pipeline_status="TT",
                priority_stage="Approach",
                detail="Updated from UAT happy path.",
                external_pic_name="Demo PIC",
            )
            detail = opportunity_service.get_opportunity_detail(state["opportunity_id"])
            assert_true(detail["opportunity"]["title"] == "UAT Opportunity Updated", "Opportunity title was not updated.")
            assert_true(detail["opportunity"]["department_name"] == "Delivery Excellence", "Opportunity department was not updated.")

        def h10():
            task_service.update_task(
                state["task_id"],
                phase_id=state["phase_id"],
                title="Prepare proposal deck v2",
                owner_name="Ptqanh3",
                pic_name="Bqthanh",
                manual_status="In Progress",
                deadline="2099-11-30",
                next_action="Review final structure",
                latest_update_summary="Edited during UAT run.",
            )
            task = task_service.get_task(state["task_id"])
            assert_true(task["title"] == "Prepare proposal deck v2", "Task title was not updated.")
            assert_true(task["manual_status"] == "In Progress", "Task status was not updated.")

        def h11():
            opportunity_service.update_stage(state["phase_id"], "Phase UAT Updated", "Contract")
            detail = opportunity_service.get_opportunity_detail(state["opportunity_id"])
            labels = {(stage["stage_name"], stage["stage_status"]) for stage in detail["stages"]}
            assert_true(("Phase UAT Updated", "Contract") in labels, "Stage update did not persist.")

        def h12():
            task_service.archive_task(state["task_id"])
            tasks = task_service.list_tasks()
            assert_true(all(task["id"] != state["task_id"] for task in tasks), "Archived task still appears in active task list.")

        def h13():
            status_id = master_data_service.add_value("task_status", "Waiting Review")
            stage_master_id = master_data_service.add_value("priority_stage", "Review Gate")
            custom_phase_id = opportunity_service.create_stage(state["opportunity_id"], "Review Gate", "TT")
            custom_task_id = task_service.create_task(
                opportunity_id=state["opportunity_id"],
                phase_id=custom_phase_id,
                title="Review package",
                manual_status="Waiting Review",
            )
            master_data_service.rename_value("task_status", status_id, "Reviewing")
            master_data_service.rename_value("priority_stage", stage_master_id, "Review Gate Final")
            updated_task = task_service.get_task(custom_task_id)
            detail = opportunity_service.get_opportunity_detail(state["opportunity_id"])
            stage_labels = {(stage["stage_name"], stage["stage_status"]) for stage in detail["stages"]}
            assert_true(updated_task["manual_status"] == "Reviewing", "Renaming task status did not propagate to tasks.")
            assert_true(("Review Gate Final", "TT") in stage_labels, "Renaming stage master data did not propagate to stages.")
            state["custom_task_id"] = custom_task_id

        def h14():
            opportunity_service.archive_opportunity(state["opportunity_id"])
            active_ids = {item["id"] for item in opportunity_service.list_opportunities()}
            assert_true(state["opportunity_id"] not in active_ids, "Archived opportunity still appears in active list.")

        def u01():
            before = dashboard_service.metrics()["opportunity_count"]
            try:
                import_service.import_workbook(Path(temp_dir) / "missing.xlsx")
            except ValidationError:
                after = dashboard_service.metrics()["opportunity_count"]
                assert_true(before == after, "Missing-path import changed database state.")
                return
            raise AssertionError("Missing-path import should fail.")

        def u02():
            try:
                opportunity_service.create_opportunity(
                    title="",
                    department_name="",
                    pipeline_status="TT",
                    priority_stage="Approach",
                )
            except ValidationError:
                return
            raise AssertionError("Opportunity validation should reject empty title.")

        def u03():
            try:
                task_service.create_task(
                    opportunity_id=state["opportunity_id"],
                    phase_id=state["phase_id"],
                    title="",
                )
            except ValidationError:
                return
            raise AssertionError("Task validation should reject empty title.")

        def u04():
            current = next(task for task in task_service.list_tasks() if task["id"] == state["task_id"])
            try:
                task_service.update_task_status(state["task_id"], "INVALID")
            except ValidationError:
                after = next(task for task in task_service.list_tasks() if task["id"] == state["task_id"])
                assert_true(after["manual_status"] == current["manual_status"], "Invalid status update changed the record.")
                return
            raise AssertionError("Invalid status should be rejected.")

        def u05():
            fresh_db = DatabaseManager(Path(temp_dir) / "taskmng_import_check.db")
            fresh_import = ExcelImportService(fresh_db)
            report = fresh_import.import_workbook(workbook_path)
            assert_true(report.tasks_created > 0, "Ambiguous-row workbook import should still create tasks.")
            assert_true(report.skipped_rows >= 0, "Skipped row count should be reported.")

        cases = [
            ("UAT-H01", "First launch creates local workspace", h01),
            ("UAT-H02", "Import Excel workbook into local database", h02),
            ("UAT-H03", "Dashboard shows imported metrics", h03),
            ("UAT-H04", "Create new opportunity with default stage", h04),
            ("UAT-H05", "Add new stage under existing opportunity", h05),
            ("UAT-H06", "Add task under selected stage", h06),
            ("UAT-H07", "Update task status from board/service flow", h07),
            ("UAT-H08", "Dashboard refresh reflects newly added task", h08),
            ("UAT-H09", "Edit opportunity details", h09),
            ("UAT-H10", "Edit task details", h10),
            ("UAT-H11", "Edit stage details", h11),
            ("UAT-U01", "Import rejects missing workbook path", u01),
            ("UAT-U02", "Opportunity save fails without required fields", u02),
            ("UAT-U03", "Task save fails without title", u03),
            ("UAT-U04", "Invalid status update is rejected", u04),
            ("UAT-U05", "Import handles ambiguous rows without crash", u05),
            ("UAT-H12", "Delete task from active workspace", h12),
            ("UAT-H13", "Rename task/stage master data and propagate", h13),
            ("UAT-H14", "Delete opportunity from active workspace", h14),
        ]

        results = [run_case(case_id, title, fn) for case_id, title, fn in cases]
        passed = sum(results)
        total = len(results)
        print(f"\nUAT summary: {passed}/{total} passed")
        return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
