"""CLI 命令行工具"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="SmartAPI-Test")
def cli():
    """SmartAPI-Test: 智能声明式 API 自动化测试平台"""
    pass


@cli.command()
@click.argument("path", default="testcases")
@click.option("--env", "-e", default=None, help="环境配置文件路径")
@click.option("--tags", "-t", default=None, help="按标签筛选 (逗号分隔)")
@click.option("--base-url", "-b", default="", help="基础 URL")
@click.option("--timeout", default=30, type=float, help="超时时间(秒)")
@click.option("--workers", "-w", default=1, type=int, help="并发执行数")
@click.option("--report", "-r", default="html", type=click.Choice(["html", "allure", "json"]), help="报告格式")
@click.option("--output", "-o", default="reports", help="报告输出目录")
def run(path, env, tags, base_url, timeout, workers, report, output):
    """执行测试用例

    PATH: 测试用例文件或目录 (默认: testcases)
    """
    import subprocess

    pytest_args = [sys.executable, "-m", "pytest", path, "-v"]

    if base_url:
        pytest_args.extend(["--smartapi-base-url", base_url])
    if env:
        pytest_args.extend(["--smartapi-env", env])
    if tags:
        pytest_args.extend(["--smartapi-tags", tags])
    if timeout:
        pytest_args.extend(["--smartapi-timeout", str(timeout)])
    if workers > 1:
        pytest_args.extend(["-n", str(workers)])

    # 报告
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    if report == "html":
        pytest_args.extend(["--html", str(output_path / "report.html"), "--self-contained-html"])
    elif report == "allure":
        pytest_args.extend(["--alluredir", str(output_path / "allure-results")])

    console.print(f"[bold green]▶ 开始执行测试...[/]")
    console.print(f"  用例路径: {path}")
    console.print(f"  基础URL: {base_url or '(未设置)'}")
    console.print(f"  环境: {env or '(未设置)'}")
    console.print(f"  标签: {tags or '(全部)'}")
    console.print()

    result = subprocess.run(pytest_args)
    sys.exit(result.returncode)


@cli.command()
@click.argument("path", default="testcases")
def validate(path):
    """校验测试用例文件格式

    PATH: 测试用例文件或目录
    """
    from smartapi.core.parser import TestCaseParser

    path = Path(path)
    files = []

    if path.is_file():
        files = [path]
    elif path.is_dir():
        for ext in ("*.yaml", "*.yml", "*.json"):
            files.extend(path.rglob(ext))

    if not files:
        console.print("[yellow]未找到测试用例文件[/]")
        return

    table = Table(title="用例校验结果")
    table.add_column("文件", style="cyan")
    table.add_column("状态", style="green")
    table.add_column("详情")

    success_count = 0
    fail_count = 0

    for f in sorted(files):
        try:
            data = TestCaseParser.load_file(f)
            if "test_cases" in data:
                suite = TestCaseParser.parse_test_suite(data)
                table.add_row(str(f), "✅ 通过", f"测试集: {suite.name}, {len(suite.test_cases)} 个用例")
            elif "steps" in data:
                case = TestCaseParser.parse_test_case(data)
                table.add_row(str(f), "✅ 通过", f"用例: {case.name}, {len(case.steps)} 个步骤")
            else:
                table.add_row(str(f), "⏭ 跳过", "不是测试用例文件")
                continue
            success_count += 1
        except Exception as e:
            table.add_row(str(f), "[red]❌ 失败[/]", f"[red]{e}[/]")
            fail_count += 1

    console.print(table)
    console.print(f"\n通过: {success_count}, 失败: {fail_count}")


@cli.command()
@click.argument("path", default="testcases")
def list_cases(path):
    """列出测试用例

    PATH: 测试用例文件或目录
    """
    from smartapi.core.parser import TestCaseParser

    path = Path(path)
    cases = TestCaseParser.load_all_test_cases(path) if path.is_dir() else []

    if path.is_file():
        data = TestCaseParser.load_file(path)
        if "test_cases" in data:
            suite = TestCaseParser.parse_test_suite(data)
            cases = suite.test_cases
        elif "steps" in data:
            cases = [TestCaseParser.parse_test_case(data)]

    if not cases:
        console.print("[yellow]未找到测试用例[/]")
        return

    table = Table(title="测试用例列表")
    table.add_column("#", style="dim")
    table.add_column("名称", style="cyan")
    table.add_column("标签", style="green")
    table.add_column("步骤数")
    table.add_column("优先级")

    for i, case in enumerate(cases, 1):
        table.add_row(
            str(i),
            case.name,
            ", ".join(case.tags) or "-",
            str(len(case.steps)),
            case.priority,
        )

    console.print(table)


@cli.command()
@click.option("--host", default="127.0.0.1", help="Mock 服务主机")
@click.option("--port", default=8000, type=int, help="Mock 服务端口")
@click.option("--config", "-c", default=None, help="Mock 配置文件路径")
def mock_server(host, port, config):
    """启动 Mock 服务"""
    from smartapi.mock.server import MockServer
    server = MockServer()
    if config:
        server.load_config(config)
        console.print(f"[green]已加载 Mock 配置: {config}[/]")
    else:
        mock_dir = Path("mock")
        if mock_dir.is_dir():
            for f in sorted(mock_dir.glob("*.yaml")) + sorted(mock_dir.glob("*.yml")):
                server.load_config(f)
                console.print(f"[green]已加载: {f}[/]")
    console.print(f"[bold green]▶ Mock 服务启动: http://{host}:{port}[/]")
    console.print(f"  路由列表: http://{host}:{port}/_mock/routes")
    server.run(host=host, port=port)


@cli.command()
@click.option("--host", default="127.0.0.1", help="Web 服务主机")
@click.option("--port", default=8100, type=int, help="Web 服务端口")
@click.option("--reload", is_flag=True, default=False, help="开发模式热重载")
def web(host, port, reload):
    """启动 Web 管理界面"""
    import uvicorn
    console.print(f"[bold green]▶ SmartAPI-Test Web 服务启动中...[/]")
    console.print(f"  地址: http://{host}:{port}")
    console.print(f"  API 文档: http://{host}:{port}/docs")
    uvicorn.run(
        "smartapi.web.app:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )


@cli.command()
@click.option("--transport", default="stdio", type=click.Choice(["stdio", "sse"]), help="MCP 传输方式")
@click.option("--port", default=3000, type=int, help="SSE 端口 (仅 sse 模式)")
def mcp(transport, port):
    """启动 MCP Server"""
    console.print(f"[bold green]▶ 启动 MCP Server (传输: {transport})[/]")
    from smartapi.mcp_server.server import run_server
    run_server(transport=transport, port=port)


@cli.command()
def init():
    """初始化项目结构"""
    dirs = ["testcases", "environments", "reports", "mock", "data"]
    files = {
        "testcases/example.yaml": _EXAMPLE_CASE,
        "environments/dev.yaml": _EXAMPLE_ENV,
    }

    for d in dirs:
        p = Path(d)
        p.mkdir(parents=True, exist_ok=True)
        console.print(f"  📁 创建目录: {d}")

    for f, content in files.items():
        p = Path(f)
        if not p.exists():
            p.write_text(content, encoding="utf-8")
            console.print(f"  📄 创建文件: {f}")

    console.print("\n[bold green]✅ 项目初始化完成！[/]")
    console.print("运行 [cyan]smartapi run[/] 开始执行测试")


_EXAMPLE_CASE = """# SmartAPI-Test 示例用例
name: "示例测试用例"
description: "演示基本的 API 测试功能"
tags:
  - smoke
  - example
base_url: "https://httpbin.org"

steps:
  - name: "GET 请求测试"
    request:
      method: GET
      url: "/get"
      params:
        foo: bar
    asserts:
      - target: status_code
        operator: eq
        expected: 200
      - target: body
        expression: "$.args.foo"
        operator: eq
        expected: "bar"

  - name: "POST 请求测试"
    request:
      method: POST
      url: "/post"
      body:
        username: "test_user"
        password: "test_pass"
    extract:
      - name: posted_data
        type: jsonpath
        expression: "$.json.username"
    asserts:
      - target: status_code
        operator: eq
        expected: 200
      - target: body
        expression: "$.json.username"
        operator: eq
        expected: "test_user"
"""

_EXAMPLE_ENV = """# 开发环境配置
name: "dev"
base_url: "https://httpbin.org"
variables:
  env_name: "development"
  debug: true
"""


if __name__ == "__main__":
    cli()
