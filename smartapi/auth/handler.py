"""鉴权处理器 - 支持多种鉴权方式的自动处理"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Optional

import httpx
from loguru import logger

from smartapi.core.models import AuthConfig, AuthType
from smartapi.core.variables import VariableManager


class AuthError(Exception):
    """鉴权错误"""
    pass


class TokenCache:
    """Token 缓存管理"""

    def __init__(self):
        self._tokens: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> Optional[str]:
        """获取缓存的 Token"""
        entry = self._tokens.get(key)
        if entry is None:
            return None
        if entry.get("expire_at") and time.time() > entry["expire_at"]:
            logger.debug(f"Token 已过期: {key}")
            del self._tokens[key]
            return None
        return entry["token"]

    def set(self, key: str, token: str, expire_seconds: Optional[int] = None):
        """缓存 Token"""
        entry = {"token": token}
        if expire_seconds:
            entry["expire_at"] = time.time() + expire_seconds
        self._tokens[key] = entry
        logger.debug(f"Token 已缓存: {key}")

    def clear(self, key: Optional[str] = None):
        """清除缓存"""
        if key:
            self._tokens.pop(key, None)
        else:
            self._tokens.clear()


class AuthHandler:
    """统一鉴权处理器"""

    def __init__(self, variable_manager: Optional[VariableManager] = None):
        self.variables = variable_manager or VariableManager()
        self.token_cache = TokenCache()
        self._http_client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.Client(timeout=30, follow_redirects=True)
        return self._http_client

    def close(self):
        if self._http_client and not self._http_client.is_closed:
            self._http_client.close()

    def apply_auth(self, auth_config: AuthConfig, request_kwargs: dict[str, Any]) -> dict[str, Any]:
        """将鉴权信息应用到请求参数"""
        if not auth_config or auth_config.type == AuthType.NONE:
            return request_kwargs

        handler = self._get_handler(auth_config.type)
        return handler(auth_config, request_kwargs)

    def _get_handler(self, auth_type: AuthType) -> callable:
        """获取鉴权类型对应的处理函数"""
        handlers = {
            AuthType.BASIC: self._apply_basic,
            AuthType.BEARER: self._apply_bearer,
            AuthType.TOKEN: self._apply_token,
            AuthType.API_KEY: self._apply_api_key,
            AuthType.JWT: self._apply_jwt,
            AuthType.OAUTH2: self._apply_oauth2,
            AuthType.CUSTOM: self._apply_custom,
        }
        handler = handlers.get(auth_type)
        if not handler:
            raise AuthError(f"不支持的鉴权类型: {auth_type}")
        return handler

    def _apply_basic(self, config: AuthConfig, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Basic Auth"""
        username = self.variables.resolve_string(config.username or "")
        password = self.variables.resolve_string(config.password or "")
        kwargs["auth"] = (username, password)
        logger.debug(f"已应用 Basic Auth: {username}")
        return kwargs

    def _apply_bearer(self, config: AuthConfig, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Bearer Token"""
        token = self._get_or_fetch_token(config)
        prefix = config.token_prefix or "Bearer"
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"]["Authorization"] = f"{prefix} {token}"
        logger.debug("已应用 Bearer Token")
        return kwargs

    def _apply_token(self, config: AuthConfig, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Token 鉴权（同 Bearer，但支持自动获取）"""
        return self._apply_bearer(config, kwargs)

    def _apply_api_key(self, config: AuthConfig, kwargs: dict[str, Any]) -> dict[str, Any]:
        """API Key"""
        key_name = self.variables.resolve_string(config.api_key_name or "")
        key_value = self.variables.resolve_string(config.api_key_value or "")

        if config.api_key_in == "header":
            if "headers" not in kwargs:
                kwargs["headers"] = {}
            kwargs["headers"][key_name] = key_value
        elif config.api_key_in == "query":
            if "params" not in kwargs or kwargs["params"] is None:
                kwargs["params"] = {}
            kwargs["params"][key_name] = key_value
        elif config.api_key_in == "cookie":
            if "cookies" not in kwargs or kwargs["cookies"] is None:
                kwargs["cookies"] = {}
            kwargs["cookies"][key_name] = key_value

        logger.debug(f"已应用 API Key: {key_name} (in {config.api_key_in})")
        return kwargs

    def _apply_jwt(self, config: AuthConfig, kwargs: dict[str, Any]) -> dict[str, Any]:
        """JWT 鉴权"""
        token = self._get_or_fetch_token(config)
        prefix = config.token_prefix or "Bearer"
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"]["Authorization"] = f"{prefix} {token}"
        logger.debug("已应用 JWT")
        return kwargs

    def _apply_oauth2(self, config: AuthConfig, kwargs: dict[str, Any]) -> dict[str, Any]:
        """OAuth2 鉴权"""
        token = self._get_or_fetch_token(config)
        prefix = config.token_prefix or "Bearer"
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"]["Authorization"] = f"{prefix} {token}"
        logger.debug("已应用 OAuth2")
        return kwargs

    def _apply_custom(self, config: AuthConfig, kwargs: dict[str, Any]) -> dict[str, Any]:
        """自定义鉴权脚本"""
        if not config.custom_script:
            raise AuthError("自定义鉴权缺少 custom_script")

        local_vars = {
            "kwargs": kwargs,
            "config": config,
            "variables": self.variables,
            "hashlib": hashlib,
            "hmac": hmac,
            "time": time,
        }
        try:
            exec(config.custom_script, {"__builtins__": __builtins__}, local_vars)
            kwargs = local_vars.get("kwargs", kwargs)
            logger.debug("已应用自定义鉴权")
        except Exception as e:
            raise AuthError(f"自定义鉴权脚本执行失败: {e}") from e

        return kwargs

    def _get_or_fetch_token(self, config: AuthConfig) -> str:
        """获取 Token（优先缓存，否则自动获取）"""
        # 如果直接配置了 Token
        if config.token:
            token = self.variables.resolve_string(config.token)
            if token:
                return token

        # 从变量中获取
        token_from_var = self.variables.get("_auth_token")
        if token_from_var:
            return str(token_from_var)

        # 从缓存获取
        cache_key = config.token_url or "default"
        cached = self.token_cache.get(cache_key)
        if cached:
            return cached

        # 自动获取 Token
        if config.token_url:
            return self._fetch_token(config)

        raise AuthError("无法获取 Token：未配置 token 或 token_url")

    def _fetch_token(self, config: AuthConfig) -> str:
        """从 Token URL 获取 Token"""
        token_url = self.variables.resolve_string(config.token_url)
        logger.info(f"自动获取 Token: {token_url}")

        try:
            # 构建请求
            req_kwargs: dict[str, Any] = {"method": "POST", "url": token_url}

            # 如果有用户名密码，作为请求体
            if config.username and config.password:
                req_kwargs["json"] = {
                    "username": self.variables.resolve_string(config.username),
                    "password": self.variables.resolve_string(config.password),
                }

            # 额外参数
            if config.extra:
                body = req_kwargs.get("json", {})
                body.update(self.variables.resolve_value(config.extra))
                req_kwargs["json"] = body

            response = self.client.request(**req_kwargs)
            response.raise_for_status()

            # 从响应中提取 Token
            data = response.json()
            token_field = config.token_field or "token"

            # 支持嵌套字段: "data.token" -> data["data"]["token"]
            token = data
            for key in token_field.split("."):
                if isinstance(token, dict):
                    token = token.get(key)
                else:
                    token = None
                    break

            if not token:
                raise AuthError(f"从响应中提取 Token 失败，字段: {token_field}，响应: {data}")

            token = str(token)

            # 缓存 Token
            cache_key = config.token_url or "default"
            self.token_cache.set(cache_key, token, config.expire_seconds)

            # 存入变量
            self.variables.set_extract_var("_auth_token", token)

            logger.info("Token 获取成功")
            return token

        except httpx.HTTPError as e:
            raise AuthError(f"Token 获取请求失败: {e}") from e

    def refresh_token(self, config: AuthConfig) -> str:
        """刷新 Token"""
        if config.refresh_url:
            old_token = self._get_or_fetch_token(config)
            refresh_url = self.variables.resolve_string(config.refresh_url)

            try:
                response = self.client.post(
                    refresh_url,
                    headers={"Authorization": f"{config.token_prefix} {old_token}"},
                )
                response.raise_for_status()
                data = response.json()

                token_field = config.token_field or "token"
                token = data
                for key in token_field.split("."):
                    if isinstance(token, dict):
                        token = token.get(key)

                if token:
                    cache_key = config.token_url or "default"
                    self.token_cache.set(cache_key, str(token), config.expire_seconds)
                    self.variables.set_extract_var("_auth_token", str(token))
                    return str(token)

            except Exception as e:
                logger.warning(f"Token 刷新失败: {e}")

        # 刷新失败，重新获取
        self.token_cache.clear()
        return self._fetch_token(config)
