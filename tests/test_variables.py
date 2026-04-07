"""变量系统单元测试"""

import os
import pytest
from smartapi.core.variables import VariableManager


class TestVariableManager:
    """测试变量管理器"""

    def setup_method(self):
        self.vm = VariableManager()

    def test_set_and_get_global_vars(self):
        self.vm.set_global_vars({"host": "localhost", "port": 8080})
        assert self.vm.get("host") == "localhost"
        assert self.vm.get("port") == 8080

    def test_set_and_get_env_vars(self):
        self.vm.set_env_vars({"env_name": "dev"})
        assert self.vm.get("env_name") == "dev"

    def test_variable_priority(self):
        """步骤变量 > 提取变量 > 用例变量 > 全局变量 > 环境变量"""
        self.vm.set_env_vars({"key": "env"})
        assert self.vm.get("key") == "env"

        self.vm.set_global_vars({"key": "global"})
        assert self.vm.get("key") == "global"

        self.vm.set_case_vars({"key": "case"})
        assert self.vm.get("key") == "case"

        self.vm.set_extract_var("key", "extract")
        assert self.vm.get("key") == "extract"

        self.vm.set_step_vars({"key": "step"})
        assert self.vm.get("key") == "step"

    def test_get_default(self):
        assert self.vm.get("nonexistent") is None
        assert self.vm.get("nonexistent", "default") == "default"

    def test_resolve_string(self):
        self.vm.set_global_vars({"name": "SmartAPI", "version": "1.0"})
        result = self.vm.resolve_string("Hello ${name} v${version}")
        assert result == "Hello SmartAPI v1.0"

    def test_resolve_string_no_vars(self):
        result = self.vm.resolve_string("no variables here")
        assert result == "no variables here"

    def test_resolve_function_timestamp(self):
        result = self.vm.resolve_string("ts=${timestamp()}")
        assert result.startswith("ts=")
        assert result[3:].isdigit()

    def test_resolve_function_uuid(self):
        result = self.vm.resolve_string("id=${uuid()}")
        assert result.startswith("id=")
        assert len(result) > 10

    def test_resolve_value_dict(self):
        self.vm.set_global_vars({"user": "test", "token": "abc123"})
        data = {
            "name": "${user}",
            "auth": "Bearer ${token}",
            "nested": {"key": "${user}"},
        }
        result = self.vm.resolve_value(data)
        assert result["name"] == "test"
        assert result["auth"] == "Bearer abc123"
        assert result["nested"]["key"] == "test"

    def test_resolve_value_list(self):
        self.vm.set_global_vars({"item1": "a", "item2": "b"})
        data = ["${item1}", "${item2}", "fixed"]
        result = self.vm.resolve_value(data)
        assert result == ["a", "b", "fixed"]

    def test_resolve_value_preserves_type(self):
        """整个字符串是变量引用时，保持原始类型"""
        self.vm.set_global_vars({"count": 42, "flag": True})
        assert self.vm.resolve_value("${count}") == 42
        assert self.vm.resolve_value("${flag}") is True

    def test_clear_step_vars(self):
        self.vm.set_step_vars({"temp": "value"})
        assert self.vm.get("temp") == "value"
        self.vm.clear_step_vars()
        assert self.vm.get("temp") is None

    def test_clear_case_vars(self):
        self.vm.set_case_vars({"case_var": "a"})
        self.vm.set_extract_var("ext_var", "b")
        self.vm.clear_case_vars()
        assert self.vm.get("case_var") is None
        assert self.vm.get("ext_var") is None

    def test_system_env_var(self):
        os.environ["SMARTAPI_TEST_VAR"] = "from_env"
        try:
            assert self.vm.get("SMARTAPI_TEST_VAR") == "from_env"
        finally:
            del os.environ["SMARTAPI_TEST_VAR"]

    def test_get_all(self):
        self.vm.set_env_vars({"a": 1})
        self.vm.set_global_vars({"b": 2})
        self.vm.set_case_vars({"c": 3})
        all_vars = self.vm.get_all()
        assert all_vars == {"a": 1, "b": 2, "c": 3}

    def test_register_custom_function(self):
        self.vm.register_function("double", lambda x: str(int(x) * 2))
        result = self.vm.resolve_string("${double(5)}")
        assert result == "10"

    def test_unresolved_var_preserved(self):
        result = self.vm.resolve_string("${undefined_var}")
        assert result == "${undefined_var}"
