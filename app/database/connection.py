"""
SQLite Database Connection and Lifecycle Management.

Provides connection pooling, schema migrations, and context managers
for the local enterprise database.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Generator
from app.config import get_settings

SCHEMA_DDL = """
-- Employees Table
CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    department TEXT NOT NULL,
    role TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- Support Tickets Table
CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    resolution_notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees (employee_id) ON DELETE CASCADE
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_tickets_employee ON support_tickets (employee_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets (status);
CREATE INDEX IF NOT EXISTS idx_tickets_category ON support_tickets (category);
CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON support_tickets (created_at);
CREATE INDEX IF NOT EXISTS idx_employees_department ON employees (department);
CREATE INDEX IF NOT EXISTS idx_employees_email ON employees (email);
"""


class DatabaseManager:
    """Manages SQLite database connections and lifecycle."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_settings().SQLITE_DB_PATH
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensures the parent directory for SQLite file exists (if not in-memory)."""
        if self.db_path != ":memory:":
            parent = Path(self.db_path).parent
            parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Creates and configures a new SQLite connection."""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=10.0,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """
        Transactional context manager.
        Yields cursor, commits on clean exit, and rolls back on exception.
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """Initializes database tables and indexes if they do not exist."""
        with self.cursor() as cur:
            cur.executescript(SCHEMA_DDL)


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Helper function to obtain an open SQLite connection."""
    manager = DatabaseManager(db_path)
    return manager.get_connection()


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes the database schema."""
    manager = DatabaseManager(db_path)
    manager.initialize()
