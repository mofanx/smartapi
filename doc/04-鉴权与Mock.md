# 鉴权与 Mock 服务

> 预计阅读时间：10 分钟 | 掌握 7 种鉴权方式和 Mock 服务的声明式配置

---

## 目录

1. [鉴权类型总览](#1-鉴权类型总览)
2. [各鉴权方式详解](#2-各鉴权方式详解)
3. [Token 自动管理](#3-token-自动管理)
4. [Mock 服务器](#4-mock-服务器)
5. [数据工厂](#5-数据工厂)
6. [测试数据池](#6-测试数据池)

---

## 1. 鉴权类型总览

| 类型 | 说明 | 适用场景 |
|------|------|---------|
| `basic` | HTTP Basic Auth | 内部管理后台 |
| `bearer` | Bearer Token | 通用 REST API |
| `token` | 自动获取+缓存 Token | 需要登录获取 Token |
| `api_key` | API Key 鉴权 | 第三方开放平台 |
| `jwt` | JWT Token | 微服务鉴权 |
| `oauth2` | OAuth2 Client Credentials | SSO / 第三方授权 |
| `custom` | 自定义脚本 | 签名算法等特殊场景 |

## 2. 各鉴权方式详解

### Basic Auth

```yaml
steps:
  - name: "Basic Auth 登录"
    request:
      method: GET
      url: "/api/admin/dashboard"
      auth:
        type: basic
        username: "admin"
        password: "password123"
```

### Bearer Token

```yaml
steps:
  - name: "Bearer Token 请求"
    request:
      method: GET
      url: "/api/protected/resource"
      auth:
        type: bearer
        token: "eyJhbGciOiJIUzI1NiJ9..."
```

### API Key

```yaml
steps:
  # API Key 放在 Header
  - name: "API Key (Header)"
    request:
      method: GET
      url: "/api/data"
      auth:
        type: api_key
        api_key_name: "X-API-Key"
        api_key_value: "sk-abc123def456"
        api_key_in: "header"     # header (默认)

  # API Key 放在 Query 参数
  - name: "API Key (Query)"
    request:
      method: GET
      url: "/api/data"
      auth:
        type: api_key
        api_key_name: "apikey"
        api_key_value: "sk-abc123def456"
        api_key_in: "query"
```

### JWT Token

```yaml
steps:
  - name: "JWT 鉴权"
    request:
      method: GET
      url: "/api/secure"
      auth:
        type: jwt
        token: "${jwt_token}"
        jwt_header_prefix: "Bearer"  # 默认 Bearer
```

### OAuth2 Client Credentials

```yaml
steps:
  - name: "OAuth2 鉴权"
    request:
      method: GET
      url: "/api/resource"
      auth:
        type: oauth2
        token_url: "https://auth.example.com/oauth/token"
        client_id: "my_client_id"
        client_secret: "my_client_secret"
        scope: "read write"
```

### 自定义脚本鉴权

```yaml
steps:
  - name: "自定义签名鉴权"
    request:
      method: POST
      url: "/api/partner/data"
      auth:
        type: custom
        custom_script: |
          import hashlib, time
          ts = str(int(time.time()))
          app_key = "my_app_key"
          secret = "my_secret"
          raw = f"{app_key}{ts}{secret}"
          sign = hashlib.md5(raw.encode()).hexdigest()
          request_kwargs["headers"]["X-App-Key"] = app_key
          request_kwargs["headers"]["X-Timestamp"] = ts
          request_kwargs["headers"]["X-Sign"] = sign
```

## 3. Token 自动管理

对于需要登录获取 Token 的场景，使用 `token` 类型实现自动获取和缓存：

```yaml
steps:
  - name: "自动获取 Token 并请求"
    request:
      method: GET
      url: "/api/user/info"
      auth:
        type: token

        # Token 获取配置
        token_url: "https://api.example.com/auth/login"
        token_method: "POST"        # 获取 Token 的 HTTP 方法
        token_body:                 # 获取 Token 的请求体
          username: "admin"
          password: "password123"
        token_headers:              # 获取 Token 的请求头
          Content-Type: "application/json"

        # Token 提取配置
        token_jsonpath: "$.data.access_token"  # 从响应中提取 Token

        # Token 携带方式
        token_header: "Authorization"   # 放在哪个 Header
        token_prefix: "Bearer"          # 前缀

        # 缓存配置
        token_cache_ttl: 3600     # 缓存有效期（秒），默认 3600
```

**工作原理：**
```
第一次请求 → 发现无缓存 Token → 调用 token_url 获取 → 缓存 → 附加到请求头
后续请求 → 发现缓存有效 → 直接使用缓存 Token → 附加到请求头
缓存过期 → 重新获取 → 更新缓存
```

### 多步骤共享 Token

```yaml
name: "共享 Token 流程"
steps:
  - id: "login"
    name: "获取 Token"
    request:
      method: POST
      url: "/auth/login"
      body:
        username: "admin"
        password: "123456"
    extract:
      - name: access_token
        type: jsonpath
        expression: "$.data.token"

  - name: "接口1 - 使用提取的 Token"
    request:
      method: GET
      url: "/api/resource1"
      auth:
        type: bearer
        token: "${access_token}"

  - name: "接口2 - 同样使用"
    request:
      method: GET
      url: "/api/resource2"
      auth:
        type: bearer
        token: "${access_token}"
```

## 4. Mock 服务器

当被测接口尚未开发完成或需要模拟特定场景时，使用 Mock 服务器。

### 启动 Mock 服务

```bash
# 加载 mock/ 目录下所有配置
smartapi mock-server --port 8000

# 指定配置文件
smartapi mock-server -c mock/my_mock.yaml --port 8000
```

### Mock 配置文件 (YAML)

创建 `mock/user_api.yaml`：

```yaml
routes:
  # 基础路由：固定响应
  - path: "/api/login"
    method: POST
    status_code: 200
    headers:
      Content-Type: "application/json"
    body:
      code: 0
      msg: "success"
      data:
        token: "mock_token_abc123"
        expires_in: 7200

  # 带动态规则的路由
  - path: "/api/users"
    method: GET
    status_code: 200
    body:
      code: 0
      data:
        total: 2
        list:
          - { id: 1, name: "张三", role: "admin" }
          - { id: 2, name: "李四", role: "user" }
    rules:
      # 规则1：当 query.role=admin 时返回不同数据
      - condition:
          query.role: "admin"
        status_code: 200
        body:
          code: 0
          data:
            total: 1
            list:
              - { id: 1, name: "张三", role: "admin" }

      # 规则2：当 query.page > 10 时返回空列表
      - condition:
          query.page: "999"
        body:
          code: 0
          data: { total: 0, list: [] }

  # 带路径参数的路由
  - path: "/api/users/{user_id}"
    method: GET
    status_code: 200
    body:
      code: 0
      data:
        id: 1
        name: "Mock User"
    rules:
      # 用户不存在
      - condition:
          path.user_id: "999"
        status_code: 404
        body:
          code: 404
          msg: "用户不存在"

  # 模拟慢接口
  - path: "/api/slow"
    method: GET
    delay: 3          # 延迟 3 秒响应
    status_code: 200
    body: { msg: "slow response" }

  # 模拟错误
  - path: "/api/error"
    method: GET
    status_code: 500
    body:
      code: 500
      msg: "Internal Server Error"
```

### 用例中指向 Mock 服务

```yaml
name: "使用 Mock 服务测试"
base_url: "http://127.0.0.1:8000"   # Mock 服务地址

steps:
  - name: "登录"
    request:
      method: POST
      url: "/api/login"
      body: { username: "admin", password: "123" }
    extract:
      - name: token
        type: jsonpath
        expression: "$.data.token"
    asserts:
      - target: body
        expression: "$.data.token"
        operator: is_not_null
```

## 5. 数据工厂

数据工厂提供 50+ 内置数据类型，用于生成测试数据。

### Python 代码中使用

```python
from smartapi.mock.data_factory import DataFactory

factory = DataFactory()

# 基础类型
factory.generate("name")        # → "张三"
factory.generate("phone")       # → "13812345678"
factory.generate("email")       # → "abc@example.com"
factory.generate("id_card")     # → "110101199001011234"
factory.generate("uuid")        # → "a1b2c3d4-..."
factory.generate("ip")          # → "192.168.1.100"
factory.generate("url")         # → "https://example.com"
factory.generate("date")        # → "2026-03-10"
factory.generate("datetime")    # → "2026-03-10T12:00:00"
factory.generate("company")     # → "科技有限公司"
factory.generate("address")     # → "北京市朝阳区..."
factory.generate("amount")      # → 99.99

# 生成复合数据
user = factory.generate_from_schema({
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string", "generator": "name"},
        "email": {"type": "string", "generator": "email"},
        "age": {"type": "integer", "minimum": 18, "maximum": 65},
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 2}
    }
})
# → {"id": 42, "name": "李四", "email": "abc@x.com", "age": 28, "tags": ["a", "b"]}
```

### 通过 Web API 使用

```bash
# 查看支持的数据类型
curl http://127.0.0.1:8100/api/v1/mock/data-factory/types

# 生成数据
curl "http://127.0.0.1:8100/api/v1/mock/data-factory/generate?type_name=phone&count=5"
```

### 支持的数据类型一览

| 类别 | 类型 |
|------|------|
| **基础** | `string` `int` `float` `bool` `uuid` `timestamp` `date` `datetime` |
| **个人** | `name` `phone` `email` `id_card` `address` `company` `job` `ssn` |
| **网络** | `ip` `ipv6` `mac` `url` `domain` `user_agent` |
| **文本** | `word` `sentence` `paragraph` `text` |
| **金融** | `credit_card` `bank_account` `amount` `currency` |
| **业务** | `order_no` `sku` `barcode` `color_hex` `file_name` `mime_type` |
| **地理** | `latitude` `longitude` `country` `city` `zipcode` |

## 6. 测试数据池

数据池用于管理一组测试数据，支持多种分配策略：

```python
from smartapi.mock.data_factory import DataFactory

factory = DataFactory()

# 创建数据池
factory.create_pool("test_users", [
    {"username": "user1", "password": "pass1"},
    {"username": "user2", "password": "pass2"},
    {"username": "user3", "password": "pass3"},
])

# 随机获取（默认模式，可重复）
user = factory.get_from_pool("test_users", mode="random")

# 顺序获取（循环）
user = factory.get_from_pool("test_users", mode="sequential")

# 唯一获取（用完不再分配，适合并发测试）
user = factory.get_from_pool("test_users", mode="unique")

# 归还数据（唯一模式下归还后可再分配）
factory.release_to_pool("test_users", user)

# 查看数据池状态
info = factory.pool_info("test_users")
# → {"name": "test_users", "total": 3, "available": 2, "occupied": 1}
```

### 在 conftest.py 中配置数据池

```python
# conftest.py
import pytest
from smartapi.mock.data_factory import DataFactory

@pytest.fixture(scope="session")
def data_factory():
    factory = DataFactory()

    # 预置测试账号池
    factory.create_pool("accounts", [
        {"user": "test01", "pass": "Test@001"},
        {"user": "test02", "pass": "Test@002"},
        {"user": "test03", "pass": "Test@003"},
    ])

    return factory
```

> **下一篇：** [05-Web管理与MCP](05-Web管理与MCP.md) — 学习 Web 管理界面和 AI 编辑器集成
