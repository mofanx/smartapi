"""断言引擎单元测试"""

import pytest

from smartapi.core.assertion import AssertionEngine, AssertionError
from smartapi.core.models import (
    AssertConfig,
    AssertLevel,
    AssertOperator,
    AssertTarget,
)


class TestAssertionEngine:
    """断言引擎测试"""

    def _make_assert(self, **kwargs) -> AssertConfig:
        defaults = {
            "target": AssertTarget.BODY,
            "operator": AssertOperator.EQUALS,
            "expected": None,
            "level": AssertLevel.ERROR,
        }
        defaults.update(kwargs)
        return AssertConfig(**defaults)

    # --- 状态码断言 ---
    def test_status_code_eq(self):
        cfg = self._make_assert(target=AssertTarget.STATUS_CODE, expected=200)
        result = AssertionEngine.execute_assert(cfg, 200, {}, {}, 100)
        assert result.passed is True

    def test_status_code_ne(self):
        cfg = self._make_assert(target=AssertTarget.STATUS_CODE, expected=200)
        result = AssertionEngine.execute_assert(cfg, 404, {}, {}, 100)
        assert result.passed is False

    # --- 响应体 JSONPath 断言 ---
    def test_body_jsonpath_eq(self):
        cfg = self._make_assert(
            target=AssertTarget.BODY,
            expression="$.code",
            expected=0,
        )
        result = AssertionEngine.execute_assert(cfg, 200, {}, {"code": 0, "msg": "ok"}, 100)
        assert result.passed is True
        assert result.actual == 0

    def test_body_jsonpath_contains(self):
        cfg = self._make_assert(
            target=AssertTarget.BODY,
            expression="$.msg",
            operator=AssertOperator.CONTAINS,
            expected="success",
        )
        result = AssertionEngine.execute_assert(cfg, 200, {}, {"msg": "operation success"}, 100)
        assert result.passed is True

    def test_body_jsonpath_not_contains(self):
        cfg = self._make_assert(
            target=AssertTarget.BODY,
            expression="$.msg",
            operator=AssertOperator.NOT_CONTAINS,
            expected="error",
        )
        result = AssertionEngine.execute_assert(cfg, 200, {}, {"msg": "all good"}, 100)
        assert result.passed is True

    # --- 响应头断言 ---
    def test_header_eq(self):
        cfg = self._make_assert(
            target=AssertTarget.HEADER,
            expression="Content-Type",
            expected="application/json",
        )
        result = AssertionEngine.execute_assert(cfg, 200, {"Content-Type": "application/json"}, {}, 100)
        assert result.passed is True

    # --- 响应时间断言 ---
    def test_response_time_lt(self):
        cfg = self._make_assert(
            target=AssertTarget.RESPONSE_TIME,
            operator=AssertOperator.LESS_THAN,
            expected=500,
        )
        result = AssertionEngine.execute_assert(cfg, 200, {}, {}, 200)
        assert result.passed is True

    def test_response_time_gt_fail(self):
        cfg = self._make_assert(
            target=AssertTarget.RESPONSE_TIME,
            operator=AssertOperator.LESS_THAN,
            expected=100,
        )
        result = AssertionEngine.execute_assert(cfg, 200, {}, {}, 200)
        assert result.passed is False

    # --- 运算符测试 ---
    def test_operator_gt(self):
        cfg = self._make_assert(
            target=AssertTarget.BODY,
            expression="$.count",
            operator=AssertOperator.GREATER_THAN,
            expected=5,
        )
        result = AssertionEngine.execute_assert(cfg, 200, {}, {"count": 10}, 100)
        assert result.passed is True

    def test_operator_gte(self):
        cfg = self._make_assert(
            target=AssertTarget.BODY,
            expression="$.count",
            operator=AssertOperator.GREATER_EQUAL,
            expected=10,
        )
        result = AssertionEngine.execute_assert(cfg, 200, {}, {"count": 10}, 100)
        assert result.passed is True

    def test_operator_lte(self):
        cfg = self._make_assert(
            target=AssertTarget.BODY,
            expression="$.count",
            operator=AssertOperator.LESS_EQUAL,
            expected=10,
        )
        result = AssertionEngine.execute_assert(cfg, 200, {}, {"count": 10}, 100)
        assert result.passed is True

    def test_operator_regex(self):
        cfg = self._make_assert(
            target=AssertTarget.BODY,
            expression="$.email",
            operator=AssertOperator.REGEX_MATCH,
            expected=r"^\w+@\w+\.\w+$",
        )
        result = AssertionEngine.execute_assert(cfg, 200, {}, {"email": "test@example.com"}, 100)
        assert result.passed is True

    def test_operator_is_null(self):
        cfg = self._make_assert(
            target=AssertTarget.BODY,
            expression="$.missing",
            operator=AssertOperator.IS_NULL,
        )
        result = AssertionEngine.execute_assert(cfg, 200, {}, {"name": "test"}, 100)
        assert result.passed is True

    def test_operator_is_not_null(self):
        cfg = self._make_assert(
            target=AssertTarget.BODY,
            expression="$.name",
            operator=AssertOperator.IS_NOT_NULL,
        )
        result = AssertionEngine.execute_assert(cfg, 200, {}, {"name": "test"}, 100)
        assert result.passed is True

    def test_operator_length_eq(self):
        cfg = self._make_assert(
            target=AssertTarget.BODY,
            expression="$.items",
            operator=AssertOperator.LENGTH_EQUALS,
            expected=3,
        )
        result = AssertionEngine.execute_assert(cfg, 200, {}, {"items": [1, 2, 3]}, 100)
        assert result.passed is True

    def test_operator_type_is(self):
        cfg = self._make_assert(
            target=AssertTarget.BODY,
            expression="$.name",
            operator=AssertOperator.TYPE_IS,
            expected="str",
        )
        result = AssertionEngine.execute_assert(cfg, 200, {}, {"name": "test"}, 100)
        assert result.passed is True

    # --- 断言级别 ---
    def test_warning_level_does_not_fail(self):
        cfg = self._make_assert(
            target=AssertTarget.STATUS_CODE,
            expected=200,
            level=AssertLevel.WARNING,
        )
        all_passed, results = AssertionEngine.execute_asserts(
            [cfg], 404, {}, {}, 100
        )
        assert all_passed is True  # WARNING 不影响结果
        assert results[0].passed is False

    def test_fatal_level_raises(self):
        cfg = self._make_assert(
            target=AssertTarget.STATUS_CODE,
            expected=200,
            level=AssertLevel.FATAL,
        )
        with pytest.raises(AssertionError):
            AssertionEngine.execute_asserts([cfg], 500, {}, {}, 100)

    # --- 自定义脚本断言 ---
    def test_script_assert_pass(self):
        cfg = self._make_assert(
            target=AssertTarget.CUSTOM,
            script='result = status_code == 200 and "ok" in str(body)',
        )
        result = AssertionEngine.execute_assert(cfg, 200, {}, {"msg": "ok"}, 100)
        assert result.passed is True

    def test_script_assert_fail(self):
        cfg = self._make_assert(
            target=AssertTarget.CUSTOM,
            script='result = status_code == 200\nmessage = "状态码不是200"',
        )
        result = AssertionEngine.execute_assert(cfg, 500, {}, {}, 100)
        assert result.passed is False

    # --- 多断言 ---
    def test_multiple_asserts_all_pass(self):
        asserts = [
            self._make_assert(target=AssertTarget.STATUS_CODE, expected=200),
            self._make_assert(target=AssertTarget.BODY, expression="$.code", expected=0),
        ]
        all_passed, results = AssertionEngine.execute_asserts(
            asserts, 200, {}, {"code": 0}, 100
        )
        assert all_passed is True
        assert all(r.passed for r in results)

    def test_multiple_asserts_partial_fail(self):
        asserts = [
            self._make_assert(target=AssertTarget.STATUS_CODE, expected=200),
            self._make_assert(target=AssertTarget.BODY, expression="$.code", expected=0),
        ]
        all_passed, results = AssertionEngine.execute_asserts(
            asserts, 200, {}, {"code": 1}, 100
        )
        assert all_passed is False
        assert results[0].passed is True
        assert results[1].passed is False
