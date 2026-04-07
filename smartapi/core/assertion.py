"""断言引擎 - 多维度断言支持"""

from __future__ import annotations

import re
from typing import Any

from jsonpath_ng.ext import parse as jsonpath_parse
from loguru import logger

from smartapi.core.models import (
    AssertConfig,
    AssertLevel,
    AssertOperator,
    AssertResult,
    AssertTarget,
)


class AssertionError(Exception):
    """断言致命错误（中断测试集）"""
    pass


class AssertionWarning(Exception):
    """断言警告"""
    pass


class AssertionEngine:
    """断言引擎"""

    OPERATOR_MAP = {
        AssertOperator.EQUALS: lambda a, e: a == e,
        AssertOperator.NOT_EQUALS: lambda a, e: a != e,
        AssertOperator.NOT_EQUALS_ALIAS: lambda a, e: a != e,
        AssertOperator.CONTAINS: lambda a, e: e in a if isinstance(a, (str, list, dict)) else False,
        AssertOperator.NOT_CONTAINS: lambda a, e: e not in a if isinstance(a, (str, list, dict)) else True,
        AssertOperator.STARTS_WITH: lambda a, e: str(a).startswith(str(e)),
        AssertOperator.ENDS_WITH: lambda a, e: str(a).endswith(str(e)),
        AssertOperator.GREATER_THAN: lambda a, e: float(a) > float(e),
        AssertOperator.LESS_THAN: lambda a, e: float(a) < float(e),
        AssertOperator.GREATER_EQUAL: lambda a, e: float(a) >= float(e),
        AssertOperator.LESS_EQUAL: lambda a, e: float(a) <= float(e),
        AssertOperator.REGEX_MATCH: lambda a, e: bool(re.search(e, str(a))),
        AssertOperator.IN: lambda a, e: a in e if isinstance(e, list) else False,
        AssertOperator.NOT_IN: lambda a, e: a not in e if isinstance(e, list) else True,
        AssertOperator.IS_NULL: lambda a, e: a is None,
        AssertOperator.IS_NOT_NULL: lambda a, e: a is not None,
        AssertOperator.LENGTH_EQUALS: lambda a, e: len(a) == int(e),
        AssertOperator.LENGTH_GREATER: lambda a, e: len(a) > int(e),
        AssertOperator.LENGTH_LESS: lambda a, e: len(a) < int(e),
        AssertOperator.TYPE_IS: lambda a, e: type(a).__name__ == e,
    }

    @classmethod
    def _get_actual_value(
        cls,
        assert_config: AssertConfig,
        status_code: int,
        headers: dict[str, str],
        body: Any,
        response_time: float,
    ) -> Any:
        """根据断言目标获取实际值"""
        if assert_config.target == AssertTarget.STATUS_CODE:
            return status_code

        elif assert_config.target == AssertTarget.RESPONSE_TIME:
            return response_time

        elif assert_config.target == AssertTarget.HEADER:
            if assert_config.expression:
                for k, v in headers.items():
                    if k.lower() == assert_config.expression.lower():
                        return v
                return None
            return headers

        elif assert_config.target == AssertTarget.BODY:
            if assert_config.expression:
                try:
                    matches = jsonpath_parse(assert_config.expression).find(body)
                    if matches:
                        return matches[0].value if len(matches) == 1 else [m.value for m in matches]
                    return None
                except Exception as e:
                    logger.warning(f"JSONPath 解析失败 [{assert_config.expression}]: {e}")
                    return None
            return body

        elif assert_config.target == AssertTarget.CUSTOM:
            return None  # 自定义脚本断言

        return None

    @classmethod
    def _run_script_assert(
        cls,
        script: str,
        status_code: int,
        headers: dict[str, str],
        body: Any,
        response_time: float,
    ) -> tuple[bool, str]:
        """执行自定义 Python 脚本断言"""
        local_vars = {
            "status_code": status_code,
            "headers": headers,
            "body": body,
            "response_time": response_time,
            "result": True,
            "message": "",
        }
        try:
            exec(script, {"__builtins__": __builtins__}, local_vars)
            return local_vars.get("result", True), local_vars.get("message", "")
        except Exception as e:
            return False, f"脚本执行错误: {e}"

    @classmethod
    def execute_assert(
        cls,
        assert_config: AssertConfig,
        status_code: int,
        headers: dict[str, str],
        body: Any,
        response_time: float,
    ) -> AssertResult:
        """执行单个断言"""
        result = AssertResult(
            target=assert_config.target.value,
            expression=assert_config.expression,
            operator=assert_config.operator.value,
            expected=assert_config.expected,
            level=assert_config.level.value,
        )

        try:
            # 自定义脚本断言
            if assert_config.script:
                passed, msg = cls._run_script_assert(
                    assert_config.script, status_code, headers, body, response_time
                )
                result.passed = passed
                result.message = msg or assert_config.message
                return result

            # 获取实际值
            actual = cls._get_actual_value(assert_config, status_code, headers, body, response_time)
            result.actual = actual

            # 执行比较
            operator_func = cls.OPERATOR_MAP.get(assert_config.operator)
            if operator_func is None:
                result.passed = False
                result.message = f"不支持的运算符: {assert_config.operator}"
                return result

            result.passed = operator_func(actual, assert_config.expected)

            if not result.passed:
                result.message = assert_config.message or (
                    f"断言失败: {assert_config.target.value}"
                    f"{'[' + assert_config.expression + ']' if assert_config.expression else ''} "
                    f"{assert_config.operator.value} {assert_config.expected}，"
                    f"实际值: {actual}"
                )

        except Exception as e:
            result.passed = False
            result.message = f"断言执行异常: {e}"

        return result

    @classmethod
    def execute_asserts(
        cls,
        asserts: list[AssertConfig],
        status_code: int,
        headers: dict[str, str],
        body: Any,
        response_time: float,
    ) -> tuple[bool, list[AssertResult]]:
        """执行所有断言，返回 (是否全部通过, 断言结果列表)

        根据断言级别处理：
        - WARNING: 记录但不影响结果
        - ERROR: 标记用例失败
        - FATAL: 中断整个测试集
        """
        results = []
        all_passed = True
        has_fatal = False

        for assert_config in asserts:
            result = cls.execute_assert(assert_config, status_code, headers, body, response_time)
            results.append(result)

            if not result.passed:
                level = assert_config.level
                if level == AssertLevel.WARNING:
                    logger.warning(f"[断言警告] {result.message}")
                elif level == AssertLevel.ERROR:
                    logger.error(f"[断言失败] {result.message}")
                    all_passed = False
                elif level == AssertLevel.FATAL:
                    logger.critical(f"[致命断言失败] {result.message}")
                    all_passed = False
                    has_fatal = True
            else:
                logger.debug(f"[断言通过] {assert_config.target.value} {assert_config.operator.value}")

        if has_fatal:
            raise AssertionError("存在致命断言失败，中断测试集")

        return all_passed, results
