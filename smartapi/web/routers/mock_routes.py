"""Mock 服务管理 API"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from smartapi.web.state import app_state

router = APIRouter()


class MockRouteCreate(BaseModel):
    path: str
    method: str = "GET"
    status_code: int = 200
    body: Any = None
    headers: dict = {"Content-Type": "application/json"}
    delay: float = 0
    rules: list[dict] = []


@router.get("/configs")
async def list_mock_configs():
    """列出 Mock 配置文件"""
    mock_dir = app_state.mock_dir
    if not mock_dir.exists():
        return {"total": 0, "configs": []}

    configs = []
    for f in sorted(mock_dir.glob("*.yaml")) + sorted(mock_dir.glob("*.yml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            routes = data.get("routes", data.get("mocks", []))
            configs.append({
                "file": f.name,
                "routes_count": len(routes),
            })
        except Exception:
            continue

    return {"total": len(configs), "configs": configs}


@router.get("/configs/{file_name}")
async def get_mock_config(file_name: str):
    """获取 Mock 配置详情"""
    mock_file = app_state.mock_dir / file_name
    if not mock_file.exists():
        raise HTTPException(404, f"Mock 配置不存在: {file_name}")

    content = mock_file.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    routes = data.get("routes", data.get("mocks", []))

    return {
        "file": file_name,
        "content": content,
        "routes": routes,
    }


@router.post("/configs/{file_name}/routes")
async def add_mock_route(file_name: str, route: MockRouteCreate):
    """向 Mock 配置添加路由"""
    mock_file = app_state.mock_dir / file_name
    if not mock_file.exists():
        # 创建新文件
        data = {"routes": []}
    else:
        data = yaml.safe_load(mock_file.read_text(encoding="utf-8")) or {"routes": []}

    routes = data.get("routes", [])
    routes.append({
        "path": route.path,
        "method": route.method,
        "status_code": route.status_code,
        "body": route.body,
        "headers": route.headers,
        "delay": route.delay,
        "rules": route.rules,
    })
    data["routes"] = routes

    app_state.mock_dir.mkdir(parents=True, exist_ok=True)
    mock_file.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")

    return {"message": "路由添加成功", "routes_count": len(routes)}


@router.get("/data-factory/types")
async def list_data_types():
    """列出数据工厂支持的数据类型"""
    types = app_state.data_factory.list_generators()
    return {"total": len(types), "types": types}


@router.post("/data-factory/generate")
async def generate_mock_data(type_name: str, count: int = 1, **kwargs):
    """生成 Mock 数据"""
    results = []
    for _ in range(min(count, 100)):
        result = app_state.data_factory.generate(type_name)
        results.append(result)

    if count == 1:
        return {"data": results[0]}
    return {"data": results, "count": len(results)}
