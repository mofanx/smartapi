"""MCP Server - 为 AI 编辑器提供测试框架能力"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from smartapi.core.parser import TestCaseParser
from smartapi.core.variables import VariableManager

app = Server("smartapi-test")


# ======================== Tools ========================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用工具"""
    return [
        Tool(
            name="generate_test_case",
            description="根据自然语言描述生成 YAML 格式的 API 测试用例。输入测试需求描述，输出符合 SmartAPI-Test 框架规范的 YAML 用例。",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "测试需求的自然语言描述，例如：'测试用户登录接口，成功后查询用户信息并断言手机号正确'",
                    },
                    "base_url": {
                        "type": "string",
                        "description": "API 基础 URL",
                        "default": "",
                    },
                },
                "required": ["description"],
            },
        ),
        Tool(
            name="validate_test_case",
            description="校验 YAML/JSON 格式的测试用例是否符合 SmartAPI-Test 框架规范",
            inputSchema={
                "type": "object",
                "properties": {
                    "yaml_content": {
                        "type": "string",
                        "description": "YAML 格式的测试用例内容",
                    },
                },
                "required": ["yaml_content"],
            },
        ),
        Tool(
            name="list_test_cases",
            description="列出指定目录中的所有测试用例",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "测试用例目录路径",
                        "default": "testcases",
                    },
                },
            },
        ),
        Tool(
            name="run_test_case",
            description="执行指定的测试用例文件并返回结果",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "测试用例文件路径",
                    },
                    "base_url": {
                        "type": "string",
                        "description": "API 基础 URL",
                        "default": "",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="analyze_failure",
            description="分析测试失败原因并给出调试建议",
            inputSchema={
                "type": "object",
                "properties": {
                    "error_info": {
                        "type": "string",
                        "description": "测试失败的错误信息",
                    },
                    "request_info": {
                        "type": "string",
                        "description": "请求信息 (URL, method, headers, body)",
                    },
                    "response_info": {
                        "type": "string",
                        "description": "响应信息 (status_code, headers, body)",
                    },
                },
                "required": ["error_info"],
            },
        ),
        Tool(
            name="get_yaml_schema",
            description="获取 SmartAPI-Test 测试用例的 YAML Schema 定义，帮助了解用例格式规范",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="import_openapi",
            description="从 OpenAPI/Swagger JSON 文件导入接口定义，自动生成基础测试用例",
            inputSchema={
                "type": "object",
                "properties": {
                    "openapi_content": {
                        "type": "string",
                        "description": "OpenAPI/Swagger JSON 内容",
                    },
                    "base_url": {
                        "type": "string",
                        "description": "API 基础 URL",
                        "default": "",
                    },
                },
                "required": ["openapi_content"],
            },
        ),
        Tool(
            name="suggest_improvements",
            description="扫描现有测试用例，提供优化建议（断言缺失、步骤冗余、变量使用不规范等）",
            inputSchema={
                "type": "object",
                "properties": {
                    "yaml_content": {
                        "type": "string",
                        "description": "YAML 格式的测试用例内容",
                    },
                },
                "required": ["yaml_content"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """处理工具调用"""
    try:
        if name == "generate_test_case":
            return _generate_test_case(arguments)
        elif name == "validate_test_case":
            return _validate_test_case(arguments)
        elif name == "list_test_cases":
            return _list_test_cases(arguments)
        elif name == "run_test_case":
            return _run_test_case(arguments)
        elif name == "analyze_failure":
            return _analyze_failure(arguments)
        elif name == "get_yaml_schema":
            return _get_yaml_schema(arguments)
        elif name == "import_openapi":
            return _import_openapi(arguments)
        elif name == "suggest_improvements":
            return _suggest_improvements(arguments)
        else:
            return [TextContent(type="text", text=f"未知工具: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"工具执行错误: {e}")]


def _generate_test_case(args: dict[str, Any]) -> list[TextContent]:
    """生成测试用例模板"""
    description = args["description"]
    base_url = args.get("base_url", "")

    # 生成一个符合规范的 YAML 模板，供 AI 进一步完善
    template = f"""# 由 SmartAPI-Test MCP 生成
# 需求描述: {description}
name: "根据描述生成的测试用例"
description: "{description}"
tags:
  - generated
base_url: "{base_url}"
variables: {{}}

steps:
  - name: "步骤1 - 请根据需求描述完善"
    request:
      method: GET
      url: "/api/endpoint"
      headers:
        Content-Type: "application/json"
      params: {{}}
      body: null
    extract: []
    asserts:
      - target: status_code
        operator: eq
        expected: 200
"""

    guidance = f"""
以上是根据您的需求描述生成的测试用例模板。

**需求描述**: {description}

**使用说明**:
1. 根据实际的 API 接口修改 `url`、`method`、`headers`、`params`、`body`
2. 添加数据提取 (`extract`) 来获取响应中的数据供后续步骤使用
3. 完善断言 (`asserts`) 来验证接口返回是否符合预期
4. 如需多步骤，在 `steps` 中添加更多步骤

**支持的断言操作符**: eq, ne, contains, not_contains, gt, lt, gte, lte, regex, is_null, is_not_null, length_eq, length_gt, length_lt, type_is
**支持的提取类型**: jsonpath, xpath, regex, header
**支持的变量引用**: ${{variable_name}}, ${{timestamp()}}, ${{uuid()}}, ${{random_phone()}}
"""

    return [TextContent(type="text", text=template + "\n---\n" + guidance)]


def _validate_test_case(args: dict[str, Any]) -> list[TextContent]:
    """校验用例"""
    yaml_content = args["yaml_content"]
    is_valid, result = TestCaseParser.validate_yaml_string(yaml_content)

    if is_valid:
        case = result
        info = (
            f"✅ 用例校验通过！\n"
            f"- 用例名称: {case.name}\n"
            f"- 步骤数量: {len(case.steps)}\n"
            f"- 标签: {', '.join(case.tags) or '无'}\n"
            f"- 基础URL: {case.base_url or '未设置'}\n"
        )
        for i, step in enumerate(case.steps, 1):
            info += f"- 步骤{i}: {step.name} ({step.request.method.value} {step.request.url})\n"
            info += f"  断言数: {len(step.asserts)}, 提取数: {len(step.extract)}\n"
        return [TextContent(type="text", text=info)]
    else:
        return [TextContent(type="text", text=f"❌ 用例校验失败:\n{result}")]


def _list_test_cases(args: dict[str, Any]) -> list[TextContent]:
    """列出用例"""
    directory = args.get("directory", "testcases")
    path = Path(directory)

    if not path.exists():
        return [TextContent(type="text", text=f"目录不存在: {directory}")]

    cases = TestCaseParser.load_all_test_cases(path)
    if not cases:
        return [TextContent(type="text", text="未找到测试用例")]

    lines = [f"找到 {len(cases)} 个测试用例:\n"]
    for i, case in enumerate(cases, 1):
        lines.append(
            f"{i}. {case.name} "
            f"[标签: {', '.join(case.tags) or '无'}] "
            f"[步骤: {len(case.steps)}] "
            f"[优先级: {case.priority}]"
        )

    return [TextContent(type="text", text="\n".join(lines))]


def _run_test_case(args: dict[str, Any]) -> list[TextContent]:
    """执行用例"""
    from smartapi.core.executor import TestExecutor

    file_path = args["file_path"]
    base_url = args.get("base_url", "")

    try:
        case = TestCaseParser.load_test_case(file_path)
    except Exception as e:
        return [TextContent(type="text", text=f"加载用例失败: {e}")]

    var_manager = VariableManager()
    executor = TestExecutor(
        variable_manager=var_manager,
        base_url=base_url or case.base_url or "",
    )

    try:
        result = executor.execute_test_case(case)

        lines = [
            f"{'✅ 通过' if result.success else '❌ 失败'} 用例: {result.case_name}",
            f"总步骤: {result.total_steps}, 通过: {result.passed_steps}, "
            f"失败: {result.failed_steps}, 跳过: {result.skipped_steps}",
            f"总耗时: {result.total_time}ms\n",
        ]

        for sr in result.step_results:
            status = "✅" if sr.success else ("⏭" if sr.skipped else "❌")
            lines.append(f"{status} {sr.step_name}")
            if sr.status_code:
                lines.append(f"  状态码: {sr.status_code}, 响应时间: {sr.response_time}ms")
            if sr.error:
                lines.append(f"  错误: {sr.error}")
            for ar in sr.assert_results:
                ar_status = "✅" if ar.passed else "❌"
                lines.append(f"  {ar_status} {ar.target} {ar.operator} {ar.expected} (实际: {ar.actual})")

        return [TextContent(type="text", text="\n".join(lines))]
    finally:
        executor.close()


def _analyze_failure(args: dict[str, Any]) -> list[TextContent]:
    """分析失败原因"""
    error_info = args["error_info"]
    request_info = args.get("request_info", "")
    response_info = args.get("response_info", "")

    analysis = f"""## 测试失败分析

### 错误信息
{error_info}

### 可能原因
"""
    # 基于错误类型给出建议
    if "timeout" in error_info.lower() or "超时" in error_info:
        analysis += "1. **网络超时**: 服务端响应过慢或网络不稳定\n   - 建议: 增大 timeout 配置，检查服务端性能\n"
    if "connection" in error_info.lower() or "连接" in error_info:
        analysis += "1. **连接失败**: 服务端未启动或地址错误\n   - 建议: 检查 base_url 配置，确认服务端是否可用\n"
    if "assert" in error_info.lower() or "断言" in error_info:
        analysis += "1. **断言失败**: 接口返回值与预期不符\n   - 建议: 核对接口文档，检查入参是否正确\n"
    if "401" in error_info or "403" in error_info or "鉴权" in error_info:
        analysis += "1. **鉴权失败**: Token 过期或权限不足\n   - 建议: 检查 auth 配置，确认 Token 是否有效\n"
    if "404" in error_info:
        analysis += "1. **接口不存在**: URL 路径错误\n   - 建议: 检查 url 配置，确认接口路径是否正确\n"
    if "500" in error_info:
        analysis += "1. **服务端错误**: 服务端内部异常\n   - 建议: 检查请求参数是否正确，查看服务端日志\n"

    if request_info:
        analysis += f"\n### 请求信息\n{request_info}\n"
    if response_info:
        analysis += f"\n### 响应信息\n{response_info}\n"

    analysis += "\n### 调试建议\n"
    analysis += "1. 使用 `validate_test_case` 工具检查用例格式\n"
    analysis += "2. 检查变量引用是否正确解析\n"
    analysis += "3. 使用 curl 或 httpie 手动测试接口\n"

    return [TextContent(type="text", text=analysis)]


def _get_yaml_schema(args: dict[str, Any]) -> list[TextContent]:
    """返回用例 Schema"""
    schema = """# SmartAPI-Test 测试用例 YAML Schema

## 顶层字段
```yaml
name: string           # 必填，用例名称
description: string    # 可选，用例描述
tags: list[string]     # 可选，标签列表
priority: string       # 可选，high/medium/low
base_url: string       # 可选，基础URL
variables: dict        # 可选，用例级变量
auth:                  # 可选，用例级鉴权
  type: string         # none/basic/bearer/token/oauth2/jwt/api_key/custom
  ...
setup: list[Step]      # 可选，前置步骤
steps: list[Step]      # 必填，测试步骤
teardown: list[Step]   # 可选，后置步骤
```

## Step 步骤字段
```yaml
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
      operator: string # eq/ne/contains/not_contains/gt/lt/gte/lte/regex/is_null/is_not_null/length_eq/length_gt/length_lt/type_is
      expected: any    # 期望值
      level: string    # warning/error/fatal
      message: string  # 自定义消息
      script: string   # Python 脚本断言
  variables: dict      # 步骤级变量
  retry: int           # 重试次数
  retry_interval: float # 重试间隔(秒)
  timeout: float       # 超时(秒)
  skip_if:             # 跳过条件
    variable: string
    operator: string   # eq/ne/contains/gt/lt/exists/not_exists
    value: any
  depends_on: list[str] # 依赖步骤ID
  loop:                # 循环配置
    times: int         # 固定次数
    condition: Condition # 条件循环
    max_iterations: int
    interval: float
  branch:              # 分支配置
    condition: Condition
    then_steps: list[str]
    else_steps: list[str]
```

## 内置变量函数
- `${timestamp()}` - Unix 时间戳
- `${uuid()}` - UUID
- `${random_int()}` - 随机整数
- `${random_string()}` - 随机字符串
- `${random_phone()}` - 随机手机号
- `${random_email()}` - 随机邮箱
- `${random_name()}` - 随机姓名
- `${random_id_card()}` - 随机身份证号
- `${now()}` - 当前时间
- `${today()}` - 当前日期
- `${md5(value)}` - MD5 哈希
- `${sha256(value)}` - SHA256 哈希
"""
    return [TextContent(type="text", text=schema)]


def _import_openapi(args: dict[str, Any]) -> list[TextContent]:
    """从 OpenAPI 导入并生成用例"""
    try:
        openapi_data = json.loads(args["openapi_content"])
    except json.JSONDecodeError as e:
        return [TextContent(type="text", text=f"JSON 解析错误: {e}")]

    base_url = args.get("base_url", "")

    # 提取基本信息
    info = openapi_data.get("info", {})
    title = info.get("title", "API")
    paths = openapi_data.get("paths", {})

    if not base_url:
        servers = openapi_data.get("servers", [])
        if servers:
            base_url = servers[0].get("url", "")

    # 生成用例
    yaml_lines = [
        f"# 从 OpenAPI 导入: {title}",
        f'name: "{title} 自动化测试"',
        f'description: "从 OpenAPI 文档自动生成"',
        "tags:",
        "  - imported",
        "  - openapi",
        f'base_url: "{base_url}"',
        "",
        "test_cases:",
    ]

    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() not in ("get", "post", "put", "delete", "patch"):
                continue

            summary = details.get("summary", f"{method.upper()} {path}")
            operation_id = details.get("operationId", "")

            yaml_lines.extend([
                f'  - name: "{summary}"',
                f'    tags: ["{operation_id or method}"]',
                "    steps:",
                f'      - name: "{summary}"',
                "        request:",
                f"          method: {method.upper()}",
                f'          url: "{path}"',
                "          headers:",
                '            Content-Type: "application/json"',
                "        asserts:",
                "          - target: status_code",
                "            operator: eq",
                "            expected: 200",
                "",
            ])

    result = "\n".join(yaml_lines)
    return [TextContent(type="text", text=f"从 OpenAPI 文档生成了 {sum(1 for _ in _iter_paths(paths))} 个测试用例:\n\n{result}")]


def _iter_paths(paths):
    for path, methods in paths.items():
        for method in methods:
            if method.lower() in ("get", "post", "put", "delete", "patch"):
                yield path, method


def _suggest_improvements(args: dict[str, Any]) -> list[TextContent]:
    """用例优化建议"""
    yaml_content = args["yaml_content"]
    is_valid, result = TestCaseParser.validate_yaml_string(yaml_content)

    if not is_valid:
        return [TextContent(type="text", text=f"用例格式错误，请先修正:\n{result}")]

    case = result
    suggestions = []

    # 检查是否缺少描述
    if not case.description:
        suggestions.append("⚠️ **缺少用例描述**: 建议添加 `description` 字段，说明用例目的")

    # 检查是否缺少标签
    if not case.tags:
        suggestions.append("⚠️ **缺少标签**: 建议添加 `tags` 字段，便于筛选和管理")

    for i, step in enumerate(case.steps, 1):
        # 检查断言
        if not step.asserts:
            suggestions.append(f"⚠️ **步骤{i} [{step.name}] 缺少断言**: 建议至少添加状态码断言")
        else:
            has_status_assert = any(a.target.value == "status_code" for a in step.asserts)
            if not has_status_assert:
                suggestions.append(f"💡 **步骤{i} [{step.name}]**: 建议添加状态码断言")

            has_body_assert = any(a.target.value == "body" for a in step.asserts)
            if not has_body_assert:
                suggestions.append(f"💡 **步骤{i} [{step.name}]**: 建议添加响应体断言以验证返回数据")

        # 检查响应时间断言
        has_time_assert = any(a.target.value == "response_time" for a in step.asserts)
        if not has_time_assert:
            suggestions.append(f"💡 **步骤{i} [{step.name}]**: 建议添加响应时间断言 (如 ≤500ms)")

        # 检查步骤 ID
        if not step.id and len(case.steps) > 1:
            suggestions.append(f"💡 **步骤{i} [{step.name}]**: 建议添加 `id` 字段，便于步骤间引用")

    if not suggestions:
        return [TextContent(type="text", text="✅ 用例质量良好，暂无优化建议！")]

    return [TextContent(type="text", text="## 用例优化建议\n\n" + "\n".join(suggestions))]


def run_server(transport: str = "stdio", port: int = 3000):
    """启动 MCP Server"""
    import asyncio

    async def _run_stdio():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    if transport == "stdio":
        asyncio.run(_run_stdio())
    elif transport == "sse":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route
        import uvicorn

        sse = SseServerTransport("/messages")

        async def handle_sse(request):
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                await app.run(streams[0], streams[1], app.create_initialization_options())

        starlette_app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Route("/messages", endpoint=sse.handle_post_message, methods=["POST"]),
            ]
        )

        uvicorn.run(starlette_app, host="0.0.0.0", port=port)
