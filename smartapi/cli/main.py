"""CLI 命令行工具 - SmartAPI-Test 智能声明式 API 自动化测试平台

提供丰富的命令行接口，可独立于 MCP 使用，也可作为 AI Skill 的后端。
所有命令输出结构化文本，便于 AI 工具解析和调用。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


@click.group()
@click.version_option(version="0.2.0", prog_name="SmartAPI-Test")
def cli():
    """SmartAPI-Test: 智能声明式 API 自动化测试平台

    CLI 提供完整的测试生命周期管理，可直接使用或由 AI 工具调用。
    """
    pass


# ================================================================
# 核心命令: run / validate / list
# ================================================================

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


@cli.command("list")
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


# ================================================================
# 生成命令: generate / import-openapi
# ================================================================

@cli.command()
@click.argument("description")
@click.option("--base-url", "-b", default="", help="API 基础 URL")
@click.option("--output", "-o", default=None, help="输出文件路径 (不指定则输出到终端)")
@click.option("--method", "-m", default="GET", type=click.Choice(["GET", "POST", "PUT", "DELETE", "PATCH"]), help="HTTP 方法")
@click.option("--url", "-u", default="/api/endpoint", help="接口路径")
@click.option("--steps", "-s", default=1, type=int, help="步骤数量")
def generate(description, base_url, output, method, url, steps):
    """根据描述生成 YAML 测试用例

    DESCRIPTION: 测试需求的自然语言描述

    \b
    示例:
      smartapi generate "测试用户登录接口"
      smartapi generate "测试用户注册" -m POST -u /api/register -o testcases/register.yaml
      smartapi generate "查询商品列表并验证分页" --base-url https://api.example.com
    """
    import yaml

    # 构建步骤列表
    step_list = []
    for i in range(steps):
        step = {
            "name": f"步骤{i + 1} - {description}" if steps == 1 else f"步骤{i + 1}",
            "request": {
                "method": method,
                "url": url,
                "headers": {"Content-Type": "application/json"},
            },
            "asserts": [
                {"target": "status_code", "operator": "eq", "expected": 200},
            ],
        }
        if method in ("POST", "PUT", "PATCH"):
            step["request"]["body"] = {"key": "value"}
        if i > 0:
            step["extract"] = []
        step_list.append(step)

    case = {
        "name": description,
        "description": f"自动生成: {description}",
        "tags": ["generated"],
        "base_url": base_url or "",
        "variables": {},
        "steps": step_list,
    }

    yaml_content = yaml.dump(case, allow_unicode=True, default_flow_style=False, sort_keys=False)
    yaml_output = f"# SmartAPI-Test 自动生成的测试用例\n# 描述: {description}\n# 请根据实际接口完善 URL、参数、断言\n\n{yaml_content}"

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(yaml_output, encoding="utf-8")
        console.print(f"[bold green]✅ 用例已生成: {output}[/]")
    else:
        console.print(Panel(
            Syntax(yaml_output, "yaml", theme="monokai"),
            title="[bold]生成的测试用例[/]",
            border_style="green",
        ))

    # 输出使用指引
    console.print("\n[dim]提示: 请根据实际 API 接口完善以下内容:[/]")
    console.print("[dim]  1. 修改 url/method/headers/params/body[/]")
    console.print("[dim]  2. 添加 extract 提取响应数据[/]")
    console.print("[dim]  3. 完善 asserts 断言验证[/]")
    console.print("[dim]  4. 使用 ${variable} 引用变量[/]")


@cli.command("import-openapi")
@click.argument("source")
@click.option("--output", "-o", default=None, help="输出目录或文件 (默认: testcases/)")
@click.option("--base-url", "-b", default="", help="覆盖 API 基础 URL")
@click.option("--tags", "-t", default="imported,openapi", help="添加的标签 (逗号分隔)")
@click.option("--split", is_flag=True, default=False, help="按接口拆分为单独文件")
def import_openapi(source, output, base_url, tags, split):
    """从 OpenAPI/Swagger 导入并生成测试用例

    SOURCE: OpenAPI 文件路径或 URL

    \b
    示例:
      smartapi import-openapi swagger.json
      smartapi import-openapi https://api.example.com/openapi.json
      smartapi import-openapi api-spec.yaml --output testcases/ --split
    """
    import yaml

    # 加载 OpenAPI 文档
    source_path = Path(source)
    if source_path.exists():
        content = source_path.read_text(encoding="utf-8")
        if source_path.suffix in (".yaml", ".yml"):
            openapi_data = yaml.safe_load(content)
        else:
            openapi_data = json.loads(content)
    elif source.startswith(("http://", "https://")):
        import httpx
        console.print(f"[dim]正在下载: {source}[/]")
        resp = httpx.get(source, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        try:
            openapi_data = resp.json()
        except Exception:
            openapi_data = yaml.safe_load(resp.text)
    else:
        console.print(f"[red]错误: 无法加载 OpenAPI 文档: {source}[/]")
        return

    # 解析 OpenAPI
    info = openapi_data.get("info", {})
    title = info.get("title", "API")
    version = info.get("version", "")
    paths = openapi_data.get("paths", {})

    if not base_url:
        servers = openapi_data.get("servers", [])
        if servers:
            base_url = servers[0].get("url", "")

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    console.print(f"[bold green]▶ 解析 OpenAPI: {title} {version}[/]")
    console.print(f"  接口数: {sum(len([m for m in methods if m.lower() in ('get','post','put','delete','patch')]) for methods in paths.values())}")
    console.print(f"  基础URL: {base_url or '(未设置)'}")

    # 生成用例
    generated_cases = []
    for path_str, methods in paths.items():
        for method, details in methods.items():
            if method.lower() not in ("get", "post", "put", "delete", "patch"):
                continue

            summary = details.get("summary", f"{method.upper()} {path_str}")
            operation_id = details.get("operationId", "")

            # 分析参数
            params = {}
            body = None
            for param in details.get("parameters", []):
                if param.get("in") == "query":
                    params[param["name"]] = param.get("schema", {}).get("example", f"<{param['name']}>")
                elif param.get("in") == "path":
                    path_str = path_str.replace(f"{{{param['name']}}}", f"${{{param['name']}}}")

            # 分析请求体
            request_body = details.get("requestBody", {})
            if request_body:
                content = request_body.get("content", {})
                json_schema = content.get("application/json", {}).get("schema", {})
                if json_schema:
                    body = _schema_to_example(json_schema, openapi_data)

            # 分析响应
            responses = details.get("responses", {})
            expected_status = 200
            for code in responses:
                if code.startswith("2"):
                    expected_status = int(code)
                    break

            step = {
                "name": summary,
                "request": {
                    "method": method.upper(),
                    "url": path_str,
                    "headers": {"Content-Type": "application/json"},
                },
                "asserts": [
                    {"target": "status_code", "operator": "eq", "expected": expected_status},
                ],
            }
            if params:
                step["request"]["params"] = params
            if body and method.lower() in ("post", "put", "patch"):
                step["request"]["body"] = body

            case = {
                "name": summary,
                "description": details.get("description", summary),
                "tags": tag_list + ([operation_id] if operation_id else []),
                "base_url": base_url,
                "steps": [step],
            }
            generated_cases.append(case)

    if not generated_cases:
        console.print("[yellow]未从 OpenAPI 文档中解析到有效接口[/]")
        return

    # 输出
    output_dir = Path(output or "testcases")

    if split:
        output_dir.mkdir(parents=True, exist_ok=True)
        for i, case in enumerate(generated_cases):
            safe_name = case["name"][:50].replace("/", "_").replace(" ", "_").replace("\\", "_")
            file_path = output_dir / f"openapi_{i + 1:03d}_{safe_name}.yaml"
            yaml_out = f"# 从 OpenAPI 导入: {title}\n" + yaml.dump(case, allow_unicode=True, default_flow_style=False, sort_keys=False)
            file_path.write_text(yaml_out, encoding="utf-8")
        console.print(f"[bold green]✅ 已生成 {len(generated_cases)} 个用例文件到: {output_dir}/[/]")
    else:
        # 合并为一个测试集文件
        suite = {
            "name": f"{title} 自动化测试",
            "description": f"从 OpenAPI {version} 导入生成",
            "tags": tag_list,
            "test_cases": generated_cases,
        }
        if output and not Path(output).is_dir():
            out_file = Path(output)
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
            out_file = output_dir / f"openapi_{title.replace(' ', '_').lower()}.yaml"

        yaml_out = f"# 从 OpenAPI 导入: {title} {version}\n" + yaml.dump(suite, allow_unicode=True, default_flow_style=False, sort_keys=False)
        out_file.write_text(yaml_out, encoding="utf-8")
        console.print(f"[bold green]✅ 已生成测试集: {out_file} ({len(generated_cases)} 个用例)[/]")

    # 显示汇总
    table = Table(title="导入接口汇总")
    table.add_column("#", style="dim")
    table.add_column("方法", style="bold")
    table.add_column("路径", style="cyan")
    table.add_column("描述")

    for i, case in enumerate(generated_cases, 1):
        step = case["steps"][0]
        table.add_row(str(i), step["request"]["method"], step["request"]["url"], case["name"])

    console.print(table)


# ================================================================
# 分析命令: schema / inspect / analyze
# ================================================================

@cli.command()
@click.option("--format", "-f", "fmt", default="yaml", type=click.Choice(["yaml", "json", "text"]), help="输出格式")
def schema(fmt):
    """输出 YAML 测试用例 Schema 参考

    AI 工具可通过此命令获取完整的用例格式规范。

    \b
    示例:
      smartapi schema
      smartapi schema --format json
    """
    schema_text = _get_schema_text()

    if fmt == "text":
        console.print(schema_text)
    elif fmt == "json":
        console.print(json.dumps(_get_schema_dict(), indent=2, ensure_ascii=False))
    else:
        console.print(Panel(
            Syntax(schema_text, "yaml", theme="monokai"),
            title="[bold]SmartAPI-Test YAML Schema[/]",
            border_style="blue",
        ))


@cli.command()
@click.argument("path")
@click.option("--fix", is_flag=True, default=False, help="自动修复可修复的问题")
def inspect(path, fix):
    """分析测试用例质量并给出优化建议

    PATH: 测试用例文件路径

    \b
    示例:
      smartapi inspect testcases/login.yaml
      smartapi inspect testcases/ --fix
    """
    from smartapi.core.parser import TestCaseParser

    path = Path(path)
    files = []
    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = TestCaseParser.discover_test_files(path)

    if not files:
        console.print("[yellow]未找到测试用例文件[/]")
        return

    total_suggestions = 0

    for f in files:
        try:
            data = TestCaseParser.load_file(f)
            if "steps" not in data and "test_cases" not in data:
                continue

            if "test_cases" in data:
                suite = TestCaseParser.parse_test_suite(data)
                cases = suite.test_cases
            else:
                cases = [TestCaseParser.parse_test_case(data)]

            for case in cases:
                suggestions = _inspect_case(case)
                if suggestions:
                    total_suggestions += len(suggestions)
                    console.print(f"\n[bold cyan]📋 {f} → {case.name}[/]")
                    for s in suggestions:
                        level_icon = {"error": "❌", "warning": "⚠️", "info": "💡"}.get(s["level"], "💡")
                        console.print(f"  {level_icon} [{s['level']}] {s['message']}")
                        if s.get("suggestion"):
                            console.print(f"     ↳ {s['suggestion']}")
        except Exception as e:
            console.print(f"[red]❌ 解析失败: {f} - {e}[/]")

    if total_suggestions == 0:
        console.print("[bold green]✅ 所有用例质量良好，暂无优化建议！[/]")
    else:
        console.print(f"\n[bold]共发现 {total_suggestions} 条建议[/]")


@cli.command()
@click.argument("error_info")
@click.option("--request", "-r", "request_info", default="", help="请求信息")
@click.option("--response", "-R", "response_info", default="", help="响应信息")
@click.option("--file", "-f", "error_file", default=None, help="从文件读取错误信息")
def analyze(error_info, request_info, response_info, error_file):
    """分析测试失败原因并给出调试建议

    ERROR_INFO: 错误信息文本

    \b
    示例:
      smartapi analyze "AssertionError: status_code eq 200, actual: 401"
      smartapi analyze "ConnectionError: 无法连接到服务器" --request "POST /api/login"
    """
    if error_file:
        error_info = Path(error_file).read_text(encoding="utf-8")

    analysis = _analyze_failure(error_info, request_info, response_info)
    console.print(Panel(analysis, title="[bold]测试失败分析[/]", border_style="red"))


# ================================================================
# 数据命令: data
# ================================================================

@cli.command()
@click.argument("type_name", default="string")
@click.option("--count", "-n", default=1, type=int, help="生成数量")
@click.option("--format", "-f", "fmt", default="text", type=click.Choice(["text", "json", "csv"]), help="输出格式")
@click.option("--schema", "-s", "schema_file", default=None, help="JSON Schema 文件路径")
@click.option("--locale", "-l", default="zh_CN", help="区域设置")
@click.option("--list-types", is_flag=True, default=False, help="列出所有可用的数据类型")
def data(type_name, count, fmt, schema_file, locale, list_types):
    """生成 Mock 测试数据

    TYPE_NAME: 数据类型 (默认: string)

    \b
    示例:
      smartapi data name --count 5
      smartapi data phone -n 10 -f json
      smartapi data email -n 3
      smartapi data --list-types
      smartapi data json_object --schema schema.json
    """
    from smartapi.mock.data_factory import DataFactory

    factory = DataFactory(locale=locale)

    if list_types:
        types = factory.list_generators()
        table = Table(title="可用数据类型")
        table.add_column("类型", style="cyan")
        table.add_column("示例", style="green")

        for t in types:
            try:
                example = str(factory.generate(t))
                if len(example) > 60:
                    example = example[:57] + "..."
            except Exception:
                example = "-"
            table.add_row(t, example)

        console.print(table)
        return

    # 从 Schema 生成
    if schema_file:
        schema_data = json.loads(Path(schema_file).read_text(encoding="utf-8"))
        results = [factory._generate_from_schema(schema_data) for _ in range(count)]
    else:
        results = [factory.generate(type_name) for _ in range(count)]

    # 输出
    if fmt == "json":
        output = json.dumps(results if count > 1 else results[0], indent=2, ensure_ascii=False, default=str)
        console.print(output)
    elif fmt == "csv":
        for item in results:
            console.print(str(item))
    else:
        if count == 1:
            console.print(str(results[0]))
        else:
            for i, item in enumerate(results, 1):
                console.print(f"[dim]{i:3d}.[/] {item}")


# ================================================================
# 安全命令: encrypt / decrypt
# ================================================================

@cli.command()
@click.argument("value")
@click.option("--key", "-k", default=None, help="加密密钥 (默认从环境变量/密钥文件获取)")
def encrypt(value, key):
    """加密敏感信息

    VALUE: 要加密的值

    \b
    示例:
      smartapi encrypt "my_secret_password"
      smartapi encrypt "api_key_value" --key my_master_key
    """
    from smartapi.core.security import SecretManager

    manager = SecretManager(key=key)
    encrypted = manager.encrypt(value)
    console.print(f"[green]{encrypted}[/]")
    console.print(f"\n[dim]在 YAML 中使用: password: \"{encrypted}\"[/]")


@cli.command()
@click.argument("value")
@click.option("--key", "-k", default=None, help="解密密钥")
def decrypt(value, key):
    """解密敏感信息

    VALUE: ENC(...) 格式的加密值

    \b
    示例:
      smartapi decrypt "ENC(gAAAAABf...)"
    """
    from smartapi.core.security import SecretManager

    manager = SecretManager(key=key)
    decrypted = manager.decrypt(value)
    console.print(decrypted)


# ================================================================
# 环境命令: env
# ================================================================

@cli.group("env")
def env_group():
    """环境配置管理"""
    pass


@env_group.command("list")
@click.option("--dir", "-d", "env_dir", default="environments", help="环境配置目录")
def env_list(env_dir):
    """列出所有环境配置

    \b
    示例:
      smartapi env list
      smartapi env list --dir config/environments
    """
    import yaml

    env_path = Path(env_dir)
    if not env_path.is_dir():
        console.print(f"[yellow]目录不存在: {env_dir}[/]")
        return

    table = Table(title="环境配置列表")
    table.add_column("文件", style="cyan")
    table.add_column("名称", style="bold")
    table.add_column("基础URL", style="green")
    table.add_column("变量数")

    for f in sorted(env_path.glob("*.yaml")) + sorted(env_path.glob("*.yml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "name" in data:
                table.add_row(
                    f.name,
                    data.get("name", "-"),
                    data.get("base_url", "-"),
                    str(len(data.get("variables", {}))),
                )
        except Exception:
            table.add_row(f.name, "[red]解析失败[/]", "-", "-")

    console.print(table)


@env_group.command("show")
@click.argument("name")
@click.option("--dir", "-d", "env_dir", default="environments", help="环境配置目录")
def env_show(name, env_dir):
    """显示环境配置详情

    NAME: 环境名称或文件名

    \b
    示例:
      smartapi env show dev
      smartapi env show prod --dir config/environments
    """
    import yaml

    env_path = Path(env_dir)
    # 查找匹配的环境文件
    target = None
    for f in sorted(env_path.glob("*.yaml")) + sorted(env_path.glob("*.yml")):
        if f.stem == name or f.name == name:
            target = f
            break
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("name") == name:
                target = f
                break
        except Exception:
            continue

    if not target:
        console.print(f"[red]未找到环境配置: {name}[/]")
        return

    content = target.read_text(encoding="utf-8")
    console.print(Panel(
        Syntax(content, "yaml", theme="monokai"),
        title=f"[bold]环境配置: {target.name}[/]",
        border_style="blue",
    ))


# ================================================================
# 报告命令: report
# ================================================================

@cli.command()
@click.argument("path", default="testcases")
@click.option("--output", "-o", default="reports/report.html", help="报告输出路径")
@click.option("--title", "-t", default="", help="报告标题")
@click.option("--base-url", "-b", default="", help="API 基础 URL")
@click.option("--env", "-e", default=None, help="环境配置文件路径")
def report(path, output, title, base_url, env):
    """执行测试并生成 HTML 报告

    PATH: 测试用例文件或目录

    \b
    示例:
      smartapi report testcases/
      smartapi report testcases/login.yaml -o reports/login.html
      smartapi report testcases/ --title "回归测试报告" --env environments/prod.yaml
    """
    from smartapi.core.executor import TestExecutor
    from smartapi.core.parser import TestCaseParser
    from smartapi.core.variables import VariableManager
    from smartapi.report.html_report import HtmlReportGenerator

    # 加载环境
    var_manager = VariableManager()
    if env:
        try:
            env_config = TestCaseParser.load_environment(env)
            var_manager.set_global_vars(env_config.variables)
            if not base_url:
                base_url = env_config.base_url
        except Exception as e:
            console.print(f"[yellow]加载环境配置失败: {e}[/]")

    # 加载用例
    path = Path(path)
    cases = []
    if path.is_file():
        data = TestCaseParser.load_file(path)
        if "test_cases" in data:
            suite = TestCaseParser.parse_test_suite(data)
            cases = suite.test_cases
        elif "steps" in data:
            cases = [TestCaseParser.parse_test_case(data)]
    elif path.is_dir():
        cases = TestCaseParser.load_all_test_cases(path)

    if not cases:
        console.print("[yellow]未找到测试用例[/]")
        return

    console.print(f"[bold green]▶ 执行 {len(cases)} 个用例并生成报告...[/]")

    # 执行并收集结果
    report_gen = HtmlReportGenerator(title=title)

    for case in cases:
        executor = TestExecutor(
            variable_manager=VariableManager(global_vars=var_manager._global_vars.copy()),
            base_url=base_url or case.base_url or "",
        )
        try:
            result = executor.execute_test_case(case)
            report_gen.add_result(result)
            status = "✅" if result.success else "❌"
            console.print(f"  {status} {case.name} ({result.total_time}ms)")
        except Exception as e:
            console.print(f"  [red]❌ {case.name}: {e}[/]")
        finally:
            executor.close()

    # 生成报告
    report_path = report_gen.generate(output)
    console.print(f"\n[bold green]✅ HTML 报告已生成: {report_path}[/]")


# ================================================================
# 服务命令: mock-server / web / mcp
# ================================================================

@cli.command("mock-server")
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


# ================================================================
# 初始化命令: init
# ================================================================

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


# ================================================================
# 内部辅助函数
# ================================================================

def _schema_to_example(schema: dict, root_doc: dict = None) -> any:
    """从 OpenAPI Schema 生成示例值"""
    if "$ref" in schema and root_doc:
        ref_path = schema["$ref"].split("/")
        ref_obj = root_doc
        for part in ref_path[1:]:
            ref_obj = ref_obj.get(part, {})
        return _schema_to_example(ref_obj, root_doc)

    if "example" in schema:
        return schema["example"]

    schema_type = schema.get("type", "string")
    if schema_type == "object":
        properties = schema.get("properties", {})
        return {k: _schema_to_example(v, root_doc) for k, v in properties.items()}
    elif schema_type == "array":
        items = schema.get("items", {"type": "string"})
        return [_schema_to_example(items, root_doc)]
    elif schema_type == "string":
        fmt = schema.get("format", "")
        if fmt == "email":
            return "user@example.com"
        if fmt == "date":
            return "2024-01-01"
        if fmt == "date-time":
            return "2024-01-01T00:00:00Z"
        return schema.get("default", "string_value")
    elif schema_type == "integer":
        return schema.get("default", 0)
    elif schema_type == "number":
        return schema.get("default", 0.0)
    elif schema_type == "boolean":
        return schema.get("default", True)
    return None


def _inspect_case(case) -> list[dict]:
    """检查用例质量，返回建议列表"""
    suggestions = []

    if not case.description:
        suggestions.append({
            "level": "warning",
            "message": "缺少用例描述 (description)",
            "suggestion": "添加 description 字段说明用例目的",
        })

    if not case.tags:
        suggestions.append({
            "level": "warning",
            "message": "缺少标签 (tags)",
            "suggestion": "添加 tags 字段便于筛选和管理",
        })

    if not case.base_url:
        suggestions.append({
            "level": "info",
            "message": "未设置 base_url",
            "suggestion": "建议在用例或环境配置中设置 base_url",
        })

    for i, step in enumerate(case.steps, 1):
        prefix = f"步骤{i} [{step.name}]"

        if not step.asserts:
            suggestions.append({
                "level": "error",
                "message": f"{prefix}: 缺少断言",
                "suggestion": "至少添加 status_code 断言",
            })
        else:
            has_status = any(a.target.value == "status_code" for a in step.asserts)
            if not has_status:
                suggestions.append({
                    "level": "warning",
                    "message": f"{prefix}: 缺少状态码断言",
                    "suggestion": "添加 status_code eq 200 断言",
                })

            has_body = any(a.target.value == "body" for a in step.asserts)
            if not has_body:
                suggestions.append({
                    "level": "info",
                    "message": f"{prefix}: 缺少响应体断言",
                    "suggestion": "添加 body 断言验证返回数据",
                })

        has_time = any(a.target.value == "response_time" for a in step.asserts)
        if not has_time:
            suggestions.append({
                "level": "info",
                "message": f"{prefix}: 缺少响应时间断言",
                "suggestion": "添加 response_time lt 500 断言",
            })

        if not step.id and len(case.steps) > 1:
            suggestions.append({
                "level": "info",
                "message": f"{prefix}: 缺少步骤 ID",
                "suggestion": "添加 id 字段便于步骤间引用",
            })

        if step.request.method.value in ("POST", "PUT", "PATCH") and not step.request.body and not step.request.form_data:
            suggestions.append({
                "level": "warning",
                "message": f"{prefix}: {step.request.method.value} 请求缺少请求体",
                "suggestion": "添加 body 或 form_data",
            })

    return suggestions


def _analyze_failure(error_info: str, request_info: str = "", response_info: str = "") -> str:
    """分析测试失败原因"""
    lines = ["[bold]## 错误信息[/]", error_info, ""]
    causes = []

    error_lower = error_info.lower()
    if "timeout" in error_lower or "超时" in error_info:
        causes.append("**网络超时**: 服务端响应过慢或网络不稳定\n  → 增大 timeout 配置，检查服务端性能")
    if "connection" in error_lower or "连接" in error_info:
        causes.append("**连接失败**: 服务端未启动或地址错误\n  → 检查 base_url 配置，确认服务可用")
    if "assert" in error_lower or "断言" in error_info:
        causes.append("**断言失败**: 接口返回值与预期不符\n  → 核对接口文档，检查入参是否正确")
    if "401" in error_info or "403" in error_info or "鉴权" in error_info:
        causes.append("**鉴权失败**: Token 过期或权限不足\n  → 检查 auth 配置，确认 Token 有效")
    if "404" in error_info:
        causes.append("**接口不存在**: URL 路径错误\n  → 检查 url 配置，确认路径正确")
    if "500" in error_info:
        causes.append("**服务端错误**: 服务端内部异常\n  → 检查请求参数，查看服务端日志")
    if "json" in error_lower and ("decode" in error_lower or "parse" in error_lower):
        causes.append("**JSON 解析错误**: 响应不是有效的 JSON\n  → 检查接口是否返回了 HTML 错误页面")

    if causes:
        lines.append("[bold]## 可能原因[/]")
        for i, c in enumerate(causes, 1):
            lines.append(f"{i}. {c}")
        lines.append("")

    if request_info:
        lines.extend(["[bold]## 请求信息[/]", request_info, ""])
    if response_info:
        lines.extend(["[bold]## 响应信息[/]", response_info, ""])

    lines.extend([
        "[bold]## 调试建议[/]",
        "1. 使用 smartapi validate <file> 检查用例格式",
        "2. 使用 smartapi inspect <file> 检查用例质量",
        "3. 使用 curl 或 httpx 手动测试接口",
        "4. 检查变量引用 ${var} 是否正确解析",
    ])

    return "\n".join(lines)


def _get_schema_text() -> str:
    """获取 YAML Schema 文本"""
    return """# SmartAPI-Test 测试用例 YAML Schema

