"""数据提取器 - 支持 JSONPath/XPath/正则/Header 提取"""

from __future__ import annotations

import re
from typing import Any

from jsonpath_ng.ext import parse as jsonpath_parse
from loguru import logger
from lxml import etree

from smartapi.core.models import ExtractConfig, ExtractType


class ExtractError(Exception):
    """提取错误"""
    pass


class DataExtractor:
    """从 HTTP 响应中提取数据"""

    @staticmethod
    def extract_jsonpath(data: Any, expression: str) -> Any:
        """JSONPath 提取"""
        try:
            matches = jsonpath_parse(expression).find(data)
            if not matches:
                return None
            if len(matches) == 1:
                return matches[0].value
            return [m.value for m in matches]
        except Exception as e:
            raise ExtractError(f"JSONPath 提取失败 [{expression}]: {e}") from e

    @staticmethod
    def extract_xpath(text: str, expression: str) -> Any:
        """XPath 提取（适用于 XML/HTML 响应）"""
        try:
            tree = etree.fromstring(text.encode() if isinstance(text, str) else text)
            results = tree.xpath(expression)
            if not results:
                return None
            if len(results) == 1:
                return results[0] if isinstance(results[0], str) else etree.tostring(results[0], encoding="unicode")
            return [r if isinstance(r, str) else etree.tostring(r, encoding="unicode") for r in results]
        except Exception as e:
            raise ExtractError(f"XPath 提取失败 [{expression}]: {e}") from e

    @staticmethod
    def extract_regex(text: str, expression: str) -> Any:
        """正则表达式提取"""
        try:
            matches = re.findall(expression, text)
            if not matches:
                return None
            if len(matches) == 1:
                return matches[0]
            return matches
        except Exception as e:
            raise ExtractError(f"正则提取失败 [{expression}]: {e}") from e

    @staticmethod
    def extract_header(headers: dict[str, str], name: str) -> Any:
        """从响应头中提取"""
        # 大小写不敏感查找
        for key, value in headers.items():
            if key.lower() == name.lower():
                return value
        return None

    @classmethod
    def extract(
        cls,
        config: ExtractConfig,
        response_body: Any,
        response_headers: dict[str, str],
        response_text: str = "",
    ) -> Any:
        """根据配置提取数据"""
        try:
            if config.type == ExtractType.JSONPATH:
                result = cls.extract_jsonpath(response_body, config.expression)
            elif config.type == ExtractType.XPATH:
                result = cls.extract_xpath(response_text, config.expression)
            elif config.type == ExtractType.REGEX:
                result = cls.extract_regex(response_text, config.expression)
            elif config.type == ExtractType.HEADER:
                result = cls.extract_header(response_headers, config.expression)
            else:
                raise ExtractError(f"不支持的提取类型: {config.type}")

            if result is None:
                if config.default is not None:
                    logger.debug(f"提取 [{config.name}] 无结果，使用默认值: {config.default}")
                    return config.default
                logger.warning(f"提取 [{config.name}] 无结果且无默认值")
                return None

            logger.debug(f"提取 [{config.name}] = {result}")
            return result

        except ExtractError:
            raise
        except Exception as e:
            raise ExtractError(f"提取 [{config.name}] 失败: {e}") from e
