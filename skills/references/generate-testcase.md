# Generate Test Cases from API Documentation

## Overview

This workflow covers generating SmartAPI-Test YAML test cases from API documentation, natural language descriptions, or OpenAPI specs.

## Step 1: Get the YAML Schema

Before generating any test case, always get the schema reference:

```bash
smartapi schema --format text
```

This outputs the complete YAML structure including all fields, operators, and built-in variables.

## Step 2: Generate from Description

For a single API endpoint:

```bash
# Simple GET endpoint
smartapi generate "Get user list" -m GET -u /api/users -o testcases/get_users.yaml

# POST with body
smartapi generate "Create new user" -m POST -u /api/users -o testcases/create_user.yaml

# Multi-step flow
smartapi generate "Login then get profile" --steps 2 -m POST -u /api/login -o testcases/login_flow.yaml

# With base URL
smartapi generate "Test payment API" -m POST -u /api/payment --base-url https://api.example.com -o testcases/payment.yaml
```

## Step 3: Refine the Generated YAML

The generated YAML is a template. You need to:

1. **Set correct request body** - Replace placeholder `key: value` with actual API parameters
2. **Add data extraction** - Extract tokens, IDs, etc. for use in subsequent steps
3. **Add meaningful assertions** - Verify status code, response body fields, response time
4. **Add variables** - Use `${variable}` syntax for dynamic values

### Example: Refining a login test case

Generated template:
```yaml
steps:
  - name: "步骤1 - 测试用户登录"
    request:
      method: POST
      url: /api/login
      headers:
        Content-Type: application/json
      body:
        key: value
    asserts:
      - target: status_code
        operator: eq
        expected: 200
```

Refined version:
```yaml
variables:
  username: "testuser"
  password: "Test@123"

steps:
  - name: "用户登录"
    request:
      method: POST
      url: /api/login
      headers:
        Content-Type: application/json
      body:
        username: "${username}"
        password: "${password}"
    extract:
      - name: token
        type: jsonpath
        expression: "$.data.token"
      - name: user_id
        type: jsonpath
        expression: "$.data.user_id"
    asserts:
      - target: status_code
        operator: eq
        expected: 200
      - target: body
        expression: "$.code"
        operator: eq
        expected: 0
      - target: body
        expression: "$.data.token"
        operator: is_not_null
      - target: response_time
        operator: lt
        expected: 500
```

## Step 4: Generate from OpenAPI

If you have an OpenAPI/Swagger specification:

```bash
# From local file
smartapi import-openapi swagger.json --output testcases/ --split

# From URL
smartapi import-openapi https://api.example.com/v3/api-docs --output testcases/

# With custom base URL
smartapi import-openapi swagger.json --base-url https://staging.example.com --split
```

The `--split` flag creates one file per endpoint, which is easier to manage.

## Step 5: Validate and Inspect

```bash
# Check format validity
smartapi validate testcases/login.yaml

# Get quality suggestions
smartapi inspect testcases/login.yaml
```

Common suggestions from `inspect`:
- Missing `description` field
- Missing `tags` for filtering
- Missing status code assertions
- Missing response body assertions
- Missing response time assertions
- POST/PUT without request body

## Step 6: Run and Iterate

```bash
# Run the test
smartapi run testcases/login.yaml --env environments/dev.yaml

# If it fails, analyze
smartapi analyze "the error message from the test output"
```

## Tips for AI-Assisted Generation

When an AI tool needs to generate test cases:

1. **First call** `smartapi schema --format text` to understand the YAML format
2. **Read the API documentation** (Swagger/OpenAPI JSON, markdown docs, or user description)
3. **Generate the YAML file** directly following the schema, or use `smartapi generate` as a starting template
4. **Validate** with `smartapi validate <file>`
5. **Inspect** with `smartapi inspect <file>` for quality checks
6. **Run** with `smartapi run <file>` to verify

### Key conventions:
- Use `${variable}` for variable references
- Use `$.path.to.field` JSONPath for body assertions
- Always include `status_code` assertion
- Extract values needed by subsequent steps
- Use `depends_on` for step dependencies
- Use `skip_if` for conditional execution
