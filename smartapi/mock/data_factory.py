"""Mock 数据工厂 - 丰富的测试数据生成器"""

from __future__ import annotations

import json
import random
import re
import string
import time
import uuid
from typing import Any, Optional

from faker import Faker
from loguru import logger


class DataFactory:
    """测试数据工厂，支持多种数据生成规则"""

    def __init__(self, locale: str = "zh_CN"):
        self.fake = Faker(locale)
        self._generators: dict[str, callable] = {}
        self._data_pools: dict[str, list] = {}
        self._pool_indices: dict[str, int] = {}
        self._pool_locks: dict[str, set] = {}
        self._register_builtin_generators()

    def _register_builtin_generators(self):
        """注册内置数据生成器"""
        f = self.fake

        self._generators = {
            # 基础类型
            "string": lambda **kw: self._random_string(**kw),
            "int": lambda **kw: random.randint(kw.get("min", 1), kw.get("max", 99999)),
            "float": lambda **kw: round(random.uniform(kw.get("min", 0.0), kw.get("max", 100.0)), kw.get("precision", 2)),
            "bool": lambda **kw: random.choice([True, False]),
            "uuid": lambda **kw: str(uuid.uuid4()),
            "timestamp": lambda **kw: int(time.time()),
            "timestamp_ms": lambda **kw: int(time.time() * 1000),
            "date": lambda **kw: f.date(pattern=kw.get("format", "%Y-%m-%d")),
            "datetime": lambda **kw: f.date_time().strftime(kw.get("format", "%Y-%m-%d %H:%M:%S")),
            "time": lambda **kw: f.time(pattern=kw.get("format", "%H:%M:%S")),

            # 个人信息
            "name": lambda **kw: f.name(),
            "first_name": lambda **kw: f.first_name(),
            "last_name": lambda **kw: f.last_name(),
            "phone": lambda **kw: f.phone_number(),
            "email": lambda **kw: f.email(),
            "id_card": lambda **kw: f.ssn(),
            "address": lambda **kw: f.address(),
            "city": lambda **kw: f.city(),
            "province": lambda **kw: f.province(),
            "postcode": lambda **kw: f.postcode(),
            "company": lambda **kw: f.company(),
            "job": lambda **kw: f.job(),

            # 网络
            "ip": lambda **kw: f.ipv4(),
            "ipv6": lambda **kw: f.ipv6(),
            "mac": lambda **kw: f.mac_address(),
            "url": lambda **kw: f.url(),
            "domain": lambda **kw: f.domain_name(),
            "user_agent": lambda **kw: f.user_agent(),

            # 文本
            "word": lambda **kw: f.word(),
            "sentence": lambda **kw: f.sentence(nb_words=kw.get("words", 6)),
            "paragraph": lambda **kw: f.paragraph(nb_sentences=kw.get("sentences", 3)),
            "text": lambda **kw: f.text(max_nb_chars=kw.get("max_chars", 200)),

            # 金融
            "credit_card": lambda **kw: f.credit_card_number(),
            "bank_account": lambda **kw: f.bban(),
            "amount": lambda **kw: round(random.uniform(kw.get("min", 0.01), kw.get("max", 9999.99)), 2),

            # 编码
            "md5": lambda **kw: f.md5(),
            "sha256": lambda **kw: f.sha256(),
            "base64": lambda **kw: self._random_base64(**kw),

            # 选项
            "choice": lambda **kw: random.choice(kw.get("options", ["a", "b", "c"])),
            "enum": lambda **kw: random.choice(kw.get("values", [1, 2, 3])),

            # 复合类型
            "list": lambda **kw: self._generate_list(**kw),
            "dict": lambda **kw: self._generate_dict(**kw),
            "json_object": lambda **kw: self._generate_json_object(**kw),

            # 业务常用
            "order_no": lambda **kw: self._generate_order_no(**kw),
            "sku": lambda **kw: f"SKU{random.randint(100000, 999999)}",
            "barcode": lambda **kw: f.ean13(),
            "color_hex": lambda **kw: f.hex_color(),
            "file_name": lambda **kw: f.file_name(extension=kw.get("ext", "txt")),
        }

    @staticmethod
    def _random_string(min_length: int = 8, max_length: int = 16, chars: str = "", **kw) -> str:
        length = random.randint(min_length, max_length)
        charset = chars or string.ascii_letters + string.digits
        return "".join(random.choice(charset) for _ in range(length))

    @staticmethod
    def _random_base64(length: int = 16, **kw) -> str:
        import base64
        raw = bytes(random.getrandbits(8) for _ in range(length))
        return base64.b64encode(raw).decode()

    def _generate_list(self, item_type: str = "string", count: int = 3, **kw) -> list:
        gen = self._generators.get(item_type, self._generators["string"])
        return [gen(**kw) for _ in range(count)]

    def _generate_dict(self, fields: Optional[dict] = None, **kw) -> dict:
        if fields:
            return {k: self.generate(v) if isinstance(v, str) else v for k, v in fields.items()}
        return {
            "id": random.randint(1, 99999),
            "name": self.fake.name(),
            "value": self.fake.word(),
        }

    def _generate_json_object(self, schema: Optional[dict] = None, **kw) -> dict:
        if schema:
            return self._generate_from_schema(schema)
        return self._generate_dict(**kw)

    @staticmethod
    def _generate_order_no(prefix: str = "ORD", **kw) -> str:
        ts = time.strftime("%Y%m%d%H%M%S")
        rand = random.randint(1000, 9999)
        return f"{prefix}{ts}{rand}"

    def generate(self, type_name: str, **kwargs) -> Any:
        """生成指定类型的 Mock 数据"""
        gen = self._generators.get(type_name)
        if gen is None:
            logger.warning(f"未知的数据类型: {type_name}，返回随机字符串")
            return self._random_string()
        try:
            return gen(**kwargs)
        except Exception as e:
            logger.error(f"生成 {type_name} 数据失败: {e}")
            return None

    def generate_by_pattern(self, pattern: str) -> str:
        """按正则模式生成数据（简化版）"""
        # 支持简单的正则模式生成
        result = []
        i = 0
        while i < len(pattern):
            c = pattern[i]
            if c == '\\' and i + 1 < len(pattern):
                nc = pattern[i + 1]
                if nc == 'd':
                    result.append(str(random.randint(0, 9)))
                elif nc == 'w':
                    result.append(random.choice(string.ascii_letters + string.digits))
                elif nc == 's':
                    result.append(' ')
                else:
                    result.append(nc)
                i += 2
            elif c == '[' and ']' in pattern[i:]:
                end = pattern.index(']', i)
                chars = pattern[i+1:end]
                result.append(random.choice(chars))
                i = end + 1
            elif c in ('^', '$', '+', '*', '?', '.', '(', ')'):
                if c == '.':
                    result.append(random.choice(string.ascii_letters))
                i += 1
            else:
                result.append(c)
                i += 1
        return "".join(result)

    def _generate_from_schema(self, schema: dict) -> Any:
        """根据 JSON Schema 风格的定义生成数据"""
        schema_type = schema.get("type", "string")

        if schema_type == "object":
            properties = schema.get("properties", {})
            result = {}
            for key, prop_schema in properties.items():
                result[key] = self._generate_from_schema(prop_schema)
            return result

        elif schema_type == "array":
            items_schema = schema.get("items", {"type": "string"})
            count = schema.get("count", random.randint(1, 5))
            return [self._generate_from_schema(items_schema) for _ in range(count)]

        elif schema_type == "string":
            gen_type = schema.get("generator", "string")
            return self.generate(gen_type, **{k: v for k, v in schema.items() if k not in ("type", "generator")})

        elif schema_type in ("int", "integer"):
            return random.randint(schema.get("min", 1), schema.get("max", 99999))

        elif schema_type in ("float", "number"):
            return round(random.uniform(schema.get("min", 0.0), schema.get("max", 100.0)), 2)

        elif schema_type in ("bool", "boolean"):
            return random.choice([True, False])

        return self.generate(schema_type)

    # --- 数据池管理 ---

    def register_pool(self, name: str, data: list[Any]):
        """注册测试数据池"""
        self._data_pools[name] = list(data)
        self._pool_indices[name] = 0
        self._pool_locks[name] = set()
        logger.debug(f"注册数据池: {name} ({len(data)} 条)")

    def get_from_pool(self, name: str, mode: str = "random") -> Any:
        """从数据池获取数据

        Args:
            name: 数据池名称
            mode: 获取模式 - random(随机) / sequential(顺序) / unique(不重复随机)
        """
        pool = self._data_pools.get(name)
        if not pool:
            raise ValueError(f"数据池不存在: {name}")

        available = [i for i, _ in enumerate(pool) if i not in self._pool_locks.get(name, set())]
        if not available:
            raise ValueError(f"数据池 {name} 已耗尽")

        if mode == "random":
            idx = random.choice(available)
        elif mode == "sequential":
            idx = self._pool_indices.get(name, 0)
            while idx in self._pool_locks.get(name, set()):
                idx = (idx + 1) % len(pool)
            self._pool_indices[name] = (idx + 1) % len(pool)
        elif mode == "unique":
            idx = random.choice(available)
            self._pool_locks.setdefault(name, set()).add(idx)
        else:
            idx = random.choice(available)

        return pool[idx]

    def release_pool_item(self, name: str, item: Any):
        """释放数据池中的数据项"""
        pool = self._data_pools.get(name)
        if pool and item in pool:
            idx = pool.index(item)
            self._pool_locks.get(name, set()).discard(idx)

    def reset_pool(self, name: str):
        """重置数据池"""
        self._pool_indices[name] = 0
        self._pool_locks[name] = set()

    def register_generator(self, name: str, func: callable):
        """注册自定义数据生成器"""
        self._generators[name] = func

    def list_generators(self) -> list[str]:
        """列出所有可用的数据生成器"""
        return sorted(self._generators.keys())
