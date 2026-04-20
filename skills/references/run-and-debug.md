# Run Tests and Debug Failures

## Running Tests

### Basic execution

```bash
# Run all test cases in directory
smartapi run testcases/

# Run specific file
smartapi run testcases/login.yaml

# Run with environment
smartapi run testcases/ --env environments/dev.yaml

# Run with base URL override
smartapi run testcases/ --base-url https://staging.example.com

# Run filtered by tags
smartapi run testcases/ --tags smoke
smartapi run testcases/ --tags "regression,api"

# Run with custom timeout
smartapi run testcases/ --timeout 60

# Run in parallel
smartapi run testcases/ --workers 4
```

### Generate reports

```bash
# Run and generate HTML report
smartapi report testcases/ --output reports/report.html

# With title and environment
smartapi report testcases/ --title "Regression Report" --env environments/prod.yaml

# Report for specific test
smartapi report testcases/login.yaml -o reports/login_report.html
```

## Pre-Run Checks

Before running, validate your test cases:

```bash
# Validate format
smartapi validate testcases/

# Check quality
smartapi inspect testcases/

# List all cases
smartapi list testcases/

# Check environment
smartapi env list
smartapi env show dev
```

## Debugging Failures

### Step 1: Analyze the error

```bash
# Analyze error message
smartapi analyze "AssertionError: status_code eq 200, actual: 401"

# With request context
smartapi analyze "timeout error" --request "POST /api/login" --response "status: 504"

# From error file
smartapi analyze "" --file error_log.txt
```

### Step 2: Common failure patterns

| Error Pattern | Likely Cause | Fix |
|---|---|---|
| `status_code eq 200, actual: 401` | Authentication failure | Check auth config, token validity |
| `status_code eq 200, actual: 404` | Wrong URL path | Verify url field matches API |
| `status_code eq 200, actual: 500` | Server error | Check request body format |
| `Connection refused` | Server not running | Verify base_url and server status |
| `Timeout` | Slow response | Increase timeout setting |
| `JSONDecodeError` | Non-JSON response | API may return HTML error page |
| `Variable not found: ${token}` | Missing extraction | Add extract step before reference |

### Step 3: Fix and re-run

```bash
# After fixing the YAML, validate first
smartapi validate testcases/login.yaml

# Then run again
smartapi run testcases/login.yaml --env environments/dev.yaml
```

## Debugging Workflow for AI Tools

When a test fails, follow this sequence:

1. **Read the error output** from `smartapi run`
2. **Analyze** with `smartapi analyze "<error>"`
3. **Inspect** the test case with `smartapi inspect <file>`
4. **Check the YAML** - read the test case file to understand what's being tested
5. **Fix the issue** - usually one of:
   - Wrong URL/method
   - Missing or incorrect request body
   - Wrong assertion expectation
   - Missing authentication
   - Variable reference to non-existent extraction
6. **Validate** with `smartapi validate <file>`
7. **Re-run** with `smartapi run <file>`

## Environment Configuration

Environment files (`environments/*.yaml`) contain:

```yaml
name: "dev"
base_url: "https://dev-api.example.com"
variables:
  api_version: "v1"
  default_timeout: 30
headers:
  X-Custom-Header: "value"
auth:
  type: bearer
  token: "dev-token-here"
```

Manage environments:

```bash
smartapi env list
smartapi env show dev
smartapi env show prod
```
