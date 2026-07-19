"""定时任务调度器 - 基于 APScheduler"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger


class JobScheduler:
    """后台任务调度器"""

    def __init__(self):
        self._scheduler = BackgroundScheduler()

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()
            self.reload_schedules()
            logger.info("定时任务调度器已启动")

    def stop(self) -> None:
        try:
            self._scheduler.shutdown(wait=False)
            logger.info("定时任务调度器已关闭")
        except Exception as e:
            logger.warning(f"关闭调度器失败: {e}")

    def reload_schedules(self) -> None:
        """从数据库重新加载所有启用状态的定时任务"""
        self._scheduler.remove_all_jobs()
        # 延迟导入避免循环依赖
        from smartapi.web.state import app_state

        for schedule in app_state.list_schedules(enabled_only=True):
            self.add_schedule(schedule, save=False)

    def add_schedule(self, schedule: dict, save: bool = True) -> None:
        """向调度器添加/更新一个任务"""
        schedule_id = schedule["id"]
        cron = schedule.get("cron")
        file = schedule.get("file")
        environment = schedule.get("environment")

        if not cron or not file:
            logger.warning(f"定时任务 {schedule_id} 缺少 cron 或 file，跳过")
            return

        try:
            trigger = CronTrigger.from_crontab(cron)
            self._scheduler.add_job(
                _run_scheduled_case,
                trigger=trigger,
                id=schedule_id,
                replace_existing=True,
                args=(schedule_id, file, environment),
            )
            logger.info(f"定时任务已加入调度: {schedule.get('name', schedule_id)} ({cron})")
        except Exception as e:
            logger.error(f"添加定时任务失败 {schedule_id}: {e}")

    def remove_schedule(self, schedule_id: str) -> None:
        try:
            self._scheduler.remove_job(schedule_id)
        except Exception:
            pass

    def update_schedule_job(self, schedule: dict) -> None:
        """更新或重新启用任务"""
        self.remove_schedule(schedule["id"])
        if schedule.get("enabled", True):
            self.add_schedule(schedule)


def _run_scheduled_case(schedule_id: str, file: str, environment: Optional[str]) -> None:
    """定时任务执行入口"""
    # 延迟导入避免循环依赖
    from smartapi.web.routers.execution import _execute_case_background
    from smartapi.web.state import app_state

    case_file = app_state.testcase_dir / file
    if not case_file.exists():
        logger.error(f"定时任务 {schedule_id} 对应用例不存在: {case_file}")
        app_state.update_schedule(schedule_id, last_run_at=datetime.now().isoformat())
        return

    record = app_state.new_execution(file)
    app_state.update_schedule(schedule_id, last_run_at=datetime.now().isoformat())
    _execute_case_background(
        record.id,
        str(case_file),
        environment,
        None,
        30.0,
        {},
    )


# 全局单例
job_scheduler = JobScheduler()
