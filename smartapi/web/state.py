"""全局应用状态管理 - 持久化版本

原内存中的执行记录已迁移到 SQLite，支持跨重启保留。
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from smartapi.core.parser import TestCaseParser
from smartapi.core.variables import VariableManager
from smartapi.mock.data_factory import DataFactory
from smartapi.plugins.base import PluginManager
from smartapi.scheduler import job_scheduler
from smartapi.web import database as db


class ExecutionRecord:
    """执行记录包装器，每次状态变更自动写库"""

    def __init__(
        self,
        state: "AppState",
        execution_id: str,
        case_file: str,
        project_id: Optional[str] = None,
        status: str = "pending",
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ):
        self._state = state
        self.id = execution_id
        self.case_file = case_file
        self.project_id = project_id
        self.status = status
        self.started_at = started_at
        self.finished_at = finished_at
        self.result = result
        self.error = error

    def _serialize_dt(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    def _save(self) -> None:
        db.update_execution(
            self._state.db,
            self.id,
            project_id=self.project_id,
            case_file=self.case_file,
            status=self.status,
            started_at=self._serialize_dt(self.started_at),
            finished_at=self._serialize_dt(self.finished_at),
            result=self.result,
            error=self.error,
        )

    def start(self) -> None:
        self.status = "running"
        self.started_at = datetime.now()
        self._save()

    def complete(self, result: dict) -> None:
        """完成用例执行，自动根据通过数判定状态"""
        total = result.get("total", 0)
        passed = result.get("passed", 0)
        self.status = "completed" if total > 0 and passed == total else "failed"
        self.result = result
        self.finished_at = datetime.now()
        self._save()

    def fail(self, error: str) -> None:
        self.status = "failed"
        self.error = error
        self.finished_at = datetime.now()
        self._save()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "case_file": self.case_file,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "result": self.result,
            "error": self.error,
        }


class AppState:
    """应用全局状态"""

    def __init__(self):
        self.testcase_dir = Path("testcases")
        self.env_dir = Path("environments")
        self.report_dir = Path("reports")
        self.mock_dir = Path("mock")
        self.variable_manager = VariableManager()
        self.data_factory = DataFactory()
        self.plugin_manager = PluginManager()
        self.db = db.Database()

    def initialize(self):
        """初始化目录与数据库"""
        for d in [self.testcase_dir, self.env_dir, self.report_dir, self.mock_dir]:
            d.mkdir(parents=True, exist_ok=True)
        self.db.init()
        # 确保存在一个默认项目，方便旧接口无缝迁移
        if not db.get_project(self.db, "default"):
            db.create_project(
                self.db,
                project_id="default",
                name="default",
                description="默认项目",
                base_path=".",
            )
        logger.info("SmartAPI-Test Web 服务已初始化")
        try:
            job_scheduler.start()
        except Exception as e:
            logger.error(f"启动调度器失败: {e}")

    def cleanup(self):
        try:
            job_scheduler.stop()
        except Exception as e:
            logger.error(f"关闭调度器失败: {e}")
        logger.info("SmartAPI-Test Web 服务已关闭")

    def new_execution(self, case_file: str, project_id: Optional[str] = None) -> ExecutionRecord:
        """创建新的执行记录"""
        if project_id is None:
            project_id = "default"
        exec_id = uuid.uuid4().hex[:12]
        db.create_execution(self.db, exec_id, case_file, project_id=project_id, status="pending")
        return ExecutionRecord(self, exec_id, case_file, project_id=project_id)

    def get_execution(self, exec_id: str) -> Optional[ExecutionRecord]:
        data = db.get_execution(self.db, exec_id)
        if not data:
            return None
        return ExecutionRecord(
            self,
            data["id"],
            data["case_file"],
            project_id=data.get("project_id"),
            status=data["status"],
            started_at=datetime.fromisoformat(data["started_at"]) if data["started_at"] else None,
            finished_at=datetime.fromisoformat(data["finished_at"]) if data["finished_at"] else None,
            result=data["result"],
            error=data["error"],
        )

    def list_executions(self, limit: int = 50, project_id: Optional[str] = None, status: Optional[str] = None) -> list[dict]:
        records = db.list_executions(self.db, limit=limit, project_id=project_id, status=status)
        return records

    # --- 项目操作 ---

    def create_project(self, name: str, description: str = "", base_path: str = ".") -> dict:
        project_id = secrets.token_hex(6)
        return db.create_project(self.db, project_id, name, description, base_path)

    def get_project(self, project_id: str) -> Optional[dict]:
        return db.get_project(self.db, project_id)

    def list_projects(self) -> list[dict]:
        return db.list_projects(self.db)

    def delete_project(self, project_id: str) -> bool:
        if project_id == "default":
            return False
        return db.delete_project(self.db, project_id)

    # --- 调度操作 ---

    def create_schedule(
        self,
        name: str,
        cron: str,
        file: str,
        environment: Optional[str] = None,
        project_id: Optional[str] = None,
        enabled: bool = True,
    ) -> dict:
        schedule_id = secrets.token_hex(6)
        return db.create_schedule(
            self.db,
            schedule_id,
            name,
            cron,
            file,
            environment=environment,
            project_id=project_id or "default",
            enabled=enabled,
        )

    def get_schedule(self, schedule_id: str) -> Optional[dict]:
        return db.get_schedule(self.db, schedule_id)

    def list_schedules(self, enabled_only: bool = False) -> list[dict]:
        return db.list_schedules(self.db, enabled_only=enabled_only)

    def update_schedule(self, schedule_id: str, **fields: Any) -> bool:
        return db.update_schedule(self.db, schedule_id, **fields)

    def delete_schedule(self, schedule_id: str) -> bool:
        return db.delete_schedule(self.db, schedule_id)

    # --- 审计日志 ---

    def audit(self, action: str, user: Optional[str] = None, resource: Optional[str] = None, detail: Optional[str] = None) -> None:
        db.create_audit_log(self.db, action, user=user, resource=resource, detail=detail)


# 全局单例
app_state = AppState()
