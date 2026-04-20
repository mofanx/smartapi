---
name: smartapi-test
description: API automated testing with smartapi-test CLI - generate, run, validate and debug YAML test cases
---

# SmartAPI-Test CLI - API Automated Testing

A declarative API testing platform. Use `smartapi` CLI to generate test cases from API docs, run tests, validate YAML, generate mock data, and debug failures — all without MCP.

## Quick Start

```bash
# Initialize project structure
smartapi init

# Generate a test case from description
smartapi generate "Test user login API" -m POST -u /api/login -o testcases/login.yaml

# Validate test case format
smartapi validate testcases/login.yaml

# Run tests
smartapi run testcases/

# Get YAML schema reference (essential before writing test cases)
smartapi schema --format text
```

## Commands

### Test Case Generation

```bash
# Generate from natural language description
smartapi generate "Test user login API" -m POST -u /api/login
smartapi generate "Query product list with pagination" --base-url https://api.example.com
smartapi generate "Test user registration" -m POST -u /api/register -o testcases/register.yaml
smartapi generate "Multi-step checkout flow" --steps 3 -m POST -u /api/order

# Import from OpenAPI/Swagger spec
smartapi import-openapi swagger.json
smartapi import-openapi https://api.example.com/openapi.json
smartapi import-openapi api-spec.yaml --output testcases/ --split
smartapi import-openapi swagger.json --base-url https://api.example.com --tags regression,api
```

### Running Tests

```bash
# Run all test cases
smartapi run testcases/

# Run specific file
smartapi run testcases/login.yaml

# Run with environment config
smartapi run testcases/ --env environments/dev.yaml

# Run with base URL and tags filter
smartapi run testcases/ --base-url https://api.example.com --tags smoke

# Run with workers (parallel)
smartapi run testcases/ --workers 4

# Run and generate HTML report
smartapi report testcases/ --output reports/report.html --title "Regression Report"
smartapi report testcases/ --env environments/prod.yaml
```

### Validation & Inspection

```bash
# Validate YAML format
smartapi validate testcases/
smartapi validate testcases/login.yaml

# List all test cases
smartapi list testcases/

# Inspect test case quality (suggestions for improvement)
smartapi inspect testcases/login.yaml
smartapi inspect testcases/

# Analyze test failures
smartapi analyze "AssertionError: status_code eq 200, actual: 401"
smartapi analyze "ConnectionError: cannot connect" --request "POST /api/login"
```

### YAML Schema Reference

```bash
# Get full YAML schema (use before writing test cases)
smartapi schema
smartapi schema --format text
smartapi schema --format json
```

### Mock Data Generation

```bash
# Generate single value
smartapi data name
smartapi data phone
smartapi data email

# Generate multiple values
smartapi data name --count 10
smartapi data phone -n 5 -f json

# List all available data types (50+)
smartapi data --list-types

# Generate from JSON Schema
smartapi data json_object --schema schema.json
```

### Security (Encrypt/Decrypt)

```bash
# Encrypt sensitive values
smartapi encrypt "my_secret_password"
smartapi encrypt "api_key_value" --key my_master_key

# Decrypt
smartapi decrypt "ENC(gAAAAABf...)"
```

### Environment Management

```bash
# List environments
smartapi env list

# Show environment details
smartapi env show dev
smartapi env show prod
```

### Services

```bash
# Start Mock server
smartapi mock-server
smartapi mock-server --port 8000 --config mock/example_mock.yaml

# Start Web UI
smartapi web
smartapi web --port 8100 --reload

# Start MCP server
smartapi mcp --transport stdio
smartapi mcp --transport sse --port 3000
```

## YAML Test Case Format

A test case YAML file has this structure:

```yaml
name: "Test case name"
description: "What this test does"
tags: [smoke, regression]
base_url: "https://api.example.com"
variables:
  username: "test_user"

steps:
  - name: "Step 1 - Login"
    request:
      method: POST
      url: "/api/login"
      headers:
        Content-Type: "application/json"
      body:
        username: "${username}"
        password: "test_pass"
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

  - name: "Step 2 - Get User Info"
    request:
      method: GET
      url: "/api/user/profile"
      headers:
        Authorization: "Bearer ${token}"
    asserts:
      - target: status_code
        operator: eq
        expected: 200
      - target: body
        expression: "$.data.username"
        operator: eq
        expected: "${username}"
```

### Assert Operators

`eq` `ne` `contains` `not_contains` `starts_with` `ends_with` `gt` `lt` `gte` `lte` `regex` `in` `not_in` `is_null` `is_not_null` `length_eq` `length_gt` `length_lt` `type_is`

### Extract Types

`jsonpath` `xpath` `regex` `header`

### Built-in Variables

`${timestamp()}` `${uuid()}` `${random_int()}` `${random_string()}` `${random_phone()}` `${random_email()}` `${random_name()}` `${random_id_card()}` `${now()}` `${today()}` `${md5(value)}` `${sha256(value)}`

## Workflow: Generate Test Cases from API Documentation

1. Get the YAML schema reference first:
   ```bash
   smartapi schema --format text
   ```

2. If you have an OpenAPI/Swagger spec:
   ```bash
   smartapi import-openapi <spec-file-or-url> --output testcases/ --split
   ```

3. If you have a natural language description:
   ```bash
   smartapi generate "<description>" -m <METHOD> -u <path> -o testcases/<name>.yaml
   ```

4. Inspect and validate generated cases:
   ```bash
   smartapi inspect testcases/<name>.yaml
   smartapi validate testcases/<name>.yaml
   ```

5. Run tests:
   ```bash
   smartapi run testcases/<name>.yaml --env environments/dev.yaml
   ```

6. If tests fail, analyze errors:
   ```bash
   smartapi analyze "<error message>"
   ```

## Specific Workflows

* **Generate test cases from API docs** → [references/generate-testcase.md](references/generate-testcase.md)
* **Import OpenAPI spec** → [references/import-openapi.md](references/import-openapi.md)
* **Run tests and debug failures** → [references/run-and-debug.md](references/run-and-debug.md)
* **Generate mock data** → [references/mock-and-data.md](references/mock-and-data.md)
* **Full YAML schema reference** → [references/yaml-schema.md](references/yaml-schema.md)
