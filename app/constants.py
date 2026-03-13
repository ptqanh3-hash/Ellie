import sys
from pathlib import Path


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parents[1]
    RESOURCE_DIR = BASE_DIR

DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "taskmng.db"
BUNDLED_DB_PATH = RESOURCE_DIR / "data" / "taskmng.db"
APP_NAME = "Ellie"
APP_TITLE = "Ellie Desktop"
EXECUTABLE_NAME = "Ellie"
LOGO_FILE_NAME = "EliieAppN.png"
LOGO_PATH = BASE_DIR / "Logo" / LOGO_FILE_NAME
BUNDLED_LOGO_PATH = RESOURCE_DIR / "Logo" / LOGO_FILE_NAME
DEFAULT_SHEET_NAME = "Opt Manage_Task List"
DEFAULT_DUE_SOON_DAYS = 3

MASTER_CATEGORY_TASK_STATUS = "task_status"
MASTER_CATEGORY_PIPELINE_STATUS = "pipeline_status"
MASTER_CATEGORY_PRIORITY_STAGE = "priority_stage"

MANUAL_STATUSES = [
    "Not Started",
    "In Progress",
    "Blocked",
    "Completed",
    "Cancelled",
]

PIPELINE_STATUSES = ["TT", "Contract", "KT3"]
PRIORITY_STAGES = ["Approach", "PoC", "Bidding", "Pending", "Cancel"]
TASK_PRIORITIES = ["Low", "Normal", "High", "Critical"]

MASTER_DEFAULTS = {
    MASTER_CATEGORY_TASK_STATUS: MANUAL_STATUSES,
    MASTER_CATEGORY_PIPELINE_STATUS: PIPELINE_STATUSES,
    MASTER_CATEGORY_PRIORITY_STAGE: PRIORITY_STAGES,
}

PALETTE = {
    "primary_700": "#5C60E8",
    "primary_500": "#7B88F0",
    "secondary_300": "#B7AFE8",
    "accent_200": "#DFC2E2",
    "ink_900": "#1E2140",
    "ink_700": "#4B4F73",
    "surface_0": "#FCFBFF",
    "surface_1": "#F4F2FD",
    "surface_2": "#ECE8FA",
    "border_soft": "#D9D3F0",
    "success": "#2E9B72",
    "warning": "#F3A93B",
    "danger": "#D95F7A",
    "muted": "#8990B2",
}
