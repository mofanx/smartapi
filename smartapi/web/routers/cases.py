"""用例管理 API"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel

from smartapi.core.parser import TestCaseParser, ParserError
from smartapi.web.state import app_state

router = APIRouter()


class CaseCreateRequest(BaseModel):
    filename: str
    content: str  # YAML 内容


class CaseUpdateRequest(BaseModel):
    content: str


class CaseValidateRequest(BaseModel):
    content: str


@router.get("")
async def list_cases(
    tags: Optional[str] = Query(None, description="按标签筛选(逗号分隔)"),
    priority: Optional[str] = Query(None, description="按优先级筛选"),
):
    """列出所有测试用例"""
    try:
        files = TestCaseParser.discover_test_files(app_state.testcase_dir)
    except Exception:
        files = []

    filter_tags = set()
    if tags:
        filter_tags = {t.strip() for t in tags.split(",")}

    cases = []
    for f in files:
        try:
            data = TestCaseParser.load_file(f)
            if "test_cases" in data:
                suite = TestCaseParser.parse_test_suite(data)
                for tc in suite.test_cases:
                    if filter_tags and not filter_tags.intersection(set(tc.tags)):
                        continue
                    if priority and tc.priority != priority:
                        continue
                    cases.append({
                        "file": str(f.relative_to(app_state.testcase_dir)),
                        "name": tc.name,
                        "description": tc.description,
                        "tags": tc.tags,
                        "priority": tc.priority,
                        "steps_count": len(tc.steps),
                        "type": "suite_case",
                    })
            elif "steps" in data:
                tc = TestCaseParser.parse_test_case(data)
                if filter_tags and not filter_tags.intersection(set(tc.tags)):
                    continue
                if priority and tc.priority != priority:
                    continue
                cases.append({
                    "file": str(f.relative_to(app_state.testcase_dir)),
                    "name": tc.name,
                    "description": tc.description,
                    "tags": tc.tags,
                    "priority": tc.priority,
                    "steps_count": len(tc.steps),
                    "type": "single_case",
                })
        except Exception:
            continue

    return {"total": len(cases), "cases": cases}


@router.get("/{file_path:path}")
async def get_case(file_path: str):
    """获取用例详情"""
    full_path = app_state.testcase_dir / file_path
    if not full_path.exists():
        raise HTTPException(404, f"用例文件不存在: {file_path}")

    content = full_path.read_text(encoding="utf-8")
    try:
        data = TestCaseParser.load_file(full_path)
        if "test_cases" in data:
            parsed = TestCaseParser.parse_test_suite(data)
        elif "steps" in data:
            parsed = TestCaseParser.parse_test_case(data)
        else:
            parsed = None
    except ParserError as e:
        return {"file": file_path, "content": content, "valid": False, "error": str(e)}

    return {
        "file": file_path,
        "content": content,
        "valid": True,
        "parsed": parsed.model_dump() if parsed else None,
    }


@router.post("")
async def create_case(req: CaseCreateRequest):
    """创建测试用例"""
    file_path = app_state.testcase_dir / req.filename
    if file_path.exists():
        raise HTTPException(409, f"文件已存在: {req.filename}")

    # 校验
    is_valid, result = TestCaseParser.validate_yaml_string(req.content)
    if not is_valid:
        raise HTTPException(422, f"用例格式错误: {result}")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(req.content, encoding="utf-8")

    return {"message": "创建成功", "file": req.filename}


@router.put("/{file_path:path}")
async def update_case(file_path: str, req: CaseUpdateRequest):
    """更新测试用例"""
    full_path = app_state.testcase_dir / file_path
    if not full_path.exists():
        raise HTTPException(404, f"用例文件不存在: {file_path}")

    is_valid, result = TestCaseParser.validate_yaml_string(req.content)
    if not is_valid:
        raise HTTPException(422, f"用例格式错误: {result}")

    full_path.write_text(req.content, encoding="utf-8")
    return {"message": "更新成功", "file": file_path}


@router.delete("/{file_path:path}")
async def delete_case(file_path: str):
    """删除测试用例"""
    full_path = app_state.testcase_dir / file_path
    if not full_path.exists():
        raise HTTPException(404, f"用例文件不存在: {file_path}")

    full_path.unlink()
    return {"message": "删除成功", "file": file_path}


@router.post("/validate")
async def validate_case(req: CaseValidateRequest):
    """校验用例格式"""
    is_valid, result = TestCaseParser.validate_yaml_string(req.content)
    if is_valid:
        case = result
        return {
            "valid": True,
            "name": case.name,
            "steps_count": len(case.steps),
            "tags": case.tags,
        }
    return {"valid": False, "error": str(result)}


@router.post("/upload")
async def upload_case(file: UploadFile = File(...)):
    """上传用例文件"""
    if not file.filename:
        raise HTTPException(400, "缺少文件名")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".yaml", ".yml", ".json"):
        raise HTTPException(400, "仅支持 .yaml/.yml/.json 文件")

    content = await file.read()
    text = content.decode("utf-8")

    is_valid, result = TestCaseParser.validate_yaml_string(text)
    if not is_valid:
        raise HTTPException(422, f"用例格式错误: {result}")

    dest = app_state.testcase_dir / file.filename
    dest.write_text(text, encoding="utf-8")

    return {"message": "上传成功", "file": file.filename}
