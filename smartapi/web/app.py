"""FastAPI Web 应用 - SmartAPI-Test REST API"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from smartapi.web.routers import cases, environments, execution, reports, mock_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时初始化
    from smartapi.web.state import app_state
    app_state.initialize()
    yield
    # 关闭时清理
    app_state.cleanup()


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="SmartAPI-Test",
        description="智能声明式 API 自动化测试平台",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 路由
    app.include_router(cases.router, prefix="/api/v1/cases", tags=["用例管理"])
    app.include_router(environments.router, prefix="/api/v1/environments", tags=["环境管理"])
    app.include_router(execution.router, prefix="/api/v1/execution", tags=["执行管理"])
    app.include_router(reports.router, prefix="/api/v1/reports", tags=["报告管理"])
    app.include_router(mock_routes.router, prefix="/api/v1/mock", tags=["Mock管理"])

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    # 生产模式：提供前端静态文件
    static_dir = Path(__file__).parent.parent.parent / "web" / "dist"
    if static_dir.is_dir():
        from fastapi.responses import FileResponse

        app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="static")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """SPA fallback - 所有非 API 路由返回 index.html"""
            file_path = static_dir / full_path
            if file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(static_dir / "index.html"))

    return app
