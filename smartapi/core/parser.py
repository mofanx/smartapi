"""YAML/JSON 用例解析器"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from loguru import logger
from pydantic import ValidationError

from smartapi.core.models import (
    EnvironmentConfig,
    TestCaseConfig,
    TestSuiteConfig,
)


class ParserError(Exception):
    """解析错误"""
    pass


class TestCaseParser:
    """声明式测试用例解析器，支持 YAML 和 JSON"""

    @staticmethod
    def load_file(file_path: str | Path) -> dict[str, Any]:
        """加载 YAML 或 JSON 文件"""
        path = Path(file_path)
        if not path.exists():
            raise ParserError(f"文件不存在: {path}")

        content = path.read_text(encoding="utf-8")
        if not content.strip():
            raise ParserError(f"文件为空: {path}")

        suffix = path.suffix.lower()
        try:
            if suffix in (".yaml", ".yml"):
                data = yaml.safe_load(content)
            elif suffix == ".json":
                data = json.loads(content)
            else:
                raise ParserError(f"不支持的文件格式: {suffix}，仅支持 .yaml/.yml/.json")
        except yaml.YAMLError as e:
            raise ParserError(f"YAML 解析错误: {e}") from e
        except json.JSONDecodeError as e:
            raise ParserError(f"JSON 解析错误: {e}") from e

        if not isinstance(data, dict):
            raise ParserError(f"文件顶层必须是字典类型，实际为: {type(data).__name__}")

        return data

    @classmethod
    def parse_test_case(cls, data: dict[str, Any]) -> TestCaseConfig:
        """解析单个测试用例"""
        try:
            return TestCaseConfig.model_validate(data)
        except ValidationError as e:
            raise ParserError(f"用例格式校验失败:\n{e}") from e

    @classmethod
    def parse_test_suite(cls, data: dict[str, Any]) -> TestSuiteConfig:
        """解析测试集"""
        try:
            return TestSuiteConfig.model_validate(data)
        except ValidationError as e:
            raise ParserError(f"测试集格式校验失败:\n{e}") from e

    @classmethod
    def parse_environment(cls, data: dict[str, Any]) -> EnvironmentConfig:
        """解析环境配置"""
        try:
            return EnvironmentConfig.model_validate(data)
        except ValidationError as e:
            raise ParserError(f"环境配置格式校验失败:\n{e}") from e

    @classmethod
    def load_test_case(cls, file_path: str | Path) -> TestCaseConfig:
        """从文件加载并解析测试用例"""
        data = cls.load_file(file_path)
        return cls.parse_test_case(data)

    @classmethod
    def load_test_suite(cls, file_path: str | Path) -> TestSuiteConfig:
        """从文件加载并解析测试集"""
        data = cls.load_file(file_path)
        return cls.parse_test_suite(data)

    @classmethod
    def load_environment(cls, file_path: str | Path) -> EnvironmentConfig:
        """从文件加载并解析环境配置"""
        data = cls.load_file(file_path)
        return cls.parse_environment(data)

    @classmethod
    def discover_test_files(cls, directory: str | Path, recursive: bool = True) -> list[Path]:
        """发现目录中的测试用例文件"""
        path = Path(directory)
        if not path.is_dir():
            raise ParserError(f"目录不存在: {path}")

        patterns = ["*.yaml", "*.yml", "*.json"]
        files = []
        for pattern in patterns:
            if recursive:
                files.extend(path.rglob(pattern))
            else:
                files.extend(path.glob(pattern))

        # 过滤: 仅包含含有 name + steps 的文件
        test_files = []
        for f in sorted(files):
            try:
                data = cls.load_file(f)
                if "steps" in data or "test_cases" in data:
                    test_files.append(f)
            except Exception:
                continue

        logger.info(f"在 {path} 中发现 {len(test_files)} 个测试文件")
        return test_files

    @classmethod
    def load_all_test_cases(cls, directory: str | Path) -> list[TestCaseConfig]:
        """加载目录中所有测试用例"""
        files = cls.discover_test_files(directory)
        cases = []
        for f in files:
            try:
                data = cls.load_file(f)
                if "test_cases" in data:
                    suite = cls.parse_test_suite(data)
                    cases.extend(suite.test_cases)
                elif "steps" in data:
                    case = cls.parse_test_case(data)
                    cases.append(case)
            except ParserError as e:
                logger.warning(f"跳过文件 {f}: {e}")
        return cases

    @classmethod
    def validate_yaml_string(cls, yaml_string: str) -> tuple[bool, str | TestCaseConfig]:
        """校验 YAML 字符串是否为有效的测试用例"""
        try:
            data = yaml.safe_load(yaml_string)
            if not isinstance(data, dict):
                return False, "YAML 顶层必须是字典类型"
            case = cls.parse_test_case(data)
            return True, case
        except yaml.YAMLError as e:
            return False, f"YAML 语法错误: {e}"
        except ParserError as e:
            return False, str(e)
