"""执行引擎集成测试 - 测试多步骤编排、数据提取、分支/循环/跳过/依赖"""

import pytest

from smartapi.core.executor import TestExecutor
from smartapi.core.models import (
    AssertConfig,
    AssertTarget,
    AssertOperator,
    BranchConfig,
    Condition,
    ConditionOperator,
    ExtractConfig,
    ExtractType,
    HttpMethod,
    LoopConfig,
    RequestConfig,
    StepConfig,
    TestCaseConfig,
)
from smartapi.core.variables import VariableManager


# 使用 httpbin.org 作为真实测试目标
BASE_URL = "https://httpbin.org"


@pytest.fixture
def executor():
    vm = VariableManager()
    ex = TestExecutor(variable_manager=vm, base_url=BASE_URL, timeout=15)
    yield ex
    ex.close()


@pytest.fixture
def var_manager():
    return VariableManager()


class TestExecutorBasic:
    """基础执行测试"""

    def test_simple_get(self, executor):
        case = TestCaseConfig(
            name="简单GET测试",
            steps=[
                StepConfig(
                    name="GET /get",
                    request=RequestConfig(method=HttpMethod.GET, url="/get", params={"foo": "bar"}),
                    asserts=[
                        AssertConfig(target=AssertTarget.STATUS_CODE, operator=AssertOperator.EQUALS, expected=200),
                        AssertConfig(
                            target=AssertTarget.BODY,
                            expression="$.args.foo",
                            operator=AssertOperator.EQUALS,
                            expected="bar",
                        ),
                    ],
                )
            ],
        )
        result = executor.execute_test_case(case)
        assert result.success is True
        assert result.passed_steps == 1

    def test_simple_post(self, executor):
        case = TestCaseConfig(
            name="简单POST测试",
            steps=[
                StepConfig(
                    name="POST /post",
                    request=RequestConfig(
                        method=HttpMethod.POST,
                        url="/post",
                        body={"name": "test", "age": 25},
                    ),
                    asserts=[
                        AssertConfig(target=AssertTarget.STATUS_CODE, operator=AssertOperator.EQUALS, expected=200),
                        AssertConfig(
                            target=AssertTarget.BODY,
                            expression="$.json.name",
                            operator=AssertOperator.EQUALS,
                            expected="test",
                        ),
                    ],
                )
            ],
        )
        result = executor.execute_test_case(case)
        assert result.success is True


class TestMultiStep:
    """多步骤编排测试"""

    def test_data_extraction_and_chaining(self, executor):
        """测试数据提取与步骤间传递"""
        case = TestCaseConfig(
            name="数据提取串联",
            steps=[
                StepConfig(
                    id="step1",
                    name="POST 提交数据",
                    request=RequestConfig(
                        method=HttpMethod.POST,
                        url="/post",
                        body={"username": "alice"},
                    ),
                    extract=[
                        ExtractConfig(name="posted_user", type=ExtractType.JSONPATH, expression="$.json.username"),
                    ],
                    asserts=[
                        AssertConfig(target=AssertTarget.STATUS_CODE, operator=AssertOperator.EQUALS, expected=200),
                    ],
                ),
                StepConfig(
                    id="step2",
                    name="GET 验证提取的数据",
                    request=RequestConfig(
                        method=HttpMethod.GET,
                        url="/get",
                        params={"user": "${posted_user}"},
                    ),
                    asserts=[
                        AssertConfig(target=AssertTarget.STATUS_CODE, operator=AssertOperator.EQUALS, expected=200),
                        AssertConfig(
                            target=AssertTarget.BODY,
                            expression="$.args.user",
                            operator=AssertOperator.EQUALS,
                            expected="alice",
                        ),
                    ],
                ),
            ],
        )
        result = executor.execute_test_case(case)
        assert result.success is True
        assert result.passed_steps == 2
        assert result.step_results[0].extracts["posted_user"] == "alice"

    def test_header_extraction(self, executor):
        """测试 Header 提取"""
        case = TestCaseConfig(
            name="Header提取",
            steps=[
                StepConfig(
                    name="提取响应头",
                    request=RequestConfig(method=HttpMethod.GET, url="/get"),
                    extract=[
                        ExtractConfig(name="content_type", type=ExtractType.HEADER, expression="Content-Type"),
                    ],
                    asserts=[
                        AssertConfig(target=AssertTarget.STATUS_CODE, operator=AssertOperator.EQUALS, expected=200),
                    ],
                ),
            ],
        )
        result = executor.execute_test_case(case)
        assert result.success is True
        assert "json" in result.step_results[0].extracts.get("content_type", "").lower()


