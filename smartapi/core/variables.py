"""变量管理系统 - 支持全局/环境/用例/步骤变量，动态变量生成"""

from __future__ import annotations

import hashlib
import os
import re
import time
import uuid
from typing import Any

from faker import Faker
from loguru import logger

fake = Faker("zh_CN")

# 内置动态变量生成函数
BUILTIN_FUNCTIONS: dict[str, callable] = {
    "timestamp": lambda: int(time.time()),
    "timestamp_ms": lambda: int(time.time() * 1000),
    "uuid": lambda: str(uuid.uuid4()),
    "uuid_hex": lambda: uuid.uuid4().hex,
    "random_int": lambda: fake.random_int(min=1, max=99999),
    "random_string": lambda: fake.pystr(min_chars=8, max_chars=16),
    "random_phone": lambda: fake.phone_number(),
    "random_email": lambda: fake.email(),
    "random_name": lambda: fake.name(),
    "random_id_card": lambda: fake.ssn(),
    "random_address": lambda: fake.address(),
    "random_company": lambda: fake.company(),
    "random_ip": lambda: fake.ipv4(),
    "random_url": lambda: fake.url(),
    "random_date": lambda: fake.date(),
    "random_datetime": lambda: fake.date_time().isoformat(),
    "md5": lambda val="": hashlib.md5(str(val).encode()).hexdigest(),
    "sha256": lambda val="": hashlib.sha256(str(val).encode()).hexdigest(),
    "now": lambda: time.strftime("%Y-%m-%d %H:%M:%S"),
    "today": lambda: time.strftime("%Y-%m-%d"),
}

# 变量引用模式: ${var_name} 或 ${func_name()} 或 ${func_name(arg)}
VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")
FUNC_PATTERN = re.compile(r"^(\w+)\((.*)\)$")


class VariableManager:
    """多层级变量管理器

    优先级（从高到低）：
    1. 步骤变量 (step)
    2. 用例变量 (case)
    3. 全局变量 (global)
    4. 环境变量 (env)
    5. 内置函数 (builtin)
    """

    def __init__(self):
        self._env_vars: dict[str, Any] = {}
        self._global_vars: dict[str, Any] = {}
        self._case_vars: dict[str, Any] = {}
        self._step_vars: dict[str, Any] = {}
        self._extract_vars: dict[str, Any] = {}  # 提取的变量
        self._custom_functions: dict[str, callable] = {}

    def set_env_vars(self, variables: dict[str, Any]) -> None:
        """设置环境变量"""
        self._env_vars.update(variables)

    def set_global_vars(self, variables: dict[str, Any]) -> None:
        """设置全局变量"""
        self._global_vars.update(variables)

    def set_case_vars(self, variables: dict[str, Any]) -> None:
        """设置用例变量"""
        self._case_vars.update(variables)

    def set_step_vars(self, variables: dict[str, Any]) -> None:
        """设置步骤变量"""
        self._step_vars.update(variables)

    def set_extract_var(self, name: str, value: Any) -> None:
        """设置提取变量"""
        self._extract_vars[name] = value
        logger.debug(f"提取变量: {name} = {value}")

    def clear_step_vars(self) -> None:
        """清除步骤变量"""
        self._step_vars.clear()

    def clear_case_vars(self) -> None:
        """清除用例变量和步骤变量"""
        self._case_vars.clear()
        self._step_vars.clear()
        self._extract_vars.clear()

    def register_function(self, name: str, func: callable) -> None:
        """注册自定义函数"""
        self._custom_functions[name] = func

    def get(self, name: str, default: Any = None) -> Any:
        """按优先级获取变量值"""
        # 步骤变量 > 提取变量 > 用例变量 > 全局变量 > 环境变量 > 系统环境变量
        for store in [
            self._step_vars,
            self._extract_vars,
            self._case_vars,
            self._global_vars,
            self._env_vars,
        ]:
            if name in store:
                return store[name]

        # 尝试从系统环境变量获取
        env_val = os.environ.get(name)
        if env_val is not None:
            return env_val

        return default

    def _resolve_function(self, func_str: str) -> Any:
        """解析函数调用，如 timestamp() 或 md5(hello)"""
        match = FUNC_PATTERN.match(func_str)
        if not match:
            return None

        func_name = match.group(1)
        func_args = match.group(2).strip()

        # 先查自定义函数，再查内置函数
        func = self._custom_functions.get(func_name) or BUILTIN_FUNCTIONS.get(func_name)
        if func is None:
            return None

        try:
            if func_args:
                # 替换参数中的变量
                resolved_args = self.resolve_string(func_args)
                return func(resolved_args)
            return func()
        except Exception as e:
            logger.warning(f"函数 {func_name} 执行失败: {e}")
            return None

    def resolve_string(self, text: str) -> str:
        """解析字符串中的变量引用 ${var} 和函数调用 ${func()}"""
        if not isinstance(text, str):
            return text

        def _replace(match: re.Match) -> str:
            expr = match.group(1).strip()

            # 尝试作为函数调用
            if "(" in expr:
                result = self._resolve_function(expr)
                if result is not None:
                    return str(result)

            # 作为变量查找
            value = self.get(expr)
            if value is not None:
                return str(value)

            logger.warning(f"未找到变量: {expr}")
            return match.group(0)  # 保持原样

        return VAR_PATTERN.sub(_replace, text)

    def resolve_value(self, value: Any) -> Any:
        """递归解析任意类型值中的变量引用"""
        if isinstance(value, str):
            resolved = self.resolve_string(value)
            # 如果整个字符串是一个变量引用，返回原始类型
            if VAR_PATTERN.fullmatch(value.strip()):
                expr = VAR_PATTERN.match(value.strip()).group(1).strip()
                if "(" in expr:
                    result = self._resolve_function(expr)
                    if result is not None:
                        return result
                raw = self.get(expr)
                if raw is not None:
                    return raw
            return resolved
        elif isinstance(value, dict):
            return {k: self.resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve_value(item) for item in value]
        return value

    def get_all(self) -> dict[str, Any]:
        """获取所有变量（合并后）"""
        merged = {}
        merged.update(self._env_vars)
        merged.update(self._global_vars)
        merged.update(self._case_vars)
        merged.update(self._extract_vars)
        merged.update(self._step_vars)
        return merged
