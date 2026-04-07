# SmartAPI-Test 教学文档

> 一小时入门并熟练使用 SmartAPI-Test 智能声明式 API 自动化测试平台

---

## 学习路线图

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 01-快速入门   │ →  │ 02-用例编写   │ →  │ 03-高级功能   │ →  │ 04-鉴权Mock  │ →  │ 05-Web与MCP  │
│   15 分钟     │    │   15 分钟     │    │   15 分钟     │    │   10 分钟     │    │   5 分钟      │
│              │    │              │    │              │    │              │    │              │
│ · 安装配置    │    │ · 请求方法    │    │ · 变量系统    │    │ · 7种鉴权    │    │ · Web UI     │
│ · 第一个用例  │    │ · 断言运算符  │    │ · 内置函数    │    │ · Mock服务   │    │ · MCP集成    │
│ · 执行方式    │    │ · 数据提取    │    │ · 多步骤编排  │    │ · 数据工厂   │    │ · Docker     │
│ · 查看结果    │    │ · 环境配置    │    │ · 分支/循环   │    │ · 数据池     │    │ · CI/CD      │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                                 总计 ≈ 1 小时
```

## 文档目录

| # | 文档 | 内容 | 预计时间 |
|---|------|------|---------|
| 1 | [快速入门](01-快速入门.md) | 安装、初始化、第一个用例、三种执行方式 | 15 分钟 |
| 2 | [用例编写详解](02-用例编写详解.md) | HTTP 方法、参数、断言运算符全表、数据提取、环境配置 | 15 分钟 |
| 3 | [高级功能](03-高级功能.md) | 变量系统、内置函数、多步骤编排、分支循环、插件、加密 | 15 分钟 |
| 4 | [鉴权与 Mock](04-鉴权与Mock.md) | 7 种鉴权方式、Mock 服务器、数据工厂(50+类型)、数据池 | 10 分钟 |
| 5 | [Web 管理与 MCP](05-Web管理与MCP.md) | Web UI 操作、REST API、MCP 集成 AI、Docker、CI/CD | 5 分钟 |

## 配套示例用例

所有示例均可直接执行（使用 httpbin.org 作为目标服务）：

```bash
# 执行全部示例
smartapi run doc/examples/

# 或
pytest doc/examples/ -v
```

| # | 示例文件 | 学习内容 | 难度 |
|---|---------|---------|------|
| 1 | [01_hello_world.yaml](examples/01_hello_world.yaml) | 最简 GET 请求 | ★☆☆ |
| 2 | [02_post_json.yaml](examples/02_post_json.yaml) | POST JSON 请求体 | ★☆☆ |
| 3 | [03_assertions_showcase.yaml](examples/03_assertions_showcase.yaml) | 15+ 断言运算符全量演示 | ★★☆ |
| 4 | [04_multi_step_extract.yaml](examples/04_multi_step_extract.yaml) | 多步骤数据提取与传递 | ★★☆ |
| 5 | [05_dynamic_variables.yaml](examples/05_dynamic_variables.yaml) | 动态变量与内置函数 | ★★☆ |
| 6 | [06_auth_demo.yaml](examples/06_auth_demo.yaml) | Basic Auth 和 Bearer Token | ★★☆ |
| 7 | [07_dependency_skip.yaml](examples/07_dependency_skip.yaml) | 步骤依赖与条件跳过 | ★★★ |
| 8 | [08_loop_retry.yaml](examples/08_loop_retry.yaml) | 循环与重试机制 | ★★★ |
| 9 | [09_full_workflow.yaml](examples/09_full_workflow.yaml) | 完整业务流程综合演示 | ★★★ |
| 10 | [10_test_suite.yaml](examples/10_test_suite.yaml) | 测试套件组织 | ★★☆ |

## 快速参考卡片

### 断言运算符速查

```
eq / neq        等于 / 不等于
gt / gte        大于 / 大于等于
lt / lte        小于 / 小于等于
contains        包含子串
not_contains    不包含
starts_with     以...开头
ends_with       以...结尾
regex           正则匹配
in / not_in     在列表中 / 不在列表中
is_null         为 null
is_not_null     非 null
type_is         类型检查 (int/str/list/dict/bool/float)
length_eq       长度等于
length_gt       长度大于
length_lt       长度小于
```

### 内置函数速查

```
${timestamp()}      Unix 时间戳
${uuid()}           UUID v4
${now()}            当前时间
${random_int()}     随机整数
${random_phone()}   随机手机号
${random_email()}   随机邮箱
${random_name()}    随机姓名
${random_id_card()} 随机身份证
${md5(value)}       MD5 哈希
${base64_encode(v)} Base64 编码
```

### CLI 命令速查

```bash
smartapi init                    # 初始化项目
smartapi run testcases/          # 执行用例
smartapi run testcases/ --tags smoke  # 按标签筛选
smartapi run testcases/ --env dev     # 指定环境
smartapi validate testcases/     # 校验格式
smartapi list testcases/         # 列出用例
smartapi web --port 8100         # 启动 Web 服务
smartapi mock-server --port 8000 # 启动 Mock 服务
smartapi mcp --transport stdio   # 启动 MCP Server
```
