# SmartAPI-Test

**智能声明式 API 自动化测试平台**

基于 Python + pytest，支持 YAML/JSON 声明式用例编写，集成 MCP 服务对接 AI 编辑器。

## 特性

- **声明式用例**: YAML/JSON 格式，零代码编写测试
- **多步骤编排**: 步骤串联、数据提取、分支/循环、步骤依赖
- **丰富断言**: 状态码/响应头/响应体/响应时间/自定义脚本，支持 15+ 运算符
- **变量系统**: 全局/环境/用例/步骤变量，内置动态函数（时间戳、UUID、随机数据等）
- **数据提取**: JSONPath / XPath / 正则 / Header 提取
- **鉴权适配**: Token / Basic / Bearer / OAuth2 / JWT / API Key / 自定义
- **MCP 集成**: 内置 MCP Server，对接 Claude/Cursor 等 AI 工具
- **Mock 服务**: 声明式配置 Mock 接口，支持动态规则和延迟响应
- **数据工厂**: 50+ 内置数据类型，支持数据池和 JSON Schema 生成
- **HTML 报告**: 美化渐变报告，支持 Allure 集成
- **通知推送**: 钉钉/飞书/企业微信/邮件/WebHook
- **安全加密**: ENC() 格式敏感信息加密存储
- **插件系统**: Hook/断言/数据生成插件，支持动态加载
- **Web 管理**: FastAPI REST API，用例/环境/执行/报告全生命周期管理
- **pytest 生态**: 完全兼容 pytest，支持 pytest-xdist 并发、pytest-html 报告、Allure
- **Docker 部署**: 提供 Dockerfile + docker-compose 一键部署

## 快速开始

### 安装

```bash
# 使用 uv (推荐)
uv pip install -e .

# 或 pip
pip install -e .
```

### 初始化项目

```bash
smartapi init
```

### 编写用例 (YAML)

```yaml
name: "用户登录测试"
base_url: "http://localhost:8080"

steps:
  - name: "登录"
    request:
      method: POST
      url: "/api/login"
      body:
        username: "admin"
        password: "123456"
    extract:
      - name: token
        type: jsonpath
        expression: "$.data.token"
    asserts:
      - target: status_code
        operator: eq
        expected: 200
      - target: body
        expression: "$.code"
        operator: eq
        expected: 0

  - name: "查询用户信息"
    request:
      method: GET
      url: "/api/user/info"
      headers:
        Authorization: "Bearer ${token}"
    asserts:
      - target: status_code
        operator: eq
        expected: 200
      - target: body
        expression: "$.data.username"
        operator: eq
        expected: "admin"
```

### 执行测试

```bash
# CLI 方式
smartapi run testcases/

# pytest 方式
pytest testcases/ --smartapi-base-url http://localhost:8080

# 按标签筛选
smartapi run testcases/ --tags smoke

# 并发执行
smartapi run testcases/ --workers 4
```

### 校验用例

```bash
smartapi validate testcases/
```

### 启动 MCP Server

```bash
# stdio 模式 (Cursor/Claude Desktop)
smartapi mcp --transport stdio

# SSE 模式 (Web 集成)
smartapi mcp --transport sse --port 3000
```

## MCP 工具列表

| 工具 | 描述 |
|------|------|
| `generate_test_case` | 根据自然语言描述生成测试用例 |
| `validate_test_case` | 校验用例格式 |
| `list_test_cases` | 列出测试用例 |
| `run_test_case` | 执行测试用例 |
| `analyze_failure` | 分析失败原因 |
| `get_yaml_schema` | 获取用例 Schema |
| `import_openapi` | 从 OpenAPI 导入生成用例 |
| `suggest_improvements` | 用例优化建议 |

## 内置变量函数

| 函数 | 说明 |
|------|------|
| `${timestamp()}` | Unix 时间戳 |
| `${uuid()}` | UUID |
| `${random_int()}` | 随机整数 |
| `${random_phone()}` | 随机手机号 |
| `${random_email()}` | 随机邮箱 |
| `${random_name()}` | 随机姓名 |
| `${random_id_card()}` | 随机身份证 |
| `${now()}` | 当前时间 |
| `${md5(value)}` | MD5 哈希 |

### 启动 Web 管理 API

```bash
# 启动 REST API (默认端口 8100)
smartapi web --port 8100

# 开发模式(热重载)
smartapi web --reload

# 访问 API 文档
# http://127.0.0.1:8100/docs
```

**Web API 端点:**

