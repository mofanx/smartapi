"""定时任务调度 API"""

from __future__ import annotations

from typing import Optional

from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from smartapi.scheduler import job_scheduler
from smartapi.web.state import app_state

router = APIRouter()


class ScheduleCreateRequest(BaseModel):
    name: str
    cron: str
    file: str
    environment: Optional[str] = None
    project_id: Optional[str] = None
    enabled: bool = True


class ScheduleUpdateRequest(BaseModel):
    name: Optional[str] = None
    cron: Optional[str] = None
    file: Optional[str] = None
    environment: Optional[str] = None
    enabled: Optional[bool] = None


def _validate_cron(cron: str) -> None:
    try:
        CronTrigger.from_crontab(cron)
    except Exception as e:
        raise HTTPException(422, f"CRON 表达式无效: {cron}, 错误: {e}")


@router.get("")
async def list_schedules(enabled_only: bool = False):
    """列出定时任务"""
    schedules = app_state.list_schedules(enabled_only=enabled_only)
    return {"total": len(schedules), "schedules": schedules}


@router.post("")
async def create_schedule(req: ScheduleCreateRequest):
    """创建定时任务"""
    _validate_cron(req.cron)

    case_file = app_state.testcase_dir / req.file
    if not case_file.exists():
        raise HTTPException(404, f"用例文件不存在: {req.file}")

    schedule = app_state.create_schedule(
        name=req.name,
        cron=req.cron,
        file=req.file,
        environment=req.environment,
        project_id=req.project_id,
        enabled=req.enabled,
    )

    if req.enabled:
        job_scheduler.add_schedule(schedule)

    app_state.audit("schedule.create", resource=schedule["id"], detail=req.name)
    return {"message": "定时任务创建成功", "schedule": schedule}


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: str):
    """获取定时任务详情"""
    schedule = app_state.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(404, f"定时任务不存在: {schedule_id}")
    return schedule


@router.put("/{schedule_id}")
async def update_schedule(schedule_id: str, req: ScheduleUpdateRequest):
    """更新定时任务"""
    schedule = app_state.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(404, f"定时任务不存在: {schedule_id}")

    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.cron is not None:
        _validate_cron(req.cron)
        updates["cron"] = req.cron
    if req.file is not None:
        case_file = app_state.testcase_dir / req.file
        if not case_file.exists():
            raise HTTPException(404, f"用例文件不存在: {req.file}")
        updates["file"] = req.file
    if req.environment is not None:
        updates["environment"] = req.environment
    if req.enabled is not None:
        updates["enabled"] = req.enabled

    if not updates:
        return {"message": "没有更新内容", "schedule": schedule}

    app_state.update_schedule(schedule_id, **updates)
    updated = app_state.get_schedule(schedule_id)
    job_scheduler.update_schedule_job(updated)

    app_state.audit("schedule.update", resource=schedule_id, detail=str(updates))
    return {"message": "定时任务更新成功", "schedule": updated}


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str):
    """删除定时任务"""
    schedule = app_state.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(404, f"定时任务不存在: {schedule_id}")

    job_scheduler.remove_schedule(schedule_id)
    app_state.delete_schedule(schedule_id)
    app_state.audit("schedule.delete", resource=schedule_id)
    return {"message": "定时任务删除成功"}


@router.post("/{schedule_id}/run-now")
async def run_schedule_now(schedule_id: str):
    """立即执行一次定时任务"""
    schedule = app_state.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(404, f"定时任务不存在: {schedule_id}")

    from smartapi.web.routers.execution import _execute_case_background

    case_file = app_state.testcase_dir / schedule["file"]
    if not case_file.exists():
        raise HTTPException(404, f"用例文件不存在: {schedule['file']}")

    record = app_state.new_execution(schedule["file"], project_id=schedule.get("project_id"))
    from fastapi import BackgroundTasks

    # 使用后台任务立即执行
    # 注意：由于路由不能返回 BackgroundTasks 对象，这里直接在线程中启动
    import threading

    def _run():
        _execute_case_background(
            record.id,
            str(case_file),
            schedule.get("environment"),
            None,
            30.0,
            {},
        )

    threading.Thread(target=_run, daemon=True).start()
    app_state.audit("schedule.run_now", resource=schedule_id)
    return {"message": "任务已立即触发", "execution_id": record.id}