class TestVariableSubstitution:
    """变量替换测试"""

    def test_case_variables(self, executor):
        """测试用例级变量替换"""
        case = TestCaseConfig(
            name="变量替换测试",
            variables={"my_param": "hello_world"},
            steps=[
                StepConfig(
                    name="使用变量",
                    request=RequestConfig(
                        method=HttpMethod.GET,
                        url="/get",
                        params={"msg": "${my_param}"},
                    ),
                    asserts=[
                        AssertConfig(target=AssertTarget.STATUS_CODE, operator=AssertOperator.EQUALS, expected=200),
                        AssertConfig(
                            target=AssertTarget.BODY,
                            expression="$.args.msg",
                            operator=AssertOperator.EQUALS,
                            expected="hello_world",
                        ),
                    ],
                ),
            ],
        )
        result = executor.execute_test_case(case)
        assert result.success is True

    def test_dynamic_variable_functions(self, executor):
        """测试动态变量函数"""
        case = TestCaseConfig(
            name="动态变量测试",
            steps=[
                StepConfig(
                    name="使用动态变量",
                    request=RequestConfig(
                        method=HttpMethod.POST,
                        url="/post",
                        body={
                            "ts": "${timestamp()}",
                            "id": "${uuid()}",
                        },
                    ),
                    asserts=[
                        AssertConfig(target=AssertTarget.STATUS_CODE, operator=AssertOperator.EQUALS, expected=200),
                        AssertConfig(
                            target=AssertTarget.BODY,
                            expression="$.json.ts",
                            operator=AssertOperator.IS_NOT_NULL,
                        ),
                        AssertConfig(
                            target=AssertTarget.BODY,
                            expression="$.json.id",
                            operator=AssertOperator.IS_NOT_NULL,
                        ),
                    ],
                ),
            ],
        )
        result = executor.execute_test_case(case)
        assert result.success is True


class TestStepDependency:
    """步骤依赖测试"""

    def test_skip_on_dependency_failure(self, executor):
        """依赖步骤失败时跳过"""
        case = TestCaseConfig(
            name="依赖跳过测试",
            steps=[
                StepConfig(
                    id="failing_step",
                    name="故意失败的步骤",
                    request=RequestConfig(method=HttpMethod.GET, url="/status/500"),
                    asserts=[
                        AssertConfig(target=AssertTarget.STATUS_CODE, operator=AssertOperator.EQUALS, expected=200),
                    ],
                ),
                StepConfig(
                    id="dependent_step",
                    name="依赖步骤",
                    depends_on=["failing_step"],
                    request=RequestConfig(method=HttpMethod.GET, url="/get"),
                ),
            ],
        )
        result = executor.execute_test_case(case)
        assert result.step_results[0].success is False
        assert result.step_results[1].skipped is True

    def test_skip_if_condition(self, executor):
        """条件跳过测试"""
        executor.variables.set_global_vars({"skip_flag": "true"})
        case = TestCaseConfig(
            name="条件跳过测试",
            steps=[
                StepConfig(
                    name="条件跳过的步骤",
                    request=RequestConfig(method=HttpMethod.GET, url="/get"),
                    skip_if=Condition(variable="skip_flag", operator=ConditionOperator.EQUALS, value="true"),
                ),
            ],
        )
        result = executor.execute_test_case(case)
        assert result.step_results[0].skipped is True


class TestRetryAndLoop:
    """重试与循环测试"""

    def test_retry_on_failure(self, executor):
        """失败重试（使用一个会成功的请求模拟）"""
        case = TestCaseConfig(
            name="重试测试",
            steps=[
                StepConfig(
                    name="带重试的步骤",
                    request=RequestConfig(method=HttpMethod.GET, url="/get"),
                    retry=2,
                    retry_interval=0.1,
                    asserts=[
                        AssertConfig(target=AssertTarget.STATUS_CODE, operator=AssertOperator.EQUALS, expected=200),
                    ],
                ),
            ],
        )
        result = executor.execute_test_case(case)
        assert result.success is True

    def test_loop_fixed_times(self, executor):
        """固定次数循环"""
        case = TestCaseConfig(
            name="固定次数循环",
            steps=[
                StepConfig(
                    name="循环3次",
                    request=RequestConfig(method=HttpMethod.GET, url="/get"),
                    loop=LoopConfig(times=3),
                    asserts=[
                        AssertConfig(target=AssertTarget.STATUS_CODE, operator=AssertOperator.EQUALS, expected=200),
                    ],
                ),
            ],
        )
        result = executor.execute_test_case(case)
        assert result.success is True


class TestSetupTeardown:
    """前置/后置步骤测试"""

    def test_setup_and_teardown(self, executor):
        """测试 setup 和 teardown"""
        case = TestCaseConfig(
            name="前置后置测试",
            setup=[
                StepConfig(
                    name="前置: 获取数据",
                    request=RequestConfig(method=HttpMethod.GET, url="/get", params={"setup": "true"}),
                    asserts=[
                        AssertConfig(target=AssertTarget.STATUS_CODE, operator=AssertOperator.EQUALS, expected=200),
                    ],
                ),
            ],
            steps=[
                StepConfig(
                    name="主步骤",
                    request=RequestConfig(method=HttpMethod.GET, url="/get"),
                    asserts=[
                        AssertConfig(target=AssertTarget.STATUS_CODE, operator=AssertOperator.EQUALS, expected=200),
                    ],
                ),
            ],
            teardown=[
                StepConfig(
                    name="后置: 清理数据",
                    request=RequestConfig(method=HttpMethod.GET, url="/get", params={"teardown": "true"}),
                ),
            ],
        )
        result = executor.execute_test_case(case)
        assert result.success is True
        # setup(1) + main(1) + teardown(1) = 3 steps
        assert result.total_steps == 3
