"""鉴权处理器单元测试"""

import pytest

from smartapi.auth.handler import AuthHandler, TokenCache
from smartapi.core.models import AuthConfig, AuthType
from smartapi.core.variables import VariableManager


class TestTokenCache:
    """Token 缓存测试"""

    def test_set_and_get(self):
        cache = TokenCache()
        cache.set("key1", "token_value")
        assert cache.get("key1") == "token_value"

    def test_get_nonexistent(self):
        cache = TokenCache()
        assert cache.get("missing") is None

    def test_expired_token(self):
        cache = TokenCache()
        cache.set("key1", "token_value", expire_seconds=-1)  # 已过期
        assert cache.get("key1") is None

    def test_clear_specific(self):
        cache = TokenCache()
        cache.set("key1", "val1")
        cache.set("key2", "val2")
        cache.clear("key1")
        assert cache.get("key1") is None
        assert cache.get("key2") == "val2"

    def test_clear_all(self):
        cache = TokenCache()
        cache.set("key1", "val1")
        cache.set("key2", "val2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestAuthHandler:
    """鉴权处理器测试"""

    def setup_method(self):
        self.vm = VariableManager()
        self.handler = AuthHandler(variable_manager=self.vm)

    def teardown_method(self):
        self.handler.close()

    def test_no_auth(self):
        config = AuthConfig(type=AuthType.NONE)
        kwargs = {"headers": {}, "url": "http://test.com"}
        result = self.handler.apply_auth(config, kwargs)
        assert "Authorization" not in result.get("headers", {})

    def test_basic_auth(self):
        config = AuthConfig(type=AuthType.BASIC, username="admin", password="pass123")
        kwargs = {"headers": {}}
        result = self.handler.apply_auth(config, kwargs)
        assert result["auth"] == ("admin", "pass123")

    def test_basic_auth_with_variables(self):
        self.vm.set_global_vars({"user": "test_user", "pwd": "test_pwd"})
        config = AuthConfig(type=AuthType.BASIC, username="${user}", password="${pwd}")
        kwargs = {"headers": {}}
        result = self.handler.apply_auth(config, kwargs)
        assert result["auth"] == ("test_user", "test_pwd")

    def test_bearer_token(self):
        config = AuthConfig(type=AuthType.BEARER, token="my_token_123")
        kwargs = {"headers": {}}
        result = self.handler.apply_auth(config, kwargs)
        assert result["headers"]["Authorization"] == "Bearer my_token_123"

    def test_bearer_custom_prefix(self):
        config = AuthConfig(type=AuthType.BEARER, token="abc", token_prefix="Token")
        kwargs = {"headers": {}}
        result = self.handler.apply_auth(config, kwargs)
        assert result["headers"]["Authorization"] == "Token abc"

    def test_api_key_in_header(self):
        config = AuthConfig(
            type=AuthType.API_KEY,
            api_key_name="X-API-Key",
            api_key_value="secret123",
            api_key_in="header",
        )
        kwargs = {"headers": {}}
        result = self.handler.apply_auth(config, kwargs)
        assert result["headers"]["X-API-Key"] == "secret123"

    def test_api_key_in_query(self):
        config = AuthConfig(
            type=AuthType.API_KEY,
            api_key_name="api_key",
            api_key_value="secret456",
            api_key_in="query",
        )
        kwargs = {"headers": {}}
        result = self.handler.apply_auth(config, kwargs)
        assert result["params"]["api_key"] == "secret456"

    def test_api_key_in_cookie(self):
        config = AuthConfig(
            type=AuthType.API_KEY,
            api_key_name="session",
            api_key_value="sess_abc",
            api_key_in="cookie",
        )
        kwargs = {"headers": {}}
        result = self.handler.apply_auth(config, kwargs)
        assert result["cookies"]["session"] == "sess_abc"

    def test_custom_auth_script(self):
        config = AuthConfig(
            type=AuthType.CUSTOM,
            custom_script="""
import time
ts = str(int(time.time()))
sign = hashlib.md5(f"secret{ts}".encode()).hexdigest()
kwargs["headers"]["X-Timestamp"] = ts
kwargs["headers"]["X-Sign"] = sign
""",
        )
        kwargs = {"headers": {}}
        result = self.handler.apply_auth(config, kwargs)
        assert "X-Timestamp" in result["headers"]
        assert "X-Sign" in result["headers"]

    def test_bearer_from_variable(self):
        self.vm.set_global_vars({"my_token": "var_token_value"})
        config = AuthConfig(type=AuthType.BEARER, token="${my_token}")
        kwargs = {"headers": {}}
        result = self.handler.apply_auth(config, kwargs)
        assert result["headers"]["Authorization"] == "Bearer var_token_value"
