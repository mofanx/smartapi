"""项目 / 工作空间管理 API"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from smartapi.web.state import app_state

router = APIRouter()


class ProjectCreateRequest(BaseModel):
    name: str
    description: str = ""
    base_path: str = "."


class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


@router.get("")
async def list_projects():
    """列出所有项目"""
    return {"total": len(app_state.list_projects()), "projects": app_state.list_projects()}


@router.post("")
async def create_project(req: ProjectCreateRequest):
    """创建项目"""
    existing = app_state.list_projects()
    if any(p["name"] == req.name for p in existing):
        raise HTTPException(409, f"项目名称已存在: {req.name}")

    project = app_state.create_project(req.name, req.description, req.base_path)
    app_state.audit("project.create", resource=project["id"], detail=req.name)
    return {"message": "项目创建成功", "project": project}


@router.get("/{project_id}")
async def get_project(project_id: str):
    """获取项目详情"""
    project = app_state.get_project(project_id)
    if not project:
        raise HTTPException(404, f"项目不存在: {project_id}")
    return project


@router.put("/{project_id}")
async def update_project(project_id: str, req: ProjectUpdateRequest):
    """更新项目信息"""
    project = app_state.get_project(project_id)
    if not project:
        raise HTTPException(404, f"项目不存在: {project_id}")

    if project_id == "default":
        raise HTTPException(403, "默认项目不允许修改")

    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.description is not None:
        updates["description"] = req.description

    if not updates:
        return {"message": "没有更新内容", "project": project}

    # 通过 database 直接更新
    from smartapi.web import database as db

    db.update_project(app_state.db, project_id, **updates)
    updated = app_state.get_project(project_id)
    app_state.audit("project.update", resource=project_id, detail=str(updates))
    return {"message": "项目更新成功", "project": updated}


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """删除项目"""
    if project_id == "default":
        raise HTTPException(403, "默认项目不允许删除")

    if not app_state.delete_project(project_id):
        raise HTTPException(404, f"项目不存在: {project_id}")

    app_state.audit("project.delete", resource=project_id)
    return {"message": "项目删除成功"}
