"""插件系统 - 支持自定义扩展"""

from __future__ import annotations

import importlib
import inspect
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from loguru import logger


class PluginType:
    """插件类型常量"""
    ASSERTION = "assertion"
    DATA_GENERATOR = "data_generator"
    NOTIFIER = "notifier"
    REPORT = "report"
    PROTOCOL = "protocol"
    AUTH = "auth"
    HOOK = "hook"


class PluginMeta:
    """插件元数据"""

    def __init__(
        self,
        name: str,
        version: str = "0.1.0",
        plugin_type: str = PluginType.HOOK,
        description: str = "",
        author: str = "",
    ):
        self.name = name
        self.version = version
        self.plugin_type = plugin_type
        self.description = description
        self.author = author


class BasePlugin(ABC):
    """插件基类"""

    meta: PluginMeta = PluginMeta(name="base_plugin")

    @abstractmethod
    def activate(self, context: dict[str, Any]) -> None:
        """激活插件"""
        pass

    def deactivate(self) -> None:
        """停用插件"""
        pass


class HookPlugin(BasePlugin):
    """钩子插件 - 在测试生命周期中插入自定义逻辑"""

    meta = PluginMeta(name="hook_plugin", plugin_type=PluginType.HOOK)

    def on_test_start(self, test_case: Any) -> None:
        """测试开始前"""
        pass

    def on_test_end(self, test_case: Any, result: Any) -> None:
        """测试结束后"""
        pass

    def on_step_start(self, step: Any) -> None:
        """步骤开始前"""
        pass

    def on_step_end(self, step: Any, result: Any) -> None:
        """步骤结束后"""
        pass

    def on_request(self, request_kwargs: dict[str, Any]) -> dict[str, Any]:
        """请求发送前（可修改请求参数）"""
        return request_kwargs

    def on_response(self, response: Any) -> Any:
        """响应接收后"""
        return response

    def on_assert(self, assert_config: Any, actual: Any) -> None:
        """断言执行时"""
        pass


class AssertPlugin(BasePlugin):
    """断言插件 - 自定义断言逻辑"""

    meta = PluginMeta(name="assert_plugin", plugin_type=PluginType.ASSERTION)

    @abstractmethod
    def assert_func(self, actual: Any, expected: Any, **kwargs) -> tuple[bool, str]:
        """执行断言，返回 (是否通过, 消息)"""
        pass


class DataGeneratorPlugin(BasePlugin):
    """数据生成插件"""

    meta = PluginMeta(name="data_generator_plugin", plugin_type=PluginType.DATA_GENERATOR)

    @abstractmethod
    def generate(self, **kwargs) -> Any:
        """生成数据"""
        pass


