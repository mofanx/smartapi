"""报告管理 API"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

from smartapi.core.models import TestCaseResult
from smartapi.report.html_report import HtmlReportGenerator
from smartapi.web.state import app_state

router = APIRouter()


@router.get("")
async def list_reports():
    """列出所有报告"""
    report_dir = app_state.report_dir
    if not report_dir.exists():
        return {"total": 0, "reports": []}

    reports = []
    for f in sorted(report_dir.glob("*.html"), reverse=True):
        stat = f.stat()
        reports.append({
            "file": f.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
        })

    return {"total": len(reports), "reports": reports}


@router.get("/view/{file_name}")
async def view_report(file_name: str):
    """查看 HTML 报告"""
    report_file = app_state.report_dir / file_name
    if not report_file.exists():
        raise HTTPException(404, f"报告不存在: {file_name}")

    content = report_file.read_text(encoding="utf-8")
    return HTMLResponse(content)


@router.get("/download/{file_name}")
async def download_report(file_name: str):
    """下载报告文件"""
    report_file = app_state.report_dir / file_name
    if not report_file.exists():
        raise HTTPException(404, f"报告不存在: {file_name}")

    return FileResponse(
        path=str(report_file),
        filename=file_name,
        media_type="text/html",
    )


@router.post("/generate/{execution_id}")
async def generate_report(execution_id: str):
    """从执行结果生成 HTML 报告"""
    record = app_state.get_execution(execution_id)
    if not record:
        raise HTTPException(404, f"执行记录不存在: {execution_id}")

    if not record.result:
        raise HTTPException(400, "执行尚未完成或无结果")

    generator = HtmlReportGenerator(title=f"执行: {record.case_file}")

    for case_data in record.result.get("cases", []):
        case_result = TestCaseResult.model_validate(case_data)
        generator.add_result(case_result)

    report_name = f"report_{execution_id}.html"
    output_path = app_state.report_dir / report_name
    generator.generate(output_path)

    return {"message": "报告生成成功", "file": report_name, "path": str(output_path)}


@router.delete("/{file_name}")
async def delete_report(file_name: str):
    """删除报告"""
    report_file = app_state.report_dir / file_name
    if not report_file.exists():
        raise HTTPException(404, f"报告不存在: {file_name}")

    report_file.unlink()
    return {"message": "删除成功"}


@router.get("/summary")
async def execution_summary():
    """执行结果汇总统计"""
    records = app_state.list_executions(limit=1000)

    total_executions = len(records)
    completed = [r for r in records if r["status"] == "completed"]
    failed_records = [r for r in records if r["status"] == "failed"]

    total_cases = 0
    passed_cases = 0
    failed_cases = 0
    total_time = 0

    for r in records:
        if r.get("result"):
            total_cases += r["result"].get("total", 0)
            passed_cases += r["result"].get("passed", 0)
            failed_cases += r["result"].get("failed", 0)

    return {
        "total_executions": total_executions,
        "completed": len(completed),
        "failed": len(failed_records),
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "pass_rate": round(passed_cases / total_cases * 100, 1) if total_cases else 0,
    }
