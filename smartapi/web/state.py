"""全局应用状态管理"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from smartapi.core.parser import TestCaseParser
from smartapi.core.variables import VariableManager
from smartapi.mock.data_factory import DataFactory
from smartapi.plugins.base import PluginManager


class ExecutionRecord:
    """执行记录"""

    def __init__(self, execution_id: str, case_file: str, status: str = "pending"):
        self.id = execution_id
        self.case_file = case_file
        self.status = status  # pending / running / completed / failed
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.result: Optional[dict] = None
        self.error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
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
        self.executions: dict[str, ExecutionRecord] = {}
        self._lock = threading.Lock()

    def initialize(self):
        """初始化目录"""
        for d in [self.testcase_dir, self.env_dir, self.report_dir, self.mock_dir]:
            d.mkdir(parents=True, exist_ok=True)
        logger.info("SmartAPI-Test Web 服务已初始化")

    def cleanup(self):
        logger.info("SmartAPI-Test Web 服务已关闭")

    def new_execution(self, case_file: str) -> ExecutionRecord:
        """创建新的执行记录"""
        exec_id = uuid.uuid4().hex[:12]
        record = ExecutionRecord(exec_id, case_file)
        with self._lock:
            self.executions[exec_id] = record
        return record

    def get_execution(self, exec_id: str) -> Optional[ExecutionRecord]:
        return self.executions.get(exec_id)

    def list_executions(self, limit: int = 50) -> list[dict]:
        records = sorted(self.executions.values(), key=lambda r: r.started_at or datetime.min, reverse=True)
        return [r.to_dict() for r in records[:limit]]


# 全局单例
app_state = AppState()
