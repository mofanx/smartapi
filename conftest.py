"""项目根 conftest - 为 pytest 提供 SmartAPI fixtures"""

import pytest

from smartapi.core.variables import VariableManager
from smartapi.core.executor import TestExecutor
from smartapi.mock.data_factory import DataFactory
from smartapi.plugins.base import PluginManager


@pytest.fixture(scope="session")
def smartapi_variable_manager():
    """全局变量管理器"""
    return VariableManager()


@pytest.fixture(scope="session")
def smartapi_data_factory():
    """全局数据工厂"""
    return DataFactory()


@pytest.fixture(scope="session")
def smartapi_plugin_manager():
    """全局插件管理器"""
    return PluginManager()


@pytest.fixture
def smartapi_executor(smartapi_variable_manager):
    """测试执行器（每个测试一个新实例）"""
    executor = TestExecutor(variable_manager=smartapi_variable_manager)
    yield executor
    executor.close()
