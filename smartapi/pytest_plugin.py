"""pytest 插件 - 将声明式 YAML/JSON 用例集成到 pytest"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from loguru import logger

from smartapi.core.executor import TestExecutor
from smartapi.core.models import TestCaseConfig, TestSuiteConfig
from smartapi.core.parser import TestCaseParser
from smartapi.core.variables import VariableManager


def pytest_addoption(parser: pytest.Parser):
    """添加命令行参数"""
    group = parser.getgroup("smartapi", "SmartAPI-Test 配置")
    group.addoption(
        "--smartapi-dir",
        action="store",
        default="testcases",
        help="测试用例目录 (默认: testcases)",
    )
    group.addoption(
        "--smartapi-env",
        action="store",
        default=None,
        help="环境配置文件路径",
    )
    group.addoption(
        "--smartapi-tags",
        action="store",
        default=None,
        help="按标签筛选用例 (逗号分隔)",
    )
    group.addoption(
        "--smartapi-base-url",
        action="store",
        default="",
        help="全局 base URL",
    )
    group.addoption(
        "--smartapi-timeout",
        action="store",
        default="30",
        help="全局超时时间(秒)",
    )


def pytest_configure(config: pytest.Config):
    """注册标记"""
    config.addinivalue_line("markers", "smartapi: SmartAPI 声明式测试用例")


class SmartAPIItem(pytest.Item):
    """SmartAPI 测试用例项"""

    def __init__(
        self,
        name: str,
        parent: pytest.Collector,
        test_case: TestCaseConfig,
        variable_manager: VariableManager,
        base_url: str = "",
        timeout: float = 30.0,
    ):
        super().__init__(name, parent)
        self.test_case = test_case
        self.variable_manager = variable_manager
        self.base_url = base_url
        self.timeout = timeout
        # 设置标签为 pytest marker
        for tag in test_case.tags:
            self.add_marker(pytest.mark.smartapi)
            self.add_marker(getattr(pytest.mark, tag))

    def runtest(self):
        """执行测试"""
        executor = TestExecutor(
            variable_manager=self.variable_manager,
            base_url=self.base_url or self.test_case.base_url or "",
            timeout=self.timeout,
        )
        try:
            result = executor.execute_test_case(self.test_case)
            if not result.success:
                fail_details = []
                for sr in result.step_results:
                    if not sr.success and not sr.skipped:
                        fail_details.append(f"  步骤 [{sr.step_name}]: {sr.error or '断言失败'}")
                        for ar in sr.assert_results:
                            if not ar.passed:
                                fail_details.append(f"    - {ar.message}")
                raise SmartAPITestFailure(
                    f"用例 [{self.test_case.name}] 失败:\n" + "\n".join(fail_details),
                    result=result,
                )
        finally:
            executor.close()

    def repr_failure(self, excinfo, style=None):
        """自定义失败报告"""
        if isinstance(excinfo.value, SmartAPITestFailure):
            return str(excinfo.value)
        return super().repr_failure(excinfo, style)

    def reportinfo(self):
        return self.path, None, f"smartapi: {self.test_case.name}"


class SmartAPITestFailure(Exception):
    """SmartAPI 测试失败异常"""
    def __init__(self, message: str, result=None):
        super().__init__(message)
        self.result = result


class SmartAPIFile(pytest.File):
    """SmartAPI 测试文件收集器"""

    def collect(self):
        """收集文件中的测试用例"""
        config = self.config
        base_url = config.getoption("--smartapi-base-url", default="")
        timeout = float(config.getoption("--smartapi-timeout", default="30"))
        tags_filter = config.getoption("--smartapi-tags", default=None)
        env_file = config.getoption("--smartapi-env", default=None)

        # 初始化变量管理器
        var_manager = VariableManager()

        # 加载环境配置
        if env_file:
            env_path = Path(env_file)
            if env_path.exists():
                try:
                    env_config = TestCaseParser.load_environment(env_path)
                    var_manager.set_env_vars(env_config.variables)
                    if not base_url:
                        base_url = env_config.base_url
                except Exception as e:
                    logger.warning(f"加载环境配置失败: {e}")

        # 解析文件
        try:
            data = TestCaseParser.load_file(self.path)
        except Exception as e:
            logger.warning(f"解析文件失败 {self.path}: {e}")
            return

        # 解析标签过滤
        filter_tags = set()
        if tags_filter:
            filter_tags = {t.strip() for t in tags_filter.split(",")}

        # 收集用例
        test_cases = []
        if "test_cases" in data:
            try:
                suite = TestCaseParser.parse_test_suite(data)
                if suite.variables:
                    var_manager.set_global_vars(suite.variables)
                test_cases = suite.test_cases
            except Exception as e:
                logger.warning(f"解析测试集失败 {self.path}: {e}")
                return
        elif "steps" in data:
            try:
                case = TestCaseParser.parse_test_case(data)
                test_cases = [case]
            except Exception as e:
                logger.warning(f"解析用例失败 {self.path}: {e}")
                return

        for case in test_cases:
            # 标签过滤
            if filter_tags and not filter_tags.intersection(set(case.tags)):
                continue

            yield SmartAPIItem.from_parent(
                self,
                name=case.name,
                test_case=case,
                variable_manager=var_manager,
                base_url=base_url,
                timeout=timeout,
            )


def pytest_collect_file(parent: pytest.Collector, file_path: Path):
    """收集 YAML/JSON 测试文件"""
    testcase_dir = parent.config.getoption("--smartapi-dir", default="testcases")

    # 检查文件是否在测试用例目录中
    if file_path.suffix in (".yaml", ".yml", ".json"):
        # 简单检查文件是否包含 steps 或 test_cases
        try:
            content = file_path.read_text(encoding="utf-8")
            if file_path.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(content)
            else:
                data = json.loads(content)

            if isinstance(data, dict) and ("steps" in data or "test_cases" in data):
                return SmartAPIFile.from_parent(parent, path=file_path)
        except Exception:
            pass

    return None
