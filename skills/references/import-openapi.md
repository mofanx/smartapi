# Import OpenAPI/Swagger Specifications

## Overview

SmartAPI-Test can import OpenAPI 3.x and Swagger 2.0 specifications to auto-generate test cases.

## Basic Usage

```bash
# From local JSON file
smartapi import-openapi swagger.json

# From local YAML file
smartapi import-openapi openapi.yaml

# From URL (auto-downloads)
smartapi import-openapi https://petstore.swagger.io/v2/swagger.json
smartapi import-openapi https://api.example.com/v3/api-docs
```

## Output Options

### Single test suite file (default)

```bash
smartapi import-openapi swagger.json
# Output: testcases/openapi_<api_title>.yaml (all endpoints in one file)
```

### Split into individual files

```bash
smartapi import-openapi swagger.json --output testcases/ --split
# Output: testcases/openapi_001_<endpoint>.yaml (one file per endpoint)
```

### Custom output path

```bash
smartapi import-openapi swagger.json --output testcases/my_api_tests.yaml
```

## Customization

### Override base URL

```bash
smartapi import-openapi swagger.json --base-url https://staging.example.com
```

### Custom tags

```bash
smartapi import-openapi swagger.json --tags regression,api,imported
```

## What Gets Generated

For each API endpoint, the import generates:

1. **Test case name** - From the endpoint's `summary` field
2. **HTTP method and URL** - From the path definition
3. **Query parameters** - From `parameters` with `in: query`
4. **Path parameters** - Converted to `${variable}` syntax
5. **Request body** - From `requestBody` schema (with example values)
6. **Status code assertion** - From the first 2xx response code
7. **Content-Type header** - `application/json` by default

## Post-Import Workflow

After importing, the generated tests are basic templates. Refine them:

```bash
# 1. Inspect quality
smartapi inspect testcases/

# 2. Common improvements needed:
#    - Add authentication headers
#    - Fill in realistic request body values
#    - Add response body assertions ($.data.field)
#    - Add data extraction for chained requests
#    - Add response time assertions
#    - Set up proper test data variables

# 3. Validate
smartapi validate testcases/

# 4. Run
smartapi run testcases/ --env environments/dev.yaml
```

## Example

Given this OpenAPI snippet:
```json
{
  "openapi": "3.0.0",
  "info": {"title": "Pet Store", "version": "1.0"},
  "servers": [{"url": "https://petstore.example.com"}],
  "paths": {
    "/pets": {
      "get": {
        "summary": "List all pets",
        "operationId": "listPets",
        "parameters": [
          {"name": "limit", "in": "query", "schema": {"type": "integer"}}
        ],
        "responses": {"200": {"description": "OK"}}
      },
      "post": {
        "summary": "Create a pet",
        "operationId": "createPet",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "name": {"type": "string"},
                  "tag": {"type": "string"}
                }
              }
            }
          }
        },
        "responses": {"201": {"description": "Created"}}
      }
    }
  }
}
```

Running `smartapi import-openapi petstore.json --split` generates two files:

**File 1: List all pets**
```yaml
name: List all pets
description: List all pets
tags: [imported, openapi, listPets]
base_url: https://petstore.example.com
steps:
  - name: List all pets
    request:
      method: GET
      url: /pets
      headers:
        Content-Type: application/json
      params:
        limit: <limit>
    asserts:
      - target: status_code
        operator: eq
        expected: 200
```

**File 2: Create a pet**
```yaml
name: Create a pet
description: Create a pet
tags: [imported, openapi, createPet]
base_url: https://petstore.example.com
steps:
  - name: Create a pet
    request:
      method: POST
      url: /pets
      headers:
        Content-Type: application/json
      body:
        name: string_value
        tag: string_value
    asserts:
      - target: status_code
        operator: eq
        expected: 201
```
