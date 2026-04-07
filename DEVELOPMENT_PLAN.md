# SmartAPI-Test 开发计划

## 项目概述
智能声明式 API 自动化测试平台，基于 Python + pytest，集成 MCP 服务。

## 技术栈
- **语言**: Python 3.10+
- **测试框架**: pytest 8.0+
- **HTTP**: httpx (异步支持)
- **YAML/JSON**: pyyaml, jsonschema
- **数据提取**: jsonpath-ng, lxml (XPath)
- **Mock数据**: faker
- **MCP**: mcp sdk
- **Web UI**: FastAPI + React (后期)
- **报告**: Allure, Jinja2 HTML
- **通知**: requests (钉钉/飞书/企微)
- **CLI**: click
- **包管理**: uv

## 开发阶段

### Phase 1: 核心基础架构 ✅
- [x] 项目结构搭建
- [x] pyproject.toml 配置
- [x] YAML/JSON 用例解析器 (`smartapi/core/parser.py`)
- [x] 变量系统 (`smartapi/core/variables.py`) - 全局/环境/用例/步骤/提取变量 + 内置函数
- [x] HTTP 执行引擎 (`smartapi/core/executor.py`)
- [x] 断言引擎 (`smartapi/core/assertion.py`) - 15+ 运算符
- [x] pytest 插件 (`smartapi/pytest_plugin.py`)
- [x] CLI 基础命令 (`smartapi/cli/main.py`) - run/validate/list/init/mcp
- [x] 基础单元测试 (66 tests)

### Phase 2: 高级用例编排 ✅
- [x] 多步骤用例串联 + 数据流转
- [x] 数据提取 (`smartapi/core/extractor.py`) - JSONPath/XPath/正则/Header
- [x] 分支逻辑 (BranchConfig)
- [x] 循环逻辑 (LoopConfig) - 固定次数/条件循环
- [x] 步骤依赖/跳过 (depends_on / skip_if)
- [x] 动态变量 - timestamp/uuid/random_*/md5/sha256 等 20+ 内置函数
- [x] 集成测试 (executor tests)

### Phase 3: 鉴权与协议适配 ✅
- [x] Token 自动获取/刷新/缓存 (`smartapi/auth/handler.py`)
- [x] Basic Auth / Bearer / OAuth2 / JWT / API Key
- [x] 自定义鉴权脚本 (签名算法)
- [x] 文件上传/下载 (FormData)
- [x] 鉴权单元测试

### Phase 4: AI/MCP 集成 ✅
- [x] MCP Server (`smartapi/mcp_server/server.py`) - stdio + SSE 传输
- [x] generate_test_case - 自然语言生成用例
- [x] validate_test_case - 用例校验
- [x] import_openapi - OpenAPI/Swagger 导入
- [x] suggest_improvements - 用例优化建议
- [x] analyze_failure - AI 故障定位
- [x] run_test_case - 远程执行用例
- [x] get_yaml_schema - Schema 文档
- [x] list_test_cases - 用例列表

### Phase 5: Mock 服务与数据工厂 ✅
- [x] Mock 数据生成器 (`smartapi/mock/data_factory.py`) - 50+ 数据类型
- [x] Mock 服务器 (`smartapi/mock/server.py`) - 声明式 YAML 配置 + 动态规则
- [x] 测试数据池 - random/sequential/unique 模式 + 占用/释放
- [x] JSON Schema 风格数据生成
- [x] 数据工厂单元测试

### Phase 6: 报告与通知 ✅
- [x] HTML 美化报告 (`smartapi/report/html_report.py`) - 渐变头部/进度条/折叠详情
- [x] Allure 集成 (通过 allure-pytest)
- [x] 钉钉通知 (Markdown + 签名)
- [x] 飞书通知 (卡片消息)
- [x] 企业微信通知 (Markdown)
- [x] 邮件通知 (SMTP + HTML)
- [x] WebHook 通知
- [x] 通知管理器 + 触发条件配置

