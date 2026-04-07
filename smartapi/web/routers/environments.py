"""环境配置管理 API"""

from __future__ import annotations

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from smartapi.core.parser import TestCaseParser, ParserError
from smartapi.web.state import app_state

router = APIRouter()


class EnvCreateRequest(BaseModel):
    name: str
    base_url: str
    variables: dict = {}
    headers: dict = {}


class EnvUpdateRequest(BaseModel):
    base_url: str | None = None
    variables: dict | None = None
    headers: dict | None = None


@router.get("")
async def list_environments():
    """列出所有环境配置"""
    envs = []
    env_dir = app_state.env_dir
    if not env_dir.exists():
        return {"total": 0, "environments": []}

    for f in sorted(env_dir.glob("*.yaml")) + sorted(env_dir.glob("*.yml")):
        try:
            env = TestCaseParser.load_environment(f)
            envs.append({
                "file": f.name,
                "name": env.name,
                "base_url": env.base_url,
                "variables_count": len(env.variables),
            })
        except Exception:
            continue

    return {"total": len(envs), "environments": envs}


@router.get("/{name}")
async def get_environment(name: str):
    """获取环境配置详情"""
    env_file = _find_env_file(name)
    if not env_file:
        raise HTTPException(404, f"环境配置不存在: {name}")

    content = env_file.read_text(encoding="utf-8")
    try:
        env = TestCaseParser.load_environment(env_file)
        return {
            "file": env_file.name,
            "content": content,
            "parsed": {
                "name": env.name,
                "base_url": env.base_url,
                "variables": env.variables,
                "headers": env.headers,
            },
        }
    except ParserError as e:
        return {"file": env_file.name, "content": content, "error": str(e)}


@router.post("")
async def create_environment(req: EnvCreateRequest):
    """创建环境配置"""
    env_file = app_state.env_dir / f"{req.name}.yaml"
    if env_file.exists():
        raise HTTPException(409, f"环境配置已存在: {req.name}")

    data = {
        "name": req.name,
        "base_url": req.base_url,
        "variables": req.variables,
        "headers": req.headers,
    }

    app_state.env_dir.mkdir(parents=True, exist_ok=True)
    env_file.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")

    return {"message": "创建成功", "file": env_file.name}


@router.put("/{name}")
async def update_environment(name: str, req: EnvUpdateRequest):
    """更新环境配置"""
    env_file = _find_env_file(name)
    if not env_file:
        raise HTTPException(404, f"环境配置不存在: {name}")

    data = yaml.safe_load(env_file.read_text(encoding="utf-8"))
    if req.base_url is not None:
        data["base_url"] = req.base_url
    if req.variables is not None:
        data["variables"] = req.variables
    if req.headers is not None:
        data["headers"] = req.headers

    env_file.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    return {"message": "更新成功"}


@router.delete("/{name}")
async def delete_environment(name: str):
    """删除环境配置"""
    env_file = _find_env_file(name)
    if not env_file:
        raise HTTPException(404, f"环境配置不存在: {name}")

    env_file.unlink()
    return {"message": "删除成功"}


def _find_env_file(name: str):
    """查找环境配置文件"""
    for ext in (".yaml", ".yml"):
        f = app_state.env_dir / f"{name}{ext}"
        if f.exists():
            return f
    return None
