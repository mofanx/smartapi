"""安全模块 - 敏感信息加密存储"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger


class SecretManager:
    """敏感信息加密管理器

    支持对密码、Token、API Key 等敏感信息进行加密存储和解密读取。
    加密密钥通过环境变量 SMARTAPI_SECRET_KEY 或密钥文件获取。
    """

    ENV_KEY_NAME = "SMARTAPI_SECRET_KEY"
    KEY_FILE_NAME = ".smartapi_key"

    def __init__(self, key: Optional[str] = None, key_file: Optional[str] = None):
        self._fernet: Optional[Fernet] = None
        self._init_key(key, key_file)

    def _init_key(self, key: Optional[str], key_file: Optional[str]):
        """初始化加密密钥"""
        raw_key = key

        if not raw_key:
            raw_key = os.environ.get(self.ENV_KEY_NAME)

        if not raw_key and key_file:
            kf = Path(key_file)
            if kf.exists():
                raw_key = kf.read_text(encoding="utf-8").strip()

        if not raw_key:
            kf = Path.home() / self.KEY_FILE_NAME
            if kf.exists():
                raw_key = kf.read_text(encoding="utf-8").strip()

        if raw_key:
            derived_key = self._derive_key(raw_key)
            self._fernet = Fernet(derived_key)
            logger.debug("加密密钥已初始化")
        else:
            logger.debug("未配置加密密钥，敏感信息将以明文存储")

    @staticmethod
    def _derive_key(password: str, salt: bytes = b"smartapi-test-salt") -> bytes:
        """从密码派生 Fernet 密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    @staticmethod
    def generate_key() -> str:
        """生成随机密钥"""
        return Fernet.generate_key().decode()

    def encrypt(self, plaintext: str) -> str:
        """加密字符串，返回 ENC(...) 格式"""
        if not self._fernet:
            logger.warning("未配置加密密钥，返回原文")
            return plaintext
        encrypted = self._fernet.encrypt(plaintext.encode())
        return f"ENC({encrypted.decode()})"

    def decrypt(self, ciphertext: str) -> str:
        """解密 ENC(...) 格式的字符串"""
        if not ciphertext.startswith("ENC(") or not ciphertext.endswith(")"):
            return ciphertext  # 非加密格式，原样返回

        if not self._fernet:
            logger.warning("未配置加密密钥，无法解密")
            return ciphertext

        try:
            encrypted = ciphertext[4:-1]
            decrypted = self._fernet.decrypt(encrypted.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"解密失败: {e}")
            return ciphertext

    def is_encrypted(self, value: str) -> bool:
        """判断值是否已加密"""
        return isinstance(value, str) and value.startswith("ENC(") and value.endswith(")")

    def process_dict(self, data: dict[str, Any], mode: str = "decrypt") -> dict[str, Any]:
        """递归处理字典中的加密/解密值

        Args:
            data: 数据字典
            mode: 'encrypt' 对指定字段加密, 'decrypt' 解密 ENC() 格式的值
        """
        result = {}
        for k, v in data.items():
            if isinstance(v, str):
                if mode == "decrypt" and self.is_encrypted(v):
                    result[k] = self.decrypt(v)
                elif mode == "encrypt" and k in self.SENSITIVE_FIELDS:
                    result[k] = self.encrypt(v) if not self.is_encrypted(v) else v
                else:
                    result[k] = v
            elif isinstance(v, dict):
                result[k] = self.process_dict(v, mode)
            elif isinstance(v, list):
                result[k] = [
                    self.process_dict(item, mode) if isinstance(item, dict)
                    else (self.decrypt(item) if mode == "decrypt" and isinstance(item, str) and self.is_encrypted(item) else item)
                    for item in v
                ]
            else:
                result[k] = v
        return result

    # 默认视为敏感的字段名
    SENSITIVE_FIELDS = {
        "password", "token", "secret", "api_key", "api_key_value",
        "access_token", "refresh_token", "private_key", "client_secret",
    }

    def encrypt_file(self, file_path: str | Path) -> None:
        """加密文件中的敏感字段"""
        import yaml
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        if isinstance(data, dict):
            encrypted = self.process_dict(data, mode="encrypt")
            path.write_text(yaml.dump(encrypted, allow_unicode=True, default_flow_style=False), encoding="utf-8")
            logger.info(f"文件已加密: {path}")

    def decrypt_file_data(self, file_path: str | Path) -> dict:
        """读取文件并解密敏感字段"""
        import yaml
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        if isinstance(data, dict):
            return self.process_dict(data, mode="decrypt")
        return data


# 全局实例
secret_manager = SecretManager()
