"""SQLite 持久化层 - Web 后端数据持久化

当前使用 Python 内置 sqlite3，避免引入 SQLAlchemy 等重型依赖。
后续如需多并发/复杂迁移，可无缝替换为 SQLAlchemy + Alembic。
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from loguru import logger


DEFAULT_DB_PATH = Path(os.environ.get("SMARTAPI_DB_PATH", "data/smartapi.db"))


class Database:
    """SQLite 数据库连接封装"""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._local = threading.local()

    def _connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def execute(self, sql: str, params: tuple | dict = ()) -> sqlite3.Cursor:
        return self._connection().execute(sql, params)

    def executescript(self, sql: str) -> sqlite3.Cursor:
        return self._connection().executescript(sql)

    def commit(self) -> None:
        self._connection().commit()

    def init(self) -> None:
        """初始化所有表"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                base_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                case_file TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                started_at TEXT,
                finished_at TEXT,
                result TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_executions_status ON executions(status);
            CREATE INDEX IF NOT EXISTS idx_executions_created ON executions(created_at);

            CREATE TABLE IF NOT EXISTS schedules (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                name TEXT NOT NULL,
                cron TEXT,
                file TEXT,
                environment TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                last_run_at TEXT,
                next_run_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                user TEXT,
                action TEXT NOT NULL,
                resource TEXT,
                detail TEXT,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
            """
        )
        self.commit()
        logger.info(f"数据库已初始化: {self.db_path}")


# --- 通用序列化 ---

def _now() -> str:
    return datetime.now().isoformat()


def _to_json(value: Any) -> Optional[str]:
    return json.dumps(value, ensure_ascii=False, default=str) if value is not None else None


def _from_json(value: Optional[str]) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


# --- Execution DAO ---

def create_execution(
    db: Database,
    execution_id: str,
    case_file: str,
    project_id: Optional[str] = None,
    status: str = "pending",
) -> dict:
    created_at = _now()
    db.execute(
        "INSERT INTO executions (id, project_id, case_file, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (execution_id, project_id, case_file, status, created_at),
    )
    db.commit()
    return {
        "id": execution_id,
        "project_id": project_id,
        "case_file": case_file,
        "status": status,
        "started_at": None,
        "finished_at": None,
        "result": None,
        "error": None,
        "created_at": created_at,
    }


def get_execution(db: Database, execution_id: str) -> Optional[dict]:
    row = db.execute("SELECT * FROM executions WHERE id = ?", (execution_id,)).fetchone()
    if not row:
        return None
    return _execution_row_to_dict(row)


def update_execution(db: Database, execution_id: str, **fields: Any) -> None:
    if not fields:
        return
    allowed = {"case_file", "status", "started_at", "finished_at", "result", "error", "project_id"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if "result" in updates:
        updates["result"] = _to_json(updates["result"])
    if not updates:
        return
    sql = "UPDATE executions SET " + ", ".join(f"{k} = ?" for k in updates) + " WHERE id = ?"
    db.execute(sql, tuple(updates.values()) + (execution_id,))
    db.commit()


def list_executions(
    db: Database,
    limit: int = 50,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
) -> list[dict]:
    sql = "SELECT * FROM executions WHERE 1=1"
    params: list[Any] = []
    if project_id:
        sql += " AND project_id = ?"
        params.append(project_id)
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = db.execute(sql, tuple(params)).fetchall()
    return [_execution_row_to_dict(r) for r in rows]


def _execution_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "case_file": row["case_file"],
        "status": row["status"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "result": _from_json(row["result"]),
        "error": row["error"],
        "created_at": row["created_at"],
    }


# --- Project DAO ---

def create_project(db: Database, project_id: str, name: str, description: str, base_path: str) -> dict:
    now = _now()
    db.execute(
        "INSERT INTO projects (id, name, description, base_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (project_id, name, description, base_path, now, now),
    )
    db.commit()
    return {
        "id": project_id,
        "name": name,
        "description": description,
        "base_path": base_path,
        "created_at": now,
        "updated_at": now,
    }


def get_project(db: Database, project_id: str) -> Optional[dict]:
    row = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return dict(row) if row else None


def get_project_by_name(db: Database, name: str) -> Optional[dict]:
    row = db.execute("SELECT * FROM projects WHERE name = ?", (name,)).fetchone()
    return dict(row) if row else None


def list_projects(db: Database) -> list[dict]:
    rows = db.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def update_project(db: Database, project_id: str, **fields: Any) -> bool:
    allowed = {"name", "description", "base_path"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    sql = "UPDATE projects SET " + ", ".join(f"{k} = ?" for k in updates) + ", updated_at = ? WHERE id = ?"
    db.execute(sql, tuple(updates.values()) + (_now(), project_id))
    db.commit()
    return True


def delete_project(db: Database, project_id: str) -> bool:
    cur = db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    db.commit()
    return cur.rowcount > 0


# --- Schedule DAO ---

def create_schedule(
    db: Database,
    schedule_id: str,
    name: str,
    cron: str,
    file: str,
    environment: Optional[str] = None,
    project_id: Optional[str] = None,
    enabled: bool = True,
) -> dict:
    now = _now()
    db.execute(
        "INSERT INTO schedules (id, project_id, name, cron, file, environment, enabled, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (schedule_id, project_id, name, cron, file, environment, int(enabled), now, now),
    )
    db.commit()
    return {
        "id": schedule_id,
        "project_id": project_id,
        "name": name,
        "cron": cron,
        "file": file,
        "environment": environment,
        "enabled": enabled,
        "last_run_at": None,
        "next_run_at": None,
        "created_at": now,
        "updated_at": now,
    }


def get_schedule(db: Database, schedule_id: str) -> Optional[dict]:
    row = db.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
    return _schedule_row_to_dict(row) if row else None


def list_schedules(db: Database, enabled_only: bool = False) -> list[dict]:
    sql = "SELECT * FROM schedules"
    params: tuple = ()
    if enabled_only:
        sql += " WHERE enabled = 1"
    sql += " ORDER BY created_at DESC"
    rows = db.execute(sql, params).fetchall()
    return [_schedule_row_to_dict(r) for r in rows]


def update_schedule(db: Database, schedule_id: str, **fields: Any) -> bool:
    allowed = {"name", "cron", "file", "environment", "enabled", "last_run_at", "next_run_at", "project_id"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    if "enabled" in updates:
        updates["enabled"] = int(updates["enabled"])
    sql = "UPDATE schedules SET " + ", ".join(f"{k} = ?" for k in updates) + ", updated_at = ? WHERE id = ?"
    db.execute(sql, tuple(updates.values()) + (_now(), schedule_id))
    db.commit()
    return True


def delete_schedule(db: Database, schedule_id: str) -> bool:
    cur = db.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    db.commit()
    return cur.rowcount > 0


def _schedule_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "name": row["name"],
        "cron": row["cron"],
        "file": row["file"],
        "environment": row["environment"],
        "enabled": bool(row["enabled"]),
        "last_run_at": row["last_run_at"],
        "next_run_at": row["next_run_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# --- Audit Log DAO ---

def create_audit_log(db: Database, action: str, user: Optional[str] = None, resource: Optional[str] = None, detail: Optional[str] = None) -> None:
    log_id = _generate_id()
    db.execute(
        "INSERT INTO audit_logs (id, user, action, resource, detail, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (log_id, user, action, resource, detail, _now()),
    )
    db.commit()


def list_audit_logs(db: Database, limit: int = 100) -> list[dict]:
    rows = db.execute("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# --- utils ---

def _generate_id(length: int = 12) -> str:
    import secrets

    return secrets.token_hex(length // 2)
