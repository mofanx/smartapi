"""HTTP 执行引擎 - 用例执行核心"""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx
from loguru import logger

from smartapi.core.assertion import AssertionEngine, AssertionError
from smartapi.core.extractor import DataExtractor
from smartapi.core.models import (
    AssertResult,
    ConditionOperator,
    Condition,
    LoopConfig,
    RequestConfig,
    StepConfig,
    StepResult,
    TestCaseConfig,
    TestCaseResult,
)
from smartapi.core.variables import VariableManager


class ExecutionError(Exception):
    """执行错误"""
    pass


class TestExecutor:
    """测试用例执行器"""

    def __init__(
        self,
        variable_manager: Optional[VariableManager] = None,
        base_url: str = "",
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ):
        self.variables = variable_manager or VariableManager()
        self.base_url = base_url
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._step_results: dict[str, StepResult] = {}  # step_id -> result
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=self.timeout,
                verify=self.verify_ssl,
                follow_redirects=True,
            )
        return self._client

    def close(self):
        if self._client and not self._client.is_closed:
            self._client.close()

    def _resolve_url(self, url: str) -> str:
        """解析 URL，拼接 base_url"""
        resolved = self.variables.resolve_string(url)
        if resolved.startswith(("http://", "https://")):
            return resolved
        return f"{self.base_url.rstrip('/')}/{resolved.lstrip('/')}"

    def _build_request(self, config: RequestConfig) -> dict[str, Any]:
        """构建 httpx 请求参数"""
        kwargs: dict[str, Any] = {
            "method": config.method.value,
            "url": self._resolve_url(config.url),
            "headers": self.variables.resolve_value(config.headers) if config.headers else {},
            "params": self.variables.resolve_value(config.params) if config.params else None,
            "cookies": self.variables.resolve_value(config.cookies) if config.cookies else None,
            "follow_redirects": config.allow_redirects,
        }

        # 请求体
        if config.body is not None:
            kwargs["json"] = self.variables.resolve_value(config.body)
        elif config.form_data is not None:
            kwargs["data"] = self.variables.resolve_value(config.form_data)

        # 文件上传
        if config.files:
            files = {}
            for field_name, file_path in config.files.items():
                resolved_path = self.variables.resolve_string(file_path)
                files[field_name] = open(resolved_path, "rb")
            kwargs["files"] = files

        # 超时
        if config.auth and config.auth.type.value != "none":
            self._apply_auth(kwargs, config)

        return kwargs

    def _apply_auth(self, kwargs: dict[str, Any], config: RequestConfig) -> None:
        """应用鉴权"""
        auth = config.auth
        if not auth:
            return

        from smartapi.core.models import AuthType

        if auth.type == AuthType.BASIC:
            kwargs["auth"] = (
                self.variables.resolve_string(auth.username or ""),
                self.variables.resolve_string(auth.password or ""),
            )
        elif auth.type in (AuthType.BEARER, AuthType.TOKEN):
            token = self.variables.resolve_string(auth.token or "")
            prefix = auth.token_prefix or "Bearer"
            kwargs["headers"]["Authorization"] = f"{prefix} {token}"
        elif auth.type == AuthType.API_KEY:
            key_name = self.variables.resolve_string(auth.api_key_name or "")
            key_value = self.variables.resolve_string(auth.api_key_value or "")
            if auth.api_key_in == "header":
                kwargs["headers"][key_name] = key_value
            else:
                if kwargs["params"] is None:
                    kwargs["params"] = {}
                kwargs["params"][key_name] = key_value

    def _check_condition(self, condition: Condition) -> bool:
        """检查条件"""
        var_value = self.variables.get(condition.variable)

        op = condition.operator
        val = condition.value

        if op == ConditionOperator.EXISTS:
            return var_value is not None
        elif op == ConditionOperator.NOT_EXISTS:
            return var_value is None
        elif op == ConditionOperator.EQUALS:
            return str(var_value) == str(val)
        elif op in (ConditionOperator.NOT_EQUALS, ConditionOperator.NOT_EQUALS_ALIAS):
            return str(var_value) != str(val)
        elif op == ConditionOperator.CONTAINS:
            return str(val) in str(var_value)
        elif op == ConditionOperator.GREATER_THAN:
            try:
                return float(var_value) > float(val)
            except (TypeError, ValueError):
                return False
        elif op == ConditionOperator.LESS_THAN:
            try:
                return float(var_value) < float(val)
            except (TypeError, ValueError):
                return False
        return False

    def _execute_step_once(self, step: StepConfig) -> StepResult:
        """执行单个步骤一次"""
        result = StepResult(
            step_name=step.name,
            step_id=step.id,
        )

        try:
            # 前置脚本
            if step.setup_script:
                exec(step.setup_script, {"variables": self.variables, "__builtins__": __builtins__})

            # 设置步骤变量
            if step.variables:
                resolved_vars = self.variables.resolve_value(step.variables)
                self.variables.set_step_vars(resolved_vars)

            # 构建并发送请求
            request_kwargs = self._build_request(step.request)
            result.request_url = request_kwargs["url"]
            result.request_method = request_kwargs["method"]
            result.request_headers = request_kwargs.get("headers", {})
            result.request_body = request_kwargs.get("json") or request_kwargs.get("data")

            start_time = time.time()
            response = self.client.request(**request_kwargs)
            elapsed = time.time() - start_time

            result.status_code = response.status_code
            result.response_time = round(elapsed * 1000, 2)  # ms
            result.response_headers = dict(response.headers)

            # 解析响应体
            try:
                result.response_body = response.json()
            except Exception:
                result.response_body = response.text

            # 数据提取
            for extract_config in step.extract:
                value = DataExtractor.extract(
                    extract_config,
                    result.response_body,
                    result.response_headers,
                    response.text,
                )
                if value is not None:
                    self.variables.set_extract_var(extract_config.name, value)
                    result.extracts[extract_config.name] = value

            # 执行断言（先解析断言中的变量引用）
            if step.asserts:
                resolved_asserts = []
                for ac in step.asserts:
                    resolved_ac = ac.model_copy(update={
                        "expected": self.variables.resolve_value(ac.expected) if ac.expected is not None else None,
                        "expression": self.variables.resolve_string(ac.expression) if ac.expression else ac.expression,
                        "message": self.variables.resolve_string(ac.message) if ac.message else ac.message,
                    })
                    resolved_asserts.append(resolved_ac)
                all_passed, assert_results = AssertionEngine.execute_asserts(
                    resolved_asserts,
                    result.status_code,
                    result.response_headers,
                    result.response_body,
                    result.response_time,
                )
                result.assert_results = assert_results
                result.success = all_passed
            else:
                result.success = True

            # 后置脚本
            if step.teardown_script:
                exec(step.teardown_script, {"variables": self.variables, "result": result, "__builtins__": __builtins__})

        except AssertionError:
            result.success = False
            raise
        except httpx.TimeoutException as e:
            result.success = False
            result.error = f"请求超时: {e}"
            logger.error(f"步骤 [{step.name}] 请求超时: {e}")
        except httpx.RequestError as e:
            result.success = False
            result.error = f"请求错误: {e}"
            logger.error(f"步骤 [{step.name}] 请求错误: {e}")
        except Exception as e:
            result.success = False
            result.error = f"执行错误: {e}"
            logger.error(f"步骤 [{step.name}] 执行错误: {e}")

        return result

    def execute_step(self, step: StepConfig) -> StepResult:
        """执行步骤（含重试、跳过、循环逻辑）"""
        # 检查依赖
        for dep_id in step.depends_on:
            dep_result = self._step_results.get(dep_id)
            if dep_result is None or not dep_result.success:
                result = StepResult(
                    step_name=step.name,
                    step_id=step.id,
                    skipped=True,
                    skip_reason=f"依赖步骤 [{dep_id}] 未通过",
                )
                logger.info(f"步骤 [{step.name}] 跳过: 依赖步骤 [{dep_id}] 未通过")
                return result

        # 检查跳过条件
        if step.skip_if and self._check_condition(step.skip_if):
            result = StepResult(
                step_name=step.name,
                step_id=step.id,
                skipped=True,
                skip_reason="满足跳过条件",
            )
            logger.info(f"步骤 [{step.name}] 跳过: 满足跳过条件")
            return result

        # 循环执行
        if step.loop:
            return self._execute_step_with_loop(step)

        # 重试执行
        return self._execute_step_with_retry(step)

    def _execute_step_with_retry(self, step: StepConfig) -> StepResult:
        """带重试的步骤执行"""
        last_result = None
        max_attempts = step.retry + 1

        for attempt in range(max_attempts):
            if attempt > 0:
                logger.info(f"步骤 [{step.name}] 第 {attempt + 1} 次重试...")
                time.sleep(step.retry_interval)

            last_result = self._execute_step_once(step)

            if last_result.success:
                break

        return last_result

    def _execute_step_with_loop(self, step: StepConfig) -> StepResult:
        """带循环的步骤执行"""
        loop = step.loop
        last_result = None

        if loop.times is not None:
            # 固定次数循环
            for i in range(loop.times):
                self.variables.set_step_vars({"loop_index": i})
                last_result = self._execute_step_with_retry(step)
                if loop.interval > 0:
                    time.sleep(loop.interval)
        elif loop.condition is not None:
            # 条件循环
            for i in range(loop.max_iterations):
                self.variables.set_step_vars({"loop_index": i})
                last_result = self._execute_step_with_retry(step)

                if self._check_condition(loop.condition):
                    break
                if loop.interval > 0:
                    time.sleep(loop.interval)

        return last_result or StepResult(step_name=step.name, step_id=step.id, success=False, error="循环未执行")

    def execute_test_case(self, test_case: TestCaseConfig) -> TestCaseResult:
        """执行完整测试用例"""
        logger.info(f"▶ 开始执行用例: {test_case.name}")
        case_result = TestCaseResult(
            case_name=test_case.name,
            case_id=test_case.id,
        )

        start_time = time.time()
        self._step_results.clear()
        self.variables.clear_case_vars()

        # 设置 base_url
        if test_case.base_url:
            self.base_url = test_case.base_url

        # 设置用例变量
        if test_case.variables:
            resolved = self.variables.resolve_value(test_case.variables)
            self.variables.set_case_vars(resolved)

        try:
            # 前置步骤
            if test_case.setup:
                for step in test_case.setup:
                    self._run_step_and_record(step, case_result, is_setup=True)

            # 主步骤
            for step in test_case.steps:
                self._run_step_and_record(step, case_result)

                # 处理分支
                if step.branch:
                    if self._check_condition(step.branch.condition):
                        branch_steps = step.branch.then_steps
                    else:
                        branch_steps = step.branch.else_steps

                    for branch_step_id in branch_steps:
                        branch_step = self._find_step_by_id(test_case.steps, branch_step_id)
                        if branch_step:
                            self._run_step_and_record(branch_step, case_result)

        except AssertionError as e:
            case_result.error = str(e)
        except Exception as e:
            case_result.error = f"用例执行异常: {e}"
            logger.error(f"用例 [{test_case.name}] 执行异常: {e}")
        finally:
            # 后置步骤
            if test_case.teardown:
                for step in test_case.teardown:
                    try:
                        self._run_step_and_record(step, case_result, is_teardown=True)
                    except Exception as e:
                        logger.warning(f"后置步骤 [{step.name}] 执行异常: {e}")

        elapsed = time.time() - start_time
        case_result.total_time = round(elapsed * 1000, 2)
        case_result.total_steps = len(case_result.step_results)
        case_result.passed_steps = sum(1 for r in case_result.step_results if r.success and not r.skipped)
        case_result.failed_steps = sum(1 for r in case_result.step_results if not r.success and not r.skipped)
        case_result.skipped_steps = sum(1 for r in case_result.step_results if r.skipped)
        case_result.success = case_result.failed_steps == 0 and case_result.error is None

        status = "✅ 通过" if case_result.success else "❌ 失败"
        logger.info(
            f"{status} 用例: {test_case.name} | "
            f"步骤: {case_result.passed_steps}/{case_result.total_steps} | "
            f"耗时: {case_result.total_time}ms"
        )

        return case_result

    def _run_step_and_record(
        self,
        step: StepConfig,
        case_result: TestCaseResult,
        is_setup: bool = False,
        is_teardown: bool = False,
    ):
        """执行步骤并记录结果"""
        step_result = self.execute_step(step)
        case_result.step_results.append(step_result)

        if step.id:
            self._step_results[step.id] = step_result

        if not step_result.success and not step_result.skipped:
            if not is_teardown:
                case_result.success = False

    @staticmethod
    def _find_step_by_id(steps: list[StepConfig], step_id: str) -> Optional[StepConfig]:
        """通过 ID 查找步骤"""
        for step in steps:
            if step.id == step_id:
                return step
        return None
