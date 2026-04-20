# SmartAPI-Test YAML Schema Reference

## Quick Reference

Get the latest schema via CLI:
```bash
smartapi schema --format text
```

## Test Case Structure

```yaml
# Top-level fields
name: string           # REQUIRED - Test case name
description: string    # Optional - Description
tags:                  # Optional - Tags for filtering
  - smoke
  - regression
priority: string       # Optional - high/medium/low (default: medium)
base_url: string       # Optional - Base URL for all requests
variables:             # Optional - Case-level variables
  key: value
auth:                  # Optional - Case-level auth (applied to all steps)
  type: bearer
  token: "xxx"
setup:                 # Optional - Steps run before main steps
  - name: "..."
    request: {...}
steps:                 # REQUIRED - Main test steps
  - name: "..."
    request: {...}
teardown:              # Optional - Steps run after main steps (always runs)
  - name: "..."
    request: {...}
```

## Step Fields

```yaml
steps:
  - id: string              # Optional - Step ID for dependencies
    name: string            # REQUIRED - Step name
    request:                # REQUIRED - HTTP request
      method: GET           # GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS
      url: "/api/path"      # URL (supports ${variable})
      headers:              # Request headers
        Content-Type: "application/json"
        Authorization: "Bearer ${token}"
      params:               # Query parameters
        page: 1
        size: 10
      body:                 # JSON request body
        username: "${username}"
        password: "${password}"
      form_data:            # Form data (mutually exclusive with body)
        field: value
      files:                # File upload
        file: "/path/to/file.pdf"
      cookies:              # Cookies
        session_id: "xxx"
      auth:                 # Step-level auth (overrides case-level)
        type: basic
        username: "user"
        password: "pass"

    extract:                # Data extraction from response
      - name: token         # Variable name to store extracted value
        type: jsonpath      # jsonpath/xpath/regex/header
        expression: "$.data.token"
        default: null       # Default if extraction fails

    asserts:                # Assertions
      - target: status_code # status_code/header/body/response_time/custom
        expression: null    # JSONPath expression (for body) or header name
        operator: eq        # Comparison operator
        expected: 200       # Expected value
        level: error        # warning/error/fatal
        message: ""         # Custom failure message
        script: ""          # Python script assertion

    variables:              # Step-level variables
      local_var: "value"

    retry: 3                # Retry count on failure
    # OR dict format:
    # retry:
    #   max_retries: 3
    #   retry_interval: 2
    retry_interval: 1.0     # Seconds between retries
    timeout: 30.0           # Request timeout in seconds

    skip_if:                # Conditional skip
      variable: "env"
      operator: eq          # eq/ne/neq/contains/gt/lt/exists/not_exists
      value: "production"

    depends_on:             # Step dependencies (skip if dependency failed)
      - step_1_id
      - step_2_id

    loop:                   # Loop execution
      times: 5              # Fixed iterations
      # OR condition loop:
      # condition:
      #   variable: "status"
      #   operator: eq
      #   value: "ready"
      max_iterations: 100
      interval: 1.0         # Seconds between iterations

    branch:                 # Conditional branching
      condition:
        variable: "user_type"
        operator: eq
        value: "admin"
      then_steps: [admin_step_id]
      else_steps: [user_step_id]
```

## Assert Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equals | `expected: 200` |
| `ne` / `neq` | Not equals | `expected: 0` |
| `contains` | Contains substring | `expected: "success"` |
| `not_contains` | Does not contain | `expected: "error"` |
| `starts_with` | Starts with | `expected: "Bearer"` |
| `ends_with` | Ends with | `expected: ".json"` |
| `gt` | Greater than | `expected: 0` |
| `lt` | Less than | `expected: 500` |
| `gte` | Greater than or equal | `expected: 1` |
| `lte` | Less than or equal | `expected: 100` |
| `regex` | Regex match | `expected: "^\\d{11}$"` |
| `in` | In list | `expected: [200, 201]` |
| `not_in` | Not in list | `expected: [400, 500]` |
| `is_null` | Is null/None | (no expected needed) |
| `is_not_null` | Is not null | (no expected needed) |
| `length_eq` | Length equals | `expected: 10` |
| `length_gt` | Length greater than | `expected: 0` |
| `length_lt` | Length less than | `expected: 100` |
| `type_is` | Type check | `expected: "str"` / `"int"` / `"list"` / `"dict"` |

## Assert Targets

| Target | Description | Expression |
|--------|-------------|------------|
| `status_code` | HTTP status code | Not needed |
| `body` | Response body | JSONPath: `$.data.id` |
| `header` | Response header | Header name: `Content-Type` |
| `response_time` | Response time (ms) | Not needed |
| `custom` | Custom script | Use `script` field |

## Extract Types

| Type | Description | Expression Example |
|------|-------------|-------------------|
| `jsonpath` | JSONPath extraction | `$.data.token` |
| `xpath` | XPath extraction (XML) | `//user/name/text()` |
| `regex` | Regex extraction | `"token":"([^"]+)"` |
| `header` | Response header | `Set-Cookie` |

## Built-in Variable Functions

| Function | Description | Example |
|----------|-------------|---------|
| `${timestamp()}` | Unix timestamp | `1712345678` |
| `${uuid()}` | UUID v4 | `a1b2c3d4-...` |
| `${random_int()}` | Random integer | `42` |
| `${random_string()}` | Random string | `aB3xY9` |
| `${random_phone()}` | Random phone | `13800138000` |
| `${random_email()}` | Random email | `user@example.com` |
| `${random_name()}` | Random name | `张三` |
| `${random_id_card()}` | Random ID card | `110101...` |
| `${now()}` | Current datetime | `2024-01-01 12:00:00` |
| `${today()}` | Current date | `2024-01-01` |
| `${md5(value)}` | MD5 hash | `e10adc...` |
| `${sha256(value)}` | SHA256 hash | `8d969e...` |

## Auth Configuration

```yaml
# Bearer Token
auth:
  type: bearer
  token: "your-token"

# Basic Auth
auth:
  type: basic
  username: "user"
  password: "pass"

# API Key (in header)
auth:
  type: api_key
  api_key_name: "X-API-Key"
  api_key_value: "your-key"
  api_key_in: header  # or: query

# Token auto-fetch
auth:
  type: token
  token_url: "/api/auth/token"
  username: "user"
  password: "pass"
  token_field: "data.token"
  token_prefix: "Bearer"
```

## Test Suite Format (Multiple Cases)

```yaml
name: "API Test Suite"
description: "Complete API test suite"
tags: [regression]
variables:
  global_var: "value"

test_cases:
  - name: "Test Case 1"
    tags: [smoke]
    steps:
      - name: "Step 1"
        request:
          method: GET
          url: "/api/health"
        asserts:
          - target: status_code
            operator: eq
            expected: 200

  - name: "Test Case 2"
    steps:
      - name: "Step 1"
        request:
          method: POST
          url: "/api/data"
          body:
            key: "value"
        asserts:
          - target: status_code
            operator: eq
            expected: 201
```