class PluginManager:
    """插件管理器"""

    def __init__(self):
        self._plugins: dict[str, BasePlugin] = {}
        self._hooks: list[HookPlugin] = []
        self._assert_plugins: dict[str, AssertPlugin] = {}
        self._data_plugins: dict[str, DataGeneratorPlugin] = {}

    def register(self, plugin: BasePlugin, context: Optional[dict[str, Any]] = None) -> None:
        """注册插件"""
        name = plugin.meta.name
        if name in self._plugins:
            logger.warning(f"插件 [{name}] 已存在，将覆盖")

        self._plugins[name] = plugin
        plugin.activate(context or {})

        # 按类型分类
        if isinstance(plugin, HookPlugin):
            self._hooks.append(plugin)
        elif isinstance(plugin, AssertPlugin):
            self._assert_plugins[name] = plugin
        elif isinstance(plugin, DataGeneratorPlugin):
            self._data_plugins[name] = plugin

        logger.info(f"插件已注册: {name} v{plugin.meta.version} [{plugin.meta.plugin_type}]")

    def unregister(self, name: str) -> None:
        """注销插件"""
        plugin = self._plugins.pop(name, None)
        if plugin:
            plugin.deactivate()
            if isinstance(plugin, HookPlugin):
                self._hooks = [h for h in self._hooks if h.meta.name != name]
            elif isinstance(plugin, AssertPlugin):
                self._assert_plugins.pop(name, None)
            elif isinstance(plugin, DataGeneratorPlugin):
                self._data_plugins.pop(name, None)
            logger.info(f"插件已注销: {name}")

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """获取插件"""
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict[str, str]]:
        """列出所有已注册插件"""
        return [
            {
                "name": p.meta.name,
                "version": p.meta.version,
                "type": p.meta.plugin_type,
                "description": p.meta.description,
            }
            for p in self._plugins.values()
        ]

    # --- Hook 调度 ---

    def fire_test_start(self, test_case: Any) -> None:
        for hook in self._hooks:
            try:
                hook.on_test_start(test_case)
            except Exception as e:
                logger.warning(f"插件 [{hook.meta.name}] on_test_start 异常: {e}")

    def fire_test_end(self, test_case: Any, result: Any) -> None:
        for hook in self._hooks:
            try:
                hook.on_test_end(test_case, result)
            except Exception as e:
                logger.warning(f"插件 [{hook.meta.name}] on_test_end 异常: {e}")

    def fire_step_start(self, step: Any) -> None:
        for hook in self._hooks:
            try:
                hook.on_step_start(step)
            except Exception as e:
                logger.warning(f"插件 [{hook.meta.name}] on_step_start 异常: {e}")

    def fire_step_end(self, step: Any, result: Any) -> None:
        for hook in self._hooks:
            try:
                hook.on_step_end(step, result)
            except Exception as e:
                logger.warning(f"插件 [{hook.meta.name}] on_step_end 异常: {e}")

    def fire_on_request(self, request_kwargs: dict[str, Any]) -> dict[str, Any]:
        for hook in self._hooks:
            try:
                request_kwargs = hook.on_request(request_kwargs)
            except Exception as e:
                logger.warning(f"插件 [{hook.meta.name}] on_request 异常: {e}")
        return request_kwargs

    def fire_on_response(self, response: Any) -> Any:
        for hook in self._hooks:
            try:
                response = hook.on_response(response)
            except Exception as e:
                logger.warning(f"插件 [{hook.meta.name}] on_response 异常: {e}")
        return response

    # --- 断言插件调度 ---

    def run_assert(self, plugin_name: str, actual: Any, expected: Any, **kwargs) -> tuple[bool, str]:
        """运行断言插件"""
        plugin = self._assert_plugins.get(plugin_name)
        if not plugin:
            return False, f"断言插件不存在: {plugin_name}"
        return plugin.assert_func(actual, expected, **kwargs)

    # --- 数据生成插件调度 ---

    def generate_data(self, plugin_name: str, **kwargs) -> Any:
        """使用数据生成插件生成数据"""
        plugin = self._data_plugins.get(plugin_name)
        if not plugin:
            raise ValueError(f"数据生成插件不存在: {plugin_name}")
        return plugin.generate(**kwargs)

    # --- 动态加载 ---

    def load_from_module(self, module_path: str, context: Optional[dict[str, Any]] = None) -> None:
        """从 Python 模块加载插件"""
        try:
            module = importlib.import_module(module_path)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BasePlugin) and obj is not BasePlugin and not inspect.isabstract(obj):
                    # 跳过基类
                    if obj in (HookPlugin, AssertPlugin, DataGeneratorPlugin):
                        continue
                    plugin = obj()
                    self.register(plugin, context)
        except Exception as e:
            logger.error(f"加载插件模块失败 [{module_path}]: {e}")

    def load_from_directory(self, directory: str | Path, context: Optional[dict[str, Any]] = None) -> None:
        """从目录加载所有插件"""
        path = Path(directory)
        if not path.is_dir():
            logger.warning(f"插件目录不存在: {path}")
            return

        for py_file in path.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            module_name = py_file.stem
            try:
                import sys
                sys.path.insert(0, str(path))
                self.load_from_module(module_name, context)
                sys.path.pop(0)
            except Exception as e:
                logger.warning(f"加载插件文件失败 [{py_file}]: {e}")