### Phase 7: 插件系统 ✅
- [x] 插件基类体系 (`smartapi/plugins/base.py`)
- [x] Hook 插件 - 测试/步骤/请求/响应生命周期钩子
- [x] 断言插件 - 自定义断言逻辑
- [x] 数据生成插件
- [x] 插件管理器 - 注册/注销/动态加载
- [x] 插件单元测试

### Phase 8: Web + 安全 + 部署 ✅
- [x] FastAPI 后端 REST API (`smartapi/web/`) - 5 个路由模块
  - 用例管理 (CRUD + 上传 + 校验)
  - 环境配置管理
  - 执行管理 (同步/异步/批量 + 历史查询)
  - 报告管理 (查看/下载/生成 + 汇总统计)
  - Mock 管理 (配置 + 数据工厂)
- [x] 敏感信息加密 (`smartapi/core/security.py`) - ENC() 格式 + PBKDF2 密钥派生
- [x] Docker 部署 (Dockerfile + docker-compose.yaml)
- [x] CI/CD 配置示例 (.gitlab-ci.yml)
- [x] MCP Server 配置示例 (mcp_server_config.json)

### Phase 9: React 前端 Web UI ✅
- [x] Vite + React + TypeScript + TailwindCSS v4 项目搭建
- [x] 仪表盘页面 - 统计卡片/用例列表/最近执行/通过率进度条
- [x] 用例管理页面 - 列表/标签筛选/详情查看/在线执行/删除
- [x] 执行管理页面 - 执行面板/批量执行/历史/状态筛选/结果展开
- [x] 测试报告页面 - 统计概览/报告列表/生成报告/查看下载
- [x] 环境配置页面 - 环境列表/创建/详情/变量查看
- [x] Mock 管理页面 - 配置查看/数据工厂类型浏览
- [x] Vite API 代理 + FastAPI SPA 静态文件服务
- [x] 前后端生产集成 (npm build → FastAPI 提供 dist/)

### Phase 10: 教学文档与示例 ✅
- [x] 快速入门指南 (`doc/01-快速入门.md`)
- [x] YAML 用例编写详解 (`doc/02-用例编写详解.md`)
- [x] 高级功能详解 (`doc/03-高级功能.md`)
- [x] 鉴权与 Mock 服务 (`doc/04-鉴权与Mock.md`)
- [x] Web 管理与 MCP 集成 (`doc/05-Web管理与MCP.md`)
- [x] 配套教学示例用例集 (`doc/examples/`)

### Phase 11: 待规划 (后续迭代)
- [ ] 定时任务调度
- [ ] Git 集成 (用例版本管理)
- [ ] 缺陷管理对接 (Jira/禅道)
- [ ] 权限与团队协作
- [ ] 分布式执行 (pytest-xdist + 自定义调度)

## 测试覆盖
| 测试模块 | 测试数 | 状态 |
|---------|--------|------|
| test_variables.py | 16 | ✅ |
| test_parser.py | 11 | ✅ |
| test_assertion.py | 21 | ✅ |
| test_extractor.py | 15 | ✅ |
| test_executor.py | 10 | ✅ |
| test_auth.py | 10 | ✅ |
| test_data_factory.py | 28 | ✅ |
| test_plugins.py | 12 | ✅ |
| test_security.py | 10 | ✅ |
| Web API 集成验证 | 7 端点 | ✅ |
| YAML 集成测试 | 2 | ✅ |
| **合计** | **145+** | **全部通过** |

## 变更记录
| 日期 | 变更内容 | 阶段 |
|------|---------|------|
| 2026-03-10 | 项目初始化，完成 Phase 1-7 核心功能 | Phase 1-7 |
| 2026-03-10 | Web API + 安全加密 + Docker + CI/CD | Phase 8 |
| 2026-03-10 | React 前端 Web UI 完成 | Phase 9 |
| 2026-03-10 | 教学文档与示例用例集 | Phase 10 |
