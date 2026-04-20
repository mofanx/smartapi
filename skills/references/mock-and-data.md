# Mock Data Generation

## Generate Test Data via CLI

### Single values

```bash
smartapi data name          # Random Chinese name
smartapi data phone         # Random phone number
smartapi data email         # Random email
smartapi data id_card       # Random ID card number
smartapi data uuid          # UUID
smartapi data ip            # IPv4 address
smartapi data url           # Random URL
smartapi data address       # Random address
smartapi data company       # Random company name
smartapi data order_no      # Order number (ORD + timestamp + random)
```

### Multiple values

```bash
smartapi data name --count 10
smartapi data phone -n 5 -f json
smartapi data email -n 20 -f csv
```

### Output formats

```bash
# Plain text (default)
smartapi data name -n 3
# Output:
#   1. 张三
#   2. 李四
#   3. 王五

# JSON format
smartapi data name -n 3 -f json
# Output: ["张三", "李四", "王五"]

# CSV format (one per line)
smartapi data name -n 3 -f csv
```

### List all 50+ data types

```bash
smartapi data --list-types
```

Available types include:

| Category | Types |
|----------|-------|
| **Basic** | `string`, `int`, `float`, `bool`, `uuid`, `timestamp`, `timestamp_ms`, `date`, `datetime`, `time` |
| **Personal** | `name`, `first_name`, `last_name`, `phone`, `email`, `id_card`, `address`, `city`, `province`, `postcode`, `company`, `job` |
| **Network** | `ip`, `ipv6`, `mac`, `url`, `domain`, `user_agent` |
| **Text** | `word`, `sentence`, `paragraph`, `text` |
| **Finance** | `credit_card`, `bank_account`, `amount` |
| **Encoding** | `md5`, `sha256`, `base64` |
| **Selection** | `choice`, `enum` |
| **Composite** | `list`, `dict`, `json_object` |
| **Business** | `order_no`, `sku`, `barcode`, `color_hex`, `file_name` |

### Generate from JSON Schema

Create a schema file:
```json
{
  "type": "object",
  "properties": {
    "username": {"type": "string", "generator": "name"},
    "email": {"type": "string", "generator": "email"},
    "age": {"type": "integer", "min": 18, "max": 65},
    "phone": {"type": "string", "generator": "phone"},
    "tags": {
      "type": "array",
      "items": {"type": "string", "generator": "word"},
      "count": 3
    }
  }
}
```

```bash
smartapi data json_object --schema user_schema.json -n 5 -f json
```

### Locale support

```bash
# Chinese (default)
smartapi data name --locale zh_CN

# English
smartapi data name --locale en_US

# Japanese
smartapi data name --locale ja_JP
```

## Using Mock Data in Test Cases

### Built-in variable functions

In YAML test cases, use built-in functions directly:

```yaml
variables:
  test_phone: "${random_phone()}"
  test_email: "${random_email()}"
  test_name: "${random_name()}"
  test_id: "${uuid()}"
  test_ts: "${timestamp()}"

steps:
  - name: "Register user"
    request:
      method: POST
      url: /api/register
      body:
        phone: "${test_phone}"
        email: "${test_email}"
        name: "${test_name}"
```

### Mock Server

For testing against a mock API:

```bash
# Start mock server with default configs
smartapi mock-server

# With custom config
smartapi mock-server --config mock/example_mock.yaml --port 8000
```

Mock config format (`mock/example_mock.yaml`):
```yaml
routes:
  - path: /api/login
    method: POST
    response:
      status: 200
      body:
        code: 0
        data:
          token: "mock-token-123"
          user_id: 1001

  - path: /api/users
    method: GET
    response:
      status: 200
      body:
        code: 0
        data:
          - id: 1
            name: "Test User"
```

Then run tests against the mock:

```bash
smartapi run testcases/ --base-url http://127.0.0.1:8000
```

## Encrypt Sensitive Test Data

```bash
# Encrypt a password
smartapi encrypt "my_secret_password"
# Output: ENC(gAAAAABf...)

# Use in YAML
# password: "ENC(gAAAAABf...)"

# Decrypt to verify
smartapi decrypt "ENC(gAAAAABf...)"
```

Set encryption key via environment variable:
```bash
export SMARTAPI_SECRET_KEY="your-master-key"
```
