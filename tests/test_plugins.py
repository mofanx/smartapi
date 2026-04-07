"""插件系统单元测试"""

from typing import Any

import pytest

from smartapi.plugins.base import (
    AssertPlugin,
    BasePlugin,
    DataGeneratorPlugin,
    HookPlugin,
    PluginManager,
    PluginMeta,
    PluginType,
)


# --- 测试插件实现 ---

class SampleHookPlugin(HookPlugin):
    meta = PluginMeta(name="sample_hook", version="1.0.0", plugin_type=PluginType.HOOK, description="测试钩子")

    def __init__(self):
        self.events = []

    def activate(self, context):
        self.events.append("activated")

    def deactivate(self):
        self.events.append("deactivated")

    def on_test_start(self, test_case):
        self.events.append(f"test_start:{test_case}")

    def on_test_end(self, test_case, result):
        self.events.append(f"test_end:{test_case}")

    def on_request(self, request_kwargs):
        request_kwargs["headers"] = request_kwargs.get("headers", {})
        request_kwargs["headers"]["X-Plugin"] = "sample"
        return request_kwargs


class SampleAssertPlugin(AssertPlugin):
    meta = PluginMeta(name="json_schema_assert", version="1.0.0", plugin_type=PluginType.ASSERTION)

    def activate(self, context):
        pass

    def assert_func(self, actual, expected, **kwargs):
        """简单的类型检查断言"""
        if isinstance(actual, type(expected)):
            return True, "类型匹配"
        return False, f"类型不匹配: 期望 {type(expected).__name__}, 实际 {type(actual).__name__}"


class SampleDataPlugin(DataGeneratorPlugin):
    meta = PluginMeta(name="test_data_gen", version="1.0.0", plugin_type=PluginType.DATA_GENERATOR)

    def activate(self, context):
        pass

    def generate(self, **kwargs):
        prefix = kwargs.get("prefix", "TEST")
        return f"{prefix}-{__import__('random').randint(1000, 9999)}"


# --- 测试 ---

class TestPluginManager:
    def setup_method(self):
        self.pm = PluginManager()

    def test_register_plugin(self):
        plugin = SampleHookPlugin()
        self.pm.register(plugin)
        assert "activated" in plugin.events
        assert len(self.pm.list_plugins()) == 1

    def test_unregister_plugin(self):
        plugin = SampleHookPlugin()
        self.pm.register(plugin)
        self.pm.unregister("sample_hook")
        assert "deactivated" in plugin.events
        assert len(self.pm.list_plugins()) == 0

    def test_get_plugin(self):
        plugin = SampleHookPlugin()
        self.pm.register(plugin)
        got = self.pm.get_plugin("sample_hook")
        assert got is plugin

    def test_get_nonexistent_plugin(self):
        assert self.pm.get_plugin("nonexistent") is None

    def test_list_plugins(self):
        self.pm.register(SampleHookPlugin())
        self.pm.register(SampleAssertPlugin())
        plugins = self.pm.list_plugins()
        assert len(plugins) == 2
        names = {p["name"] for p in plugins}
        assert "sample_hook" in names
        assert "json_schema_assert" in names

    def test_fire_hooks(self):
        plugin = SampleHookPlugin()
        self.pm.register(plugin)

        self.pm.fire_test_start("case1")
        assert "test_start:case1" in plugin.events

        self.pm.fire_test_end("case1", {"success": True})
        assert "test_end:case1" in plugin.events

    def test_fire_on_request(self):
        plugin = SampleHookPlugin()
        self.pm.register(plugin)

        kwargs = {"url": "http://test.com", "headers": {}}
        result = self.pm.fire_on_request(kwargs)
        assert result["headers"]["X-Plugin"] == "sample"

    def test_assert_plugin(self):
        self.pm.register(SampleAssertPlugin())

        passed, msg = self.pm.run_assert("json_schema_assert", "hello", "world")
        assert passed is True

        passed, msg = self.pm.run_assert("json_schema_assert", 123, "world")
        assert passed is False

    def test_assert_plugin_not_found(self):
        passed, msg = self.pm.run_assert("nonexistent", None, None)
        assert passed is False
        assert "不存在" in msg

    def test_data_generator_plugin(self):
        self.pm.register(SampleDataPlugin())
        result = self.pm.generate_data("test_data_gen", prefix="ORD")
        assert result.startswith("ORD-")

    def test_data_generator_not_found(self):
        with pytest.raises(ValueError, match="不存在"):
            self.pm.generate_data("nonexistent")

    def test_duplicate_plugin_overwrite(self):
        p1 = SampleHookPlugin()
        p2 = SampleHookPlugin()
        self.pm.register(p1)
        self.pm.register(p2)
        # 应该有两个 hook（因为名称相同会覆盖 _plugins 但 hooks 列表会追加）
        assert self.pm.get_plugin("sample_hook") is p2