## 顶层字段
name: string           # 必填，用例名称
description: string    # 可选，用例描述
tags: list[string]     # 可选，标签列表
priority: string       # 可选，high/medium/low
base_url: string       # 可选，基础URL
variables: dict        # 可选，用例级变量
auth:                  # 可选，用例级鉴权
  type: string         # none/basic/bearer/token/oauth2/jwt/api_key/custom
  username: string     # basic 鉴权
  password: string     # basic 鉴权
  token: string        # bearer/token 鉴权
  token_url: string    # 自动获取 token
  token_field: string  # token 字段名 (默认: token)
  token_prefix: string # token 前缀 (默认: Bearer)
  api_key_name: string # API Key 名称
  api_key_value: string # API Key 值
  api_key_in: string   # header/query
setup: list[Step]      # 可选，前置步骤
steps: list[Step]      # 必填，测试步骤
teardown: list[Step]   # 可选，后置步骤

## Step 步骤字段
- id: string           # 可选，步骤ID（用于依赖引用）
  name: string         # 必填，步骤名称
  request:             # 必填，请求配置
    method: string     # GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS
    url: string        # 请求URL（支持 ${variable} 变量）
    headers: dict      # 请求头
    params: dict       # 查询参数
    body: any          # JSON 请求体
    form_data: dict    # 表单数据
    files: dict        # 文件上传 {field: path}
    cookies: dict      # Cookie
    auth: Auth         # 步骤级鉴权
  extract:             # 可选，数据提取
    - name: string     # 变量名
      type: string     # jsonpath/xpath/regex/header
      expression: str  # 提取表达式
      default: any     # 默认值
  asserts:             # 可选，断言列表
    - target: string   # status_code/header/body/response_time/custom
      expression: str  # JSONPath/Header名
      operator: string # eq/ne/neq/contains/not_contains/starts_with/ends_with
                       # gt/lt/gte/lte/regex/in/not_in
                       # is_null/is_not_null/length_eq/length_gt/length_lt/type_is
      expected: any    # 期望值
      level: string    # warning/error/fatal
      message: string  # 自定义消息
      script: string   # Python 脚本断言
  variables: dict      # 步骤级变量
  retry: int|dict      # 重试次数 或 {max_retries: 3, retry_interval: 2}
  retry_interval: float # 重试间隔(秒)
  timeout: float       # 超时(秒)
  skip_if:             # 跳过条件
    variable: string
    operator: string   # eq/ne/neq/contains/gt/lt/exists/not_exists
    value: any
  depends_on: list[str] # 依赖步骤ID
  loop:                # 循环配置
    times: int         # 固定次数
    condition:         # 条件循环
      variable: string
      operator: string
      value: any
    max_iterations: int
    interval: float
  branch:              # 分支配置
    condition:
      variable: string
      operator: string
      value: any
    then_steps: list[str]
    else_steps: list[str]

