"""数据提取器单元测试"""

import pytest

from smartapi.core.extractor import DataExtractor, ExtractError
from smartapi.core.models import ExtractConfig, ExtractType


class TestDataExtractor:
    """数据提取器测试"""

    # --- JSONPath ---
    def test_jsonpath_simple(self):
        data = {"code": 0, "data": {"name": "test"}}
        result = DataExtractor.extract_jsonpath(data, "$.data.name")
        assert result == "test"

    def test_jsonpath_nested(self):
        data = {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}
        result = DataExtractor.extract_jsonpath(data, "$.users[0].name")
        assert result == "Alice"

    def test_jsonpath_array(self):
        data = {"items": [1, 2, 3]}
        result = DataExtractor.extract_jsonpath(data, "$.items[*]")
        assert result == [1, 2, 3]

    def test_jsonpath_no_match(self):
        data = {"name": "test"}
        result = DataExtractor.extract_jsonpath(data, "$.nonexistent")
        assert result is None

    # --- Regex ---
    def test_regex_single_match(self):
        text = 'token: "abc123def"'
        result = DataExtractor.extract_regex(text, r'"(\w+)"')
        assert result == "abc123def"

    def test_regex_multiple_matches(self):
        text = "id=1, id=2, id=3"
        result = DataExtractor.extract_regex(text, r"id=(\d+)")
        assert result == ["1", "2", "3"]

    def test_regex_no_match(self):
        text = "hello world"
        result = DataExtractor.extract_regex(text, r"\d+")
        assert result is None

    # --- Header ---
    def test_header_extract(self):
        headers = {"Content-Type": "application/json", "X-Request-Id": "abc123"}
        result = DataExtractor.extract_header(headers, "X-Request-Id")
        assert result == "abc123"

    def test_header_case_insensitive(self):
        headers = {"Content-Type": "application/json"}
        result = DataExtractor.extract_header(headers, "content-type")
        assert result == "application/json"

    def test_header_not_found(self):
        headers = {"Content-Type": "application/json"}
        result = DataExtractor.extract_header(headers, "X-Missing")
        assert result is None

    # --- Extract with config ---
    def test_extract_jsonpath_config(self):
        config = ExtractConfig(name="token", type=ExtractType.JSONPATH, expression="$.data.token")
        body = {"data": {"token": "abc"}}
        result = DataExtractor.extract(config, body, {}, "")
        assert result == "abc"

    def test_extract_regex_config(self):
        config = ExtractConfig(name="code", type=ExtractType.REGEX, expression=r"code=(\d+)")
        result = DataExtractor.extract(config, None, {}, "response code=200 ok")
        assert result == "200"

    def test_extract_header_config(self):
        config = ExtractConfig(name="req_id", type=ExtractType.HEADER, expression="X-Request-Id")
        result = DataExtractor.extract(config, None, {"X-Request-Id": "req-001"}, "")
        assert result == "req-001"

    def test_extract_default_value(self):
        config = ExtractConfig(
            name="missing", type=ExtractType.JSONPATH, expression="$.nonexistent", default="fallback"
        )
        result = DataExtractor.extract(config, {"key": "value"}, {}, "")
        assert result == "fallback"

    def test_extract_no_default(self):
        config = ExtractConfig(name="missing", type=ExtractType.JSONPATH, expression="$.nonexistent")
        result = DataExtractor.extract(config, {"key": "value"}, {}, "")
        assert result is None
