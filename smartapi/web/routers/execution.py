"""执行管理 API"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from smartapi.core.executor import TestExecutor
from smartapi.core.parser import TestCaseParser, ParserError
from smartapi.core.variables import VariableManager
from smartapi.web.state import app_state

router = APIRouter()


class RunRequest(BaseModel):
    file: str
    environment: Optional[str] = None
    base_url: Optional[str] = None
    tags: Optional[str] = None
    timeout: float = 30.0
    variables: dict = {}


class BatchRunRequest(BaseModel):
    files: list[str] = []
    directory: Optional[str] = None
    environment: Optional[str] = None
    base_url: Optional[str] = None
    tags: Optional[str] = None
    timeout: float = 30.0
    concurrency: int = 1


@router.post("/run")
async def run_case(req: RunRequest, background_tasks: BackgroundTasks):
    """执行单个测试用例（异步）"""
    case_file = app_state.testcase_dir / req.file
    if not case_file.exists():
        raise HTTPException(404, f"用例文件不存在: {req.file}")

    record = app_state.new_execution(req.file)

    background_tasks.add_task(
        _execute_case_background,
        record.id,
        str(case_file),
        req.environment,
        req.base_url,
        req.timeout,
        req.variables,
    )

    return {"execution_id": record.id, "status": "pending", "message": "执行已提交"}


@router.post("/run-sync")
async def run_case_sync(req: RunRequest):
    """同步执行测试用例（等待结果）"""
    case_file = app_state.testcase_dir / req.file
    if not case_file.exists():
        raise HTTPException(404, f"用例文件不存在: {req.file}")

    record = app_state.new_execution(req.file)

    _execute_case_background(
        record.id,
        str(case_file),
        req.environment,
        req.base_url,
        req.timeout,
        req.variables,
    )

    return record.to_dict()


@router.post("/batch")
async def batch_run(req: BatchRunRequest, background_tasks: BackgroundTasks):
    """批量执行测试用例"""
    files = []

    if req.files:
        for f in req.files:
            fp = app_state.testcase_dir / f
            if fp.exists():
                files.append(fp)
    elif req.directory:
        dir_path = app_state.testcase_dir / req.directory
        if dir_path.is_dir():
            try:
                files = TestCaseParser.discover_test_files(dir_path)
            except Exception:
                pass
    else:
        try:
            files = TestCaseParser.discover_test_files(app_state.testcase_dir)
        except Exception:
            pass

    if not files:
        raise HTTPException(400, "未找到测试用例文件")

    execution_ids = []
    for f in files:
        rel_path = str(f.relative_to(app_state.testcase_dir))
        record = app_state.new_execution(rel_path)
        execution_ids.append(record.id)

        background_tasks.add_task(
            _execute_case_background,
            record.id,
            str(f),
            req.environment,
            req.base_url,
            req.timeout,
            {},
        )

    return {
        "message": f"已提交 {len(execution_ids)} 个用例执行",
        "execution_ids": execution_ids,
    }


@router.get("/status/{execution_id}")
async def get_execution_status(execution_id: str):
    """查询执行状态"""
    record = app_state.get_execution(execution_id)
    if not record:
        raise HTTPException(404, f"执行记录不存在: {execution_id}")
    return record.to_dict()


@router.get("/history")
async def execution_history(
    limit: int = Query(50, ge=1, le=500),
    status: Optional[str] = Query(None, description="筛选状态: pending/running/completed/failed"),
):
    """执行历史"""
    records = app_state.list_executions(limit=limit)
    if status:
        records = [r for r in records if r["status"] == status]
    return {"total": len(records), "records": records}


def _execute_case_background(
    exec_id: str,
    case_file: str,
    environment: Optional[str],
    base_url: Optional[str],
    timeout: float,
    extra_variables: dict,
):
    """后台执行用例"""
    record = app_state.get_execution(exec_id)
    if not record:
        return

    record.status = "running"
    record.started_at = datetime.now()

    var_manager = VariableManager()

    # 加载环境配置
    if environment:
        for ext in (".yaml", ".yml"):
            env_path = app_state.env_dir / f"{environment}{ext}"
            if env_path.exists():
                try:
                    env_config = TestCaseParser.load_environment(env_path)
                    var_manager.set_env_vars(env_config.variables)
                    if not base_url:
                        base_url = env_config.base_url
                except Exception:
                    pass
                break

    if extra_variables:
        var_manager.set_global_vars(extra_variables)

    try:
        data = TestCaseParser.load_file(case_file)

        cases = []
        if "test_cases" in data:
            suite = TestCaseParser.parse_test_suite(data)
            if suite.variables:
                var_manager.set_global_vars(suite.variables)
            cases = suite.test_cases
        elif "steps" in data:
            cases = [TestCaseParser.parse_test_case(data)]

        results = []
        executor = TestExecutor(
            variable_manager=var_manager,
            base_url=base_url or "",
            timeout=timeout,
        )

        try:
            for case in cases:
                case_result = executor.execute_test_case(case)
                results.append(case_result.model_dump())
        finally:
            executor.close()

        total = len(results)
        passed = sum(1 for r in results if r["success"])

        record.result = {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total * 100, 1) if total else 0,
            "cases": results,
        }
        record.status = "completed" if passed == total else "failed"

    except Exception as e:
        record.status = "failed"
        record.error = str(e)

    record.finished_at = datetime.now()