## 内置变量函数
- ${timestamp()}      - Unix 时间戳
- ${uuid()}           - UUID
- ${random_int()}     - 随机整数
- ${random_string()}  - 随机字符串
- ${random_phone()}   - 随机手机号
- ${random_email()}   - 随机邮箱
- ${random_name()}    - 随机姓名
- ${random_id_card()} - 随机身份证号
- ${now()}            - 当前时间
- ${today()}          - 当前日期
- ${md5(value)}       - MD5 哈希
- ${sha256(value)}    - SHA256 哈希

## 测试集格式 (多用例)
name: string
description: string
tags: list[string]
variables: dict
test_cases:
  - name: string
    steps: [...]
  - name: string
    steps: [...]
"""


def _get_schema_dict() -> dict:
    """获取 Schema 的结构化表示"""
    return {
        "test_case": {
            "name": {"type": "string", "required": True, "description": "用例名称"},
            "description": {"type": "string", "required": False},
            "tags": {"type": "list[string]", "required": False},
            "priority": {"type": "string", "enum": ["high", "medium", "low"]},
            "base_url": {"type": "string", "required": False},
            "variables": {"type": "dict", "required": False},
            "steps": {"type": "list[Step]", "required": True},
        },
        "step": {
            "name": {"type": "string", "required": True},
            "request": {
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]},
                "url": {"type": "string", "required": True},
                "headers": {"type": "dict"},
                "params": {"type": "dict"},
                "body": {"type": "any"},
            },
            "extract": {"type": "list", "items": {"name": "string", "type": "jsonpath|xpath|regex|header", "expression": "string"}},
            "asserts": {"type": "list", "items": {"target": "status_code|header|body|response_time", "operator": "eq|ne|contains|gt|lt|...", "expected": "any"}},
        },
        "operators": {
            "assert": ["eq", "ne", "neq", "contains", "not_contains", "starts_with", "ends_with", "gt", "lt", "gte", "lte", "regex", "in", "not_in", "is_null", "is_not_null", "length_eq", "length_gt", "length_lt", "type_is"],
            "condition": ["eq", "ne", "neq", "contains", "gt", "lt", "exists", "not_exists"],
        },
    }


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
