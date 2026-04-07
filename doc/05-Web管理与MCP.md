# Web 管理界面与 MCP 集成

> 预计阅读时间：5 分钟 | 掌握 Web UI 操作和 AI 编辑器集成

---

## 目录

1. [Web 管理界面](#1-web-管理界面)
2. [Web API 参考](#2-web-api-参考)
3. [MCP Server 集成](#3-mcp-server-集成)
4. [Docker 部署](#4-docker-部署)
5. [CI/CD 集成](#5-cicd-集成)
6. [常见问题](#6-常见问题)

---

## 1. Web 管理界面

### 启动 Web 服务

```bash
# 基础启动（端口 8100）
smartapi web --port 8100

# 开发模式（代码变更自动重载）
smartapi web --reload

# 开放外部访问
smartapi web --host 0.0.0.0 --port 8100
```

启动后访问 `http://127.0.0.1:8100` 即可使用 Web 管理界面。

### 页面功能一览

| 页面 | 功能 | 入口 |
|------|------|------|
| **仪表盘** | 统计概览、用例列表、最近执行、通过率 | `/` |
| **用例管理** | 用例列表、搜索筛选、查看 YAML 源码、在线执行、删除 | `/cases` |
| **执行管理** | 选择用例执行、批量执行、执行历史、状态筛选、结果详情展开 | `/execution` |
| **测试报告** | 统计概览、HTML 报告列表、查看/下载/生成报告 | `/reports` |
| **环境配置** | 环境列表、新建环境、查看变量和 Base URL | `/environments` |
| **Mock 管理** | Mock 配置查看、数据工厂类型浏览 | `/mock` |

### 典型操作流程

```
1. 打开「用例管理」→ 浏览/搜索用例 → 点击 ▶ 执行
2. 跳转「执行管理」→ 查看执行历史 → 展开查看每个步骤结果
3. 在「测试报告」→ 从执行记录生成 HTML 报告 → 查看/下载
4. 在「环境配置」→ 创建新环境 → 设定 Base URL 和变量
```

### Swagger API 文档

Web 服务自带交互式 API 文档：

- **Swagger UI**: `http://127.0.0.1:8100/docs`
- **ReDoc**: `http://127.0.0.1:8100/redoc`

可直接在浏览器中调试所有 API 接口。

## 2. Web API 参考

所有 API 路径前缀为 `/api/v1`。

### 用例管理

```bash
# 列出用例（支持标签/优先级筛选）
GET /api/v1/cases?tags=smoke&priority=high

# 获取用例详情
GET /api/v1/cases/example_get.yaml

# 创建用例
POST /api/v1/cases
Body: {"filename": "new_case.yaml", "content": "name: test\nsteps: ..."}

# 更新用例
PUT /api/v1/cases/example_get.yaml
Body: {"content": "name: updated\nsteps: ..."}

# 删除用例
DELETE /api/v1/cases/example_get.yaml

# 校验用例格式
POST /api/v1/cases/validate
Body: {"content": "name: test\nsteps:\n  - name: s1\n    request: ..."}

# 上传用例文件
POST /api/v1/cases/upload
Content-Type: multipart/form-data
File: test.yaml
```

### 执行管理

```bash
# 异步执行（立即返回 execution_id）
POST /api/v1/execution/run
Body: {"file": "example_get.yaml", "environment": "dev"}

# 同步执行（等待结果返回）
POST /api/v1/execution/run-sync
Body: {"file": "example_get.yaml", "base_url": "https://httpbin.org"}

# 批量执行
POST /api/v1/execution/batch
Body: {"files": ["case1.yaml", "case2.yaml"]}

# 查询执行状态
GET /api/v1/execution/status/{execution_id}

# 执行历史
GET /api/v1/execution/history?limit=50&status=failed
```

### 报告与环境

```bash
# 报告列表
GET /api/v1/reports

# 从执行记录生成报告
POST /api/v1/reports/generate/{execution_id}

# 查看 HTML 报告
GET /api/v1/reports/view/{report_name.html}

# 执行汇总统计
GET /api/v1/reports/summary

# 环境列表
GET /api/v1/environments

# 创建环境
POST /api/v1/environments
Body: {"name": "staging", "base_url": "https://staging.api.com", "variables": {"key": "val"}}
```

## 3. MCP Server 集成

MCP (Model Context Protocol) 允许 AI 编辑器（Cursor、Windsurf、Claude Desktop 等）直接操作 SmartAPI-Test。

### 启动 MCP Server

```bash
# stdio 模式（Cursor / Claude Desktop 推荐）
smartapi mcp --transport stdio

# SSE 模式（Web 场景）
smartapi mcp --transport sse --port 3000
```

### 配置 AI 编辑器

**Cursor / Windsurf 配置** (`mcp_server_config.json`)：

```json
{
  "mcpServers": {
    "smartapi-test": {
      "command": "python",
      "args": ["-m", "smartapi.cli.main", "mcp", "--transport", "stdio"],
      "cwd": "/path/to/your/apitest/project"
    }
  }
}
```

**Claude Desktop 配置** (`~/.claude/config.json`)：

```json
{
  "mcpServers": {
    "smartapi-test": {
      "command": "python",
      "args": ["-m", "smartapi.cli.main", "mcp", "--transport", "stdio"],
      "cwd": "/path/to/your/apitest/project"
    }
  }
}
```

### MCP 工具列表

配置完成后，AI 助手可以使用以下 8 个工具：

| 工具 | 说明 | 示例对话 |
|------|------|---------|
| `generate_test_case` | 自然语言生成用例 | "帮我生成一个用户登录的测试用例" |
| `validate_test_case` | 校验用例格式 | "帮我检查这个 YAML 用例格式对不对" |
| `list_test_cases` | 列出所有用例 | "列出所有 smoke 标签的测试用例" |
| `run_test_case` | 执行用例 | "执行 example_get.yaml" |
| `analyze_failure` | 分析失败原因 | "分析上次测试失败的原因" |
| `get_yaml_schema` | 获取用例 Schema | "告诉我 YAML 用例都有哪些字段" |
| `import_openapi` | 从 OpenAPI 导入 | "从 swagger.json 生成测试用例" |
| `suggest_improvements` | 优化建议 | "帮我优化这个用例的断言" |

### 使用场景示例

在 AI 编辑器中直接对话：

```
你: 帮我为 /api/users 接口生成完整的 CRUD 测试用例

AI: [调用 generate_test_case] 已生成用例文件 testcases/users_crud.yaml，包含：
    - POST /api/users 创建用户
    - GET /api/users 查询列表
    - GET /api/users/{id} 查询详情
    - PUT /api/users/{id} 更新用户
    - DELETE /api/users/{id} 删除用户

你: 执行一下看看结果

AI: [调用 run_test_case] 执行结果：5 个步骤全部通过，耗时 2.3s

你: 帮我加上分页参数和边界值测试

AI: [调用 suggest_improvements + generate_test_case] 已更新用例，新增：
    - 分页参数测试 (page=0, page=999)
    - 空列表边界
    - 无效 ID 返回 404
```

## 4. Docker 部署

### 快速部署

```bash
# 构建并启动所有服务
docker-compose up -d

# 服务端口：
#   Web API + 前端: 8100
#   Mock 服务:      8000
```

### docker-compose.yaml 说明

```yaml
services:
  smartapi-web:          # Web API + React 前端
    ports: ["8100:8100"]
    volumes:
      - ./testcases:/app/testcases    # 挂载用例目录
      - ./environments:/app/environments
      - ./reports:/app/reports
      - ./mock:/app/mock
    environment:
      - SMARTAPI_SECRET_KEY=${SMARTAPI_SECRET_KEY:-}

  smartapi-mock:         # Mock 服务
    ports: ["8000:8000"]
    volumes:
      - ./mock:/app/mock              # 挂载 Mock 配置
```

### 自定义 Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -e ".[web]"
# 构建前端（如需要）
# RUN cd web && npm install && npm run build
EXPOSE 8100
CMD ["smartapi", "web", "--host", "0.0.0.0", "--port", "8100"]
```

## 5. CI/CD 集成

### GitLab CI

项目已内置 `.gitlab-ci.yml`：

```yaml
test:
  stage: test
  image: python:3.12-slim
  before_script:
    - pip install -e ".[dev]"
  script:
    # 单元测试
    - python -m pytest tests/ -v --junitxml=report.xml
    # 集成测试（真实 HTTP 请求）
    - python -m pytest testcases/ -v --junitxml=integration-report.xml
  artifacts:
    reports:
      junit: [report.xml, integration-report.xml]
```

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: API Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: python -m pytest tests/ -v
      - run: python -m pytest testcases/ -v
```

### Jenkins Pipeline

```groovy
pipeline {
    agent { docker { image 'python:3.12-slim' } }
    stages {
        stage('Install') {
            steps { sh 'pip install -e ".[dev]"' }
        }
        stage('Unit Test') {
            steps { sh 'python -m pytest tests/ -v --junitxml=report.xml' }
        }
        stage('API Test') {
            steps { sh 'python -m pytest testcases/ -v --junitxml=api-report.xml' }
        }
    }
    post {
        always { junit '*.xml' }
    }
}
```

## 6. 常见问题

### Q: 用例中的变量没有被替换？

确保变量语法正确：`${变量名}` 而非 `$变量名` 或 `{{变量名}}`。断言中的 expected 也支持变量引用。

### Q: Mock 服务启动后路由不匹配？

检查 Mock 配置中 `path` 和 `method` 是否与请求完全一致。路径参数使用 `{param_name}` 语法。

### Q: 如何在 CI/CD 中指定环境？

```bash
pytest testcases/ --smartapi-env staging --smartapi-base-url https://staging.api.com
```

### Q: 如何并发执行提高速度？

```bash
# 使用 pytest-xdist
pytest testcases/ -n 4 -v
```

### Q: 如何只执行特定标签的用例？

```bash
smartapi run testcases/ --tags smoke
# 或
pytest testcases/ -v -k "smoke"
```

### Q: 如何生成 Allure 报告？

```bash
pytest testcases/ --alluredir=allure-results
allure serve allure-results
```

---

**恭喜！** 你已完成 SmartAPI-Test 全部教学文档的学习。现在你可以：

- 编写声明式 YAML 测试用例
- 使用变量系统、数据提取、断言引擎
- 配置多步骤编排、分支循环
- 设置鉴权和 Mock 服务
- 通过 Web 管理界面操作
- 集成 AI 编辑器提升效率
- 部署到 Docker 和 CI/CD

有任何问题，欢迎查阅 [API 文档](http://127.0.0.1:8100/docs) 或提交 Issue！
