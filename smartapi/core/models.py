"""核心数据模型 - 声明式测试用例的 Pydantic 模型定义"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ExtractType(str, Enum):
    JSONPATH = "jsonpath"
    XPATH = "xpath"
    REGEX = "regex"
    HEADER = "header"


class AssertOperator(str, Enum):
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    NOT_EQUALS_ALIAS = "neq"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "gte"
    LESS_EQUAL = "lte"
    REGEX_MATCH = "regex"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    LENGTH_EQUALS = "length_eq"
    LENGTH_GREATER = "length_gt"
    LENGTH_LESS = "length_lt"
    TYPE_IS = "type_is"


class AssertLevel(str, Enum):
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class AssertTarget(str, Enum):
    STATUS_CODE = "status_code"
    HEADER = "header"
    BODY = "body"
    RESPONSE_TIME = "response_time"
    CUSTOM = "custom"


class ConditionOperator(str, Enum):
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    NOT_EQUALS_ALIAS = "neq"
    CONTAINS = "contains"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class AuthType(str, Enum):
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    TOKEN = "token"
    OAUTH2 = "oauth2"
    JWT = "jwt"
    API_KEY = "api_key"
    CUSTOM = "custom"


# --- 提取器 ---
class ExtractConfig(BaseModel):
    """从响应中提取数据的配置"""
    name: str = Field(..., description="提取后的变量名")
    type: ExtractType = Field(default=ExtractType.JSONPATH, description="提取类型")
    expression: str = Field(..., description="提取表达式")
    default: Any = Field(default=None, description="提取失败时的默认值")


# --- 断言 ---
class AssertConfig(BaseModel):
    """断言配置"""
    target: AssertTarget = Field(default=AssertTarget.BODY, description="断言目标")
    expression: Optional[str] = Field(default=None, description="目标表达式 (JSONPath/Header名)")
    operator: AssertOperator = Field(default=AssertOperator.EQUALS, description="比较运算符")
    expected: Any = Field(default=None, description="期望值")
    level: AssertLevel = Field(default=AssertLevel.ERROR, description="断言失败级别")
    message: Optional[str] = Field(default=None, description="自定义断言消息")
    script: Optional[str] = Field(default=None, description="自定义 Python 脚本断言")


# --- 条件 ---
class Condition(BaseModel):
    """条件判断配置"""
    variable: str = Field(..., description="变量名或表达式")
    operator: ConditionOperator = Field(default=ConditionOperator.EQUALS)
    value: Any = Field(default=None, description="比较值")


# --- 分支 ---
class BranchConfig(BaseModel):
    """分支配置"""
    condition: Condition
    then_steps: list[str] = Field(default_factory=list, description="条件为真时执行的步骤ID")
    else_steps: list[str] = Field(default_factory=list, description="条件为假时执行的步骤ID")


# --- 循环 ---
class LoopConfig(BaseModel):
    """循环配置"""
    times: Optional[int] = Field(default=None, description="循环次数")
    condition: Optional[Condition] = Field(default=None, description="条件循环")
    max_iterations: int = Field(default=100, description="最大循环次数")
    interval: float = Field(default=0, description="循环间隔(秒)")


# --- 鉴权 ---
class AuthConfig(BaseModel):
    """鉴权配置"""
    type: AuthType = Field(default=AuthType.NONE)
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    token_url: Optional[str] = None
    token_field: Optional[str] = Field(default="token", description="Token 字段名")
    token_prefix: str = Field(default="Bearer", description="Token 前缀")
    api_key_name: Optional[str] = None
    api_key_value: Optional[str] = None
    api_key_in: str = Field(default="header", description="API Key 位置: header/query")
    custom_script: Optional[str] = None
    refresh_url: Optional[str] = None
    expire_seconds: Optional[int] = None
    extra: dict[str, Any] = Field(default_factory=dict)


# --- 请求步骤 ---
class StepConfig(BaseModel):
    """单个测试步骤"""
    id: Optional[str] = Field(default=None, description="步骤ID")
    name: str = Field(..., description="步骤名称")
    request: RequestConfig = Field(..., description="请求配置")
    extract: list[ExtractConfig] = Field(default_factory=list, description="提取配置")
    asserts: list[AssertConfig] = Field(default_factory=list, description="断言配置")
    variables: dict[str, Any] = Field(default_factory=dict, description="步骤级变量")
    retry: int = Field(default=0, description="失败重试次数")
    retry_interval: float = Field(default=1.0, description="重试间隔(秒)")
    timeout: float = Field(default=30.0, description="超时时间(秒)")
    skip_if: Optional[Condition] = Field(default=None, description="跳过条件")
    depends_on: list[str] = Field(default_factory=list, description="依赖步骤ID列表")
    branch: Optional[BranchConfig] = Field(default=None, description="分支配置")
    loop: Optional[LoopConfig] = Field(default=None, description="循环配置")
    setup_script: Optional[str] = Field(default=None, description="前置脚本")
    teardown_script: Optional[str] = Field(default=None, description="后置脚本")

    @model_validator(mode="before")
    @classmethod
    def _normalize_retry(cls, data: Any) -> Any:
        """支持 retry 为 int 或 dict 格式"""
        if isinstance(data, dict) and isinstance(data.get("retry"), dict):
            retry_cfg = data.pop("retry")
            data["retry"] = retry_cfg.get("max_retries", 0)
            if "retry_interval" in retry_cfg:
                data["retry_interval"] = retry_cfg["retry_interval"]
        return data


class RequestConfig(BaseModel):
    """HTTP 请求配置"""
    method: HttpMethod = Field(default=HttpMethod.GET)
    url: str = Field(..., description="请求URL (支持变量替换)")
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict, description="查询参数")
    body: Optional[Any] = Field(default=None, description="请求体 (JSON)")
    form_data: Optional[dict[str, Any]] = Field(default=None, description="表单数据")
    files: Optional[dict[str, str]] = Field(default=None, description="上传文件路径")
    cookies: dict[str, str] = Field(default_factory=dict)
    auth: Optional[AuthConfig] = Field(default=None, description="步骤级鉴权")
    allow_redirects: bool = Field(default=True)
    verify_ssl: bool = Field(default=True)


# --- 测试用例 ---
class TestCaseConfig(BaseModel):
    """测试用例配置"""
    id: Optional[str] = Field(default=None, description="用例ID")
    name: str = Field(..., description="用例名称")
    description: Optional[str] = Field(default=None, description="用例描述")
    tags: list[str] = Field(default_factory=list, description="标签")
    priority: str = Field(default="medium", description="优先级: high/medium/low")
    base_url: Optional[str] = Field(default=None, description="基础URL")
    variables: dict[str, Any] = Field(default_factory=dict, description="用例级变量")
    auth: Optional[AuthConfig] = Field(default=None, description="用例级鉴权")
    setup: Optional[list[StepConfig]] = Field(default=None, description="前置步骤")
    steps: list[StepConfig] = Field(..., description="测试步骤")
    teardown: Optional[list[StepConfig]] = Field(default=None, description="后置步骤")


# --- 环境配置 ---
class EnvironmentConfig(BaseModel):
    """环境配置"""
    name: str = Field(..., description="环境名称")
    base_url: str = Field(..., description="基础URL")
    variables: dict[str, Any] = Field(default_factory=dict)
    auth: Optional[AuthConfig] = None
    headers: dict[str, str] = Field(default_factory=dict, description="全局请求头")


# --- 测试集 ---
class TestSuiteConfig(BaseModel):
    """测试集配置"""
    name: str = Field(..., description="测试集名称")
    description: Optional[str] = None
    environment: Optional[str] = Field(default=None, description="环境名称")
    variables: dict[str, Any] = Field(default_factory=dict, description="全局变量")
    auth: Optional[AuthConfig] = None
    tags: list[str] = Field(default_factory=list)
    test_cases: list[TestCaseConfig] = Field(default_factory=list)
    concurrency: int = Field(default=1, description="并发数")


# --- 执行结果模型 ---
class StepResult(BaseModel):
    """步骤执行结果"""
    step_name: str
    step_id: Optional[str] = None
    success: bool = True
    status_code: Optional[int] = None
    response_time: float = 0.0
    request_url: Optional[str] = None
    request_method: Optional[str] = None
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: Any = None
    response_headers: dict[str, str] = Field(default_factory=dict)
    response_body: Any = None
    extracts: dict[str, Any] = Field(default_factory=dict)
    assert_results: list[AssertResult] = Field(default_factory=list)
    error: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


class AssertResult(BaseModel):
    """断言结果"""
    target: str
    expression: Optional[str] = None
    operator: str
    expected: Any = None
    actual: Any = None
    passed: bool = True
    level: str = "error"
    message: Optional[str] = None


class TestCaseResult(BaseModel):
    """用例执行结果"""
    case_name: str
    case_id: Optional[str] = None
    success: bool = True
    total_steps: int = 0
    passed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    total_time: float = 0.0
    step_results: list[StepResult] = Field(default_factory=list)
    error: Optional[str] = None
