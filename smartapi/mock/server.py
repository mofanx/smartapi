"""Mock 服务器 - 声明式配置，快速搭建模拟接口"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

import yaml
from loguru import logger


class MockRoute:
    """Mock 路由定义"""

    def __init__(
        self,
        path: str,
        method: str = "GET",
        status_code: int = 200,
        response_body: Any = None,
        response_headers: Optional[dict[str, str]] = None,
        delay: float = 0,
        dynamic_rules: Optional[list[dict]] = None,
    ):
        self.path = path
        self.method = method.upper()
        self.status_code = status_code
        self.response_body = response_body
        self.response_headers = response_headers or {"Content-Type": "application/json"}
        self.delay = delay
        self.dynamic_rules = dynamic_rules or []

    def match(self, request_path: str, request_method: str) -> bool:
        """匹配请求"""
        if self.method != request_method.upper():
            return False
        # 支持路径参数: /api/user/{id}
        pattern = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", self.path)
        return bool(re.fullmatch(pattern, request_path))

    def get_response(self, request_body: Any = None, request_params: dict = None) -> tuple[int, dict, Any]:
        """获取响应（支持动态规则）"""
        # 检查动态规则
        for rule in self.dynamic_rules:
            condition = rule.get("condition", {})
            if self._match_condition(condition, request_body, request_params):
                return (
                    rule.get("status_code", self.status_code),
                    rule.get("headers", self.response_headers),
                    rule.get("body", self.response_body),
                )

        return self.status_code, self.response_headers, self.response_body

    @staticmethod
    def _match_condition(condition: dict, body: Any, params: dict) -> bool:
        """检查动态规则条件"""
        if not condition:
            return False

        for field, expected in condition.items():
            # 支持 body.xxx 和 params.xxx
            if field.startswith("body."):
                key = field[5:]
                actual = body.get(key) if isinstance(body, dict) else None
            elif field.startswith("params."):
                key = field[7:]
                actual = (params or {}).get(key)
            else:
                actual = None

            if str(actual) != str(expected):
                return False

        return True


class MockServer:
    """Mock 服务器"""

    def __init__(self):
        self.routes: list[MockRoute] = []

    def add_route(self, route: MockRoute):
        """添加路由"""
        self.routes.append(route)
        logger.debug(f"Mock 路由: {route.method} {route.path}")

    def load_config(self, config_path: str | Path):
        """从 YAML 配置加载 Mock 路由"""
        path = Path(config_path)
        content = path.read_text(encoding="utf-8")

        if path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)

        routes = data.get("routes", data.get("mocks", []))
        for route_data in routes:
            route = MockRoute(
                path=route_data["path"],
                method=route_data.get("method", "GET"),
                status_code=route_data.get("status_code", 200),
                response_body=route_data.get("body", route_data.get("response", {})),
                response_headers=route_data.get("headers", {"Content-Type": "application/json"}),
                delay=route_data.get("delay", 0),
                dynamic_rules=route_data.get("rules", []),
            )
            self.add_route(route)

        logger.info(f"加载 {len(routes)} 个 Mock 路由")

    def find_route(self, path: str, method: str) -> Optional[MockRoute]:
        """查找匹配路由"""
        for route in self.routes:
            if route.match(path, method):
                return route
        return None

    def create_app(self):
        """创建 Starlette ASGI 应用"""
        import asyncio
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import JSONResponse, Response
        from starlette.routing import Route

        mock_server = self

        async def handle_request(request: Request):
            path = request.url.path
            method = request.method

            route = mock_server.find_route(path, method)
            if not route:
                return JSONResponse(
                    {"error": "Mock route not found", "path": path, "method": method},
                    status_code=404,
                )

            # 解析请求体
            body = None
            try:
                body = await request.json()
            except Exception:
                pass

            params = dict(request.query_params)

            # 延迟
            if route.delay > 0:
                await asyncio.sleep(route.delay)

            status_code, headers, response_body = route.get_response(body, params)

            if isinstance(response_body, (dict, list)):
                return JSONResponse(response_body, status_code=status_code, headers=headers)
            else:
                return Response(
                    content=str(response_body) if response_body else "",
                    status_code=status_code,
                    headers=headers,
                )

        async def list_mocks(request: Request):
            """列出所有 Mock 路由"""
            routes_info = [
                {"method": r.method, "path": r.path, "status_code": r.status_code}
                for r in mock_server.routes
            ]
            return JSONResponse({"routes": routes_info, "total": len(routes_info)})

        # 创建 catch-all 路由
        app = Starlette(
            routes=[
                Route("/_mock/routes", list_mocks, methods=["GET"]),
                Route("/{path:path}", handle_request, methods=["GET", "POST", "PUT", "DELETE", "PATCH"]),
            ],
        )
        return app

    def run(self, host: str = "127.0.0.1", port: int = 8000):
        """启动 Mock 服务"""
        import uvicorn
        app = self.create_app()
        logger.info(f"Mock 服务启动: http://{host}:{port}")
        logger.info(f"路由列表: http://{host}:{port}/_mock/routes")
        uvicorn.run(app, host=host, port=port)
