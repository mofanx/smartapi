"""用例解析器单元测试"""

import tempfile
from pathlib import Path

import pytest
import yaml

from smartapi.core.models import HttpMethod, AssertOperator, AssertTarget
from smartapi.core.parser import ParserError, TestCaseParser


class TestParser:
    """测试用例解析器测试"""

    def _write_yaml(self, data: dict, suffix: str = ".yaml") -> Path:
        """写入临时 YAML 文件"""
        f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8")
        yaml.dump(data, f, allow_unicode=True)
        f.close()
        return Path(f.name)

    def test_load_yaml_file(self):
        data = {"name": "test", "steps": [{"name": "s1", "request": {"url": "/api"}}]}
        path = self._write_yaml(data)
        result = TestCaseParser.load_file(path)
        assert result["name"] == "test"

    def test_load_nonexistent_file(self):
        with pytest.raises(ParserError, match="文件不存在"):
            TestCaseParser.load_file("/nonexistent/file.yaml")

    def test_load_empty_file(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        f.write("")
        f.close()
        with pytest.raises(ParserError, match="文件为空"):
            TestCaseParser.load_file(f.name)

    def test_load_unsupported_format(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        f.write("hello")
        f.close()
        with pytest.raises(ParserError, match="不支持的文件格式"):
            TestCaseParser.load_file(f.name)

    def test_parse_simple_test_case(self):
        data = {
            "name": "登录测试",
            "description": "测试用户登录",
            "tags": ["smoke"],
            "base_url": "http://localhost:8080",
            "steps": [
                {
                    "name": "登录请求",
                    "request": {
                        "method": "POST",
                        "url": "/api/login",
                        "body": {"username": "admin", "password": "123456"},
                    },
                    "asserts": [
                        {"target": "status_code", "operator": "eq", "expected": 200},
                    ],
                }
            ],
        }
        case = TestCaseParser.parse_test_case(data)
        assert case.name == "登录测试"
        assert len(case.steps) == 1
        assert case.steps[0].request.method == HttpMethod.POST
        assert case.steps[0].asserts[0].target == AssertTarget.STATUS_CODE
        assert case.steps[0].asserts[0].operator == AssertOperator.EQUALS

    def test_parse_multi_step_case(self):
        data = {
            "name": "多步骤测试",
            "steps": [
                {
                    "id": "step1",
                    "name": "获取Token",
                    "request": {"method": "POST", "url": "/auth/token"},
                    "extract": [
                        {"name": "token", "type": "jsonpath", "expression": "$.token"}
                    ],
                },
                {
                    "id": "step2",
                    "name": "查询用户",
                    "request": {"method": "GET", "url": "/api/user"},
                    "depends_on": ["step1"],
                },
            ],
        }
        case = TestCaseParser.parse_test_case(data)
        assert len(case.steps) == 2
        assert case.steps[0].extract[0].name == "token"
        assert case.steps[1].depends_on == ["step1"]

    def test_parse_test_suite(self):
        data = {
            "name": "测试集",
            "variables": {"base": "http://api.example.com"},
            "test_cases": [
                {
                    "name": "用例1",
                    "steps": [{"name": "步骤1", "request": {"url": "/api"}}],
                },
                {
                    "name": "用例2",
                    "steps": [{"name": "步骤1", "request": {"url": "/api2"}}],
                },
            ],
        }
        suite = TestCaseParser.parse_test_suite(data)
        assert suite.name == "测试集"
        assert len(suite.test_cases) == 2

    def test_validate_yaml_string_valid(self):
        yaml_str = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "/api"
"""
        is_valid, result = TestCaseParser.validate_yaml_string(yaml_str)
        assert is_valid is True

    def test_validate_yaml_string_invalid(self):
        yaml_str = """
description: "缺少 name 和 steps"
"""
        is_valid, result = TestCaseParser.validate_yaml_string(yaml_str)
        assert is_valid is False

    def test_parse_case_with_auth(self):
        data = {
            "name": "鉴权测试",
            "auth": {"type": "bearer", "token": "abc123"},
            "steps": [{"name": "步骤", "request": {"url": "/api"}}],
        }
        case = TestCaseParser.parse_test_case(data)
        assert case.auth.type.value == "bearer"
        assert case.auth.token == "abc123"

    def test_parse_case_with_loop(self):
        data = {
            "name": "循环测试",
            "steps": [
                {
                    "name": "循环步骤",
                    "request": {"url": "/api"},
                    "loop": {"times": 3},
                }
            ],
        }
        case = TestCaseParser.parse_test_case(data)
        assert case.steps[0].loop.times == 3

    def test_parse_case_with_branch(self):
        data = {
            "name": "分支测试",
            "steps": [
                {
                    "name": "分支步骤",
                    "request": {"url": "/api"},
                    "branch": {
                        "condition": {"variable": "status", "operator": "eq", "value": "success"},
                        "then_steps": ["step_a"],
                        "else_steps": ["step_b"],
                    },
                }
            ],
        }
        case = TestCaseParser.parse_test_case(data)
        assert case.steps[0].branch.then_steps == ["step_a"]
