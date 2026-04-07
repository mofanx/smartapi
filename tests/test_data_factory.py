"""数据工厂单元测试"""

import pytest

from smartapi.mock.data_factory import DataFactory


class TestDataFactory:
    """数据工厂测试"""

    def setup_method(self):
        self.factory = DataFactory()

    # --- 基础类型 ---
    def test_generate_string(self):
        result = self.factory.generate("string")
        assert isinstance(result, str)
        assert len(result) >= 8

    def test_generate_string_with_length(self):
        result = self.factory.generate("string", min_length=5, max_length=5)
        assert len(result) == 5

    def test_generate_int(self):
        result = self.factory.generate("int")
        assert isinstance(result, int)

    def test_generate_int_range(self):
        result = self.factory.generate("int", min=10, max=20)
        assert 10 <= result <= 20

    def test_generate_float(self):
        result = self.factory.generate("float")
        assert isinstance(result, float)

    def test_generate_bool(self):
        result = self.factory.generate("bool")
        assert isinstance(result, bool)

    def test_generate_uuid(self):
        result = self.factory.generate("uuid")
        assert isinstance(result, str)
        assert len(result) == 36  # UUID format

    def test_generate_timestamp(self):
        result = self.factory.generate("timestamp")
        assert isinstance(result, int)
        assert result > 1000000000

    # --- 个人信息 ---
    def test_generate_name(self):
        result = self.factory.generate("name")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_phone(self):
        result = self.factory.generate("phone")
        assert isinstance(result, str)

    def test_generate_email(self):
        result = self.factory.generate("email")
        assert "@" in result

    def test_generate_id_card(self):
        result = self.factory.generate("id_card")
        assert isinstance(result, str)

    def test_generate_address(self):
        result = self.factory.generate("address")
        assert isinstance(result, str)

    # --- 网络 ---
    def test_generate_ip(self):
        result = self.factory.generate("ip")
        assert result.count(".") == 3

    def test_generate_url(self):
        result = self.factory.generate("url")
        assert result.startswith("http")

    # --- 业务类型 ---
    def test_generate_order_no(self):
        result = self.factory.generate("order_no")
        assert result.startswith("ORD")

    def test_generate_order_no_custom_prefix(self):
        result = self.factory.generate("order_no", prefix="PAY")
        assert result.startswith("PAY")

    def test_generate_choice(self):
        options = ["a", "b", "c"]
        result = self.factory.generate("choice", options=options)
        assert result in options

    # --- 复合类型 ---
    def test_generate_list(self):
        result = self.factory.generate("list", item_type="int", count=5)
        assert isinstance(result, list)
        assert len(result) == 5
        assert all(isinstance(x, int) for x in result)

    def test_generate_dict(self):
        result = self.factory.generate("dict")
        assert isinstance(result, dict)
        assert "id" in result

    # --- Schema 生成 ---
    def test_generate_from_schema(self):
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "min": 1, "max": 100},
                "name": {"type": "string", "generator": "name"},
                "email": {"type": "string", "generator": "email"},
                "tags": {"type": "array", "items": {"type": "string", "generator": "word"}, "count": 3},
            },
        }
        result = self.factory._generate_from_schema(schema)
        assert isinstance(result, dict)
        assert isinstance(result["id"], int)
        assert isinstance(result["name"], str)
        assert "@" in result["email"]
        assert isinstance(result["tags"], list)
        assert len(result["tags"]) == 3

    # --- 数据池 ---
    def test_pool_register_and_get(self):
        self.factory.register_pool("users", [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
        ])
        result = self.factory.get_from_pool("users")
        assert result["id"] in [1, 2, 3]

    def test_pool_sequential(self):
        self.factory.register_pool("items", ["a", "b", "c"])
        results = [self.factory.get_from_pool("items", mode="sequential") for _ in range(3)]
        assert results == ["a", "b", "c"]

    def test_pool_unique(self):
        self.factory.register_pool("codes", [1, 2, 3])
        results = set()
        for _ in range(3):
            results.add(self.factory.get_from_pool("codes", mode="unique"))
        assert results == {1, 2, 3}

    def test_pool_exhausted(self):
        self.factory.register_pool("small", ["only_one"])
        self.factory.get_from_pool("small", mode="unique")
        with pytest.raises(ValueError, match="已耗尽"):
            self.factory.get_from_pool("small", mode="unique")

    def test_pool_release(self):
        self.factory.register_pool("items", ["x", "y"])
        item = self.factory.get_from_pool("items", mode="unique")
        self.factory.release_pool_item("items", item)
        # 释放后应该可以再次获取
        result = self.factory.get_from_pool("items", mode="unique")
        assert result is not None

    def test_pool_reset(self):
        self.factory.register_pool("items", ["a", "b"])
        self.factory.get_from_pool("items", mode="unique")
        self.factory.get_from_pool("items", mode="unique")
        self.factory.reset_pool("items")
        result = self.factory.get_from_pool("items", mode="unique")
        assert result in ["a", "b"]

    def test_pool_nonexistent(self):
        with pytest.raises(ValueError, match="不存在"):
            self.factory.get_from_pool("nonexistent")

    # --- 自定义生成器 ---
    def test_register_custom_generator(self):
        self.factory.register_generator("ticket_id", lambda **kw: f"TK-{self.factory.generate('int', min=10000, max=99999)}")
        result = self.factory.generate("ticket_id")
        assert result.startswith("TK-")

    def test_list_generators(self):
        generators = self.factory.list_generators()
        assert "string" in generators
        assert "email" in generators
        assert "phone" in generators
        assert len(generators) > 30

    # --- 未知类型 ---
    def test_unknown_type(self):
        result = self.factory.generate("unknown_type_xyz")
        assert isinstance(result, str)  # 回退到随机字符串