| 端点 | 描述 |
|------|------|
| `GET /api/v1/cases` | 用例列表 (支持标签/优先级筛选) |
| `POST /api/v1/cases` | 创建用例 |
| `POST /api/v1/cases/upload` | 上传用例文件 |
| `POST /api/v1/cases/validate` | 校验用例格式 |
| `GET /api/v1/environments` | 环境配置列表 |
| `POST /api/v1/execution/run` | 异步执行用例 |
| `POST /api/v1/execution/run-sync` | 同步执行用例 |
| `POST /api/v1/execution/batch` | 批量执行 |
| `GET /api/v1/execution/history` | 执行历史 |
| `GET /api/v1/reports` | 报告列表 |
| `POST /api/v1/reports/generate/{id}` | 生成 HTML 报告 |
| `GET /api/v1/reports/summary` | 执行汇总统计 |
| `GET /api/v1/mock/data-factory/types` | 数据工厂类型列表 |

### 启动 Mock 服务

```bash
# 加载 mock/ 目录下所有配置
smartapi mock-server --port 8000

# 指定配置文件
smartapi mock-server -c mock/example_mock.yaml
```

Mock 配置示例 (`mock/example_mock.yaml`):
```yaml
routes:
  - path: "/api/login"
    method: POST
    status_code: 200
    body:
      code: 0
      data: { token: "mock_token" }
    rules:
      - condition:
          body.username: "invalid"
        status_code: 401
        body: { code: 401, msg: "认证失败" }
```

### 敏感信息加密

```bash
# 设置加密密钥 (环境变量)
export SMARTAPI_SECRET_KEY="your_secret_key"
```

在 YAML 中使用加密值:
```yaml
auth:
  type: bearer
  token: "ENC(gAAAAABm...)"  # 加密后的 Token
```

### Docker 部署

```bash
# 构建并启动
docker-compose up -d

# 服务端口:
#   Web API: 8100
#   Mock:    8000
```

## 数据工厂 (50+ 类型)

| 类别 | 类型 |
|------|------|
| 基础 | `string` `int` `float` `bool` `uuid` `timestamp` `date` `datetime` |
| 个人 | `name` `phone` `email` `id_card` `address` `company` `job` |
| 网络 | `ip` `ipv6` `mac` `url` `domain` `user_agent` |
| 文本 | `word` `sentence` `paragraph` `text` |
| 金融 | `credit_card` `bank_account` `amount` |
| 业务 | `order_no` `sku` `barcode` `color_hex` `file_name` |
| 复合 | `list` `dict` `json_object` (JSON Schema) |
| 选项 | `choice` `enum` |

## 通知渠道

```python
from smartapi.notify.notifier import NotifyManager, DingTalkNotifier, FeishuNotifier

manager = NotifyManager()
manager.add_notifier(DingTalkNotifier(webhook_url="https://..."))
manager.add_notifier(FeishuNotifier(webhook_url="https://..."))
manager.set_conditions(on_failure=True, min_failures=1)
manager.notify(total=10, passed=8, failed=2, total_time=30.5)
```

## 插件开发

```python
from smartapi.plugins.base import HookPlugin, PluginMeta, PluginType

class MyPlugin(HookPlugin):
    meta = PluginMeta(name="my_plugin", version="1.0.0", plugin_type=PluginType.HOOK)

    def activate(self, context):
        print("插件已激活")

    def on_request(self, request_kwargs):
        request_kwargs["headers"]["X-Custom"] = "value"
        return request_kwargs
```

## 项目结构

```
smartapi/
├── core/              # 核心引擎
│   ├── models.py      # Pydantic 数据模型
│   ├── parser.py      # YAML/JSON 用例解析器
│   ├── variables.py   # 分层变量系统 + 20+ 内置函数
│   ├── extractor.py   # JSONPath/XPath/Regex/Header 数据提取
│   ├── assertion.py   # 15+ 运算符断言引擎
│   ├── executor.py    # HTTP 执行引擎 (重试/循环/分支/依赖)
│   └── security.py    # 敏感信息 ENC() 加密
├── auth/              # 鉴权处理 (7种鉴权 + Token 缓存)
├── cli/               # CLI 命令行 (run/validate/list/web/mock/mcp/init)
├── mcp_server/        # MCP Server (8 个 AI Tools)
├── mock/              # Mock 数据工厂 + Mock 服务器
├── report/            # HTML 美化报告生成
├── notify/            # 通知 (钉钉/飞书/企微/邮件/WebHook)
├── plugins/           # 插件系统 (Hook/断言/数据生成)
├── web/               # FastAPI REST API
│   ├── app.py         # 应用入口
│   ├── state.py       # 全局状态管理
│   └── routers/       # 路由 (cases/env/execution/reports/mock)
└── pytest_plugin.py   # pytest 集成插件
```

## License

MIT
