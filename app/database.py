import sqlite3
from contextlib import contextmanager
from pathlib import Path
from shutil import copy2

from app.constants import BUNDLED_DB_PATH, DB_PATH, MASTER_DEFAULTS


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL UNIQUE,
    email TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    color_seed TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    department_name TEXT,
    company_name TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, department_name)
);

CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    department_name TEXT,
    external_pic_id INTEGER,
    pipeline_status TEXT NOT NULL,
    priority_stage TEXT NOT NULL,
    detail TEXT,
    account_year TEXT,
    tags TEXT,
    source_row_ref TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    archived_at TEXT,
    FOREIGN KEY (external_pic_id) REFERENCES contacts(id)
);

CREATE TABLE IF NOT EXISTS phases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    order_index INTEGER NOT NULL DEFAULT 0,
    phase_status TEXT,
    planned_start_date TEXT,
    planned_end_date TEXT,
    actual_end_date TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    archived_at TEXT,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE,
    UNIQUE(opportunity_id, name, phase_status)
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL,
    phase_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    owner_user_id INTEGER,
    pic_user_id INTEGER,
    manual_status TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'Normal',
    deadline TEXT,
    completed_at TEXT,
    next_action TEXT,
    latest_update_summary TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    source_row_ref TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    archived_at TEXT,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE,
    FOREIGN KEY (phase_id) REFERENCES phases(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_user_id) REFERENCES users(id),
    FOREIGN KEY (pic_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS task_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    author_user_id INTEGER,
    entry_type TEXT NOT NULL DEFAULT 'note',
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (author_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    opportunities_created INTEGER NOT NULL DEFAULT 0,
    phases_created INTEGER NOT NULL DEFAULT 0,
    tasks_created INTEGER NOT NULL DEFAULT 0,
    skipped_rows INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS master_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    value TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    archived_at TEXT,
    UNIQUE(category, value)
);
"""


class DatabaseManager:
    def __init__(self, db_path: Path | None = None):
        self.db_path = Path(db_path or DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.seed_db_path = Path(BUNDLED_DB_PATH)

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        self._seed_if_needed()
        with self.connection() as conn:
            conn.executescript(SCHEMA)
            self._migrate_phases_table(conn)
            self._seed_master_values(conn)

    def exists(self) -> bool:
        return self.db_path.exists()

    def _seed_if_needed(self) -> None:
        if self.db_path.exists():
            return
        if not self.seed_db_path.exists():
            return
        if self.seed_db_path.resolve() == self.db_path.resolve():
            return
        copy2(self.seed_db_path, self.db_path)

    def _seed_master_values(self, conn) -> None:
        for category, values in MASTER_DEFAULTS.items():
            for index, value in enumerate(values, start=1):
                conn.execute(
                    """
                    INSERT OR IGNORE INTO master_values (category, value, sort_order, is_active)
                    VALUES (?, ?, ?, 1)
                    """,
                    (category, value, index),
                )

    def _migrate_phases_table(self, conn) -> None:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'phases'"
        ).fetchone()
        if not row or "UNIQUE(opportunity_id, name, phase_status)" in (row["sql"] or ""):
            return
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute("ALTER TABLE phases RENAME TO phases_legacy")
        conn.execute(
            """
            CREATE TABLE phases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                order_index INTEGER NOT NULL DEFAULT 0,
                phase_status TEXT,
                planned_start_date TEXT,
                planned_end_date TEXT,
                actual_end_date TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                archived_at TEXT,
                FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE,
                UNIQUE(opportunity_id, name, phase_status)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO phases (
                id, opportunity_id, name, description, order_index, phase_status,
                planned_start_date, planned_end_date, actual_end_date, created_at, archived_at
            )
            SELECT
                id, opportunity_id, name, description, order_index, phase_status,
                planned_start_date, planned_end_date, actual_end_date, created_at, archived_at
            FROM phases_legacy
            """
        )
        conn.execute("DROP TABLE phases_legacy")
        conn.execute("PRAGMA foreign_keys = ON;")
