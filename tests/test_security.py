"""安全加密模块单元测试"""

import pytest

from smartapi.core.security import SecretManager


class TestSecretManager:
    """加密管理器测试"""

    def setup_method(self):
        self.sm = SecretManager(key="test_secret_key_123")

    def test_encrypt_decrypt(self):
        plaintext = "my_secret_password"
        encrypted = self.sm.encrypt(plaintext)
        assert encrypted.startswith("ENC(")
        assert encrypted.endswith(")")
        assert encrypted != plaintext

        decrypted = self.sm.decrypt(encrypted)
        assert decrypted == plaintext

    def test_decrypt_non_encrypted(self):
        """非加密格式直接返回原文"""
        assert self.sm.decrypt("plain_text") == "plain_text"

    def test_is_encrypted(self):
        assert self.sm.is_encrypted("ENC(abc123)") is True
        assert self.sm.is_encrypted("plain_text") is False
        assert self.sm.is_encrypted("ENC(") is False
        assert self.sm.is_encrypted("") is False

    def test_generate_key(self):
        key = SecretManager.generate_key()
        assert isinstance(key, str)
        assert len(key) > 20

    def test_process_dict_decrypt(self):
        encrypted_pw = self.sm.encrypt("secret123")
        data = {
            "username": "admin",
            "password": encrypted_pw,
            "nested": {
                "token": self.sm.encrypt("token_abc"),
            },
            "plain_field": "not_encrypted",
        }
        result = self.sm.process_dict(data, mode="decrypt")
        assert result["username"] == "admin"
        assert result["password"] == "secret123"
        assert result["nested"]["token"] == "token_abc"
        assert result["plain_field"] == "not_encrypted"

    def test_process_dict_encrypt(self):
        data = {
            "username": "admin",
            "password": "secret123",
            "token": "my_token",
            "normal_field": "hello",
        }
        result = self.sm.process_dict(data, mode="encrypt")
        assert result["username"] == "admin"  # 非敏感字段不加密
        assert result["password"].startswith("ENC(")
        assert result["token"].startswith("ENC(")
        assert result["normal_field"] == "hello"

    def test_no_key_returns_plaintext(self):
        sm_no_key = SecretManager()
        assert sm_no_key.encrypt("test") == "test"
        assert sm_no_key.decrypt("ENC(xyz)") == "ENC(xyz)"

    def test_different_keys_incompatible(self):
        sm2 = SecretManager(key="different_key")
        encrypted = self.sm.encrypt("hello")
        # 用不同密钥解密应该失败，返回原密文
        result = sm2.decrypt(encrypted)
        assert result == encrypted  # 解密失败返回原文

    def test_encrypt_already_encrypted(self):
        """已加密的不重复加密"""
        encrypted = self.sm.encrypt("test")
        data = {"password": encrypted}
        result = self.sm.process_dict(data, mode="encrypt")
        assert result["password"] == encrypted  # 不重复加密

    def test_process_list_in_dict(self):
        data = {
            "items": [
                {"password": self.sm.encrypt("pw1")},
                {"password": self.sm.encrypt("pw2")},
            ]
        }
        result = self.sm.process_dict(data, mode="decrypt")
        assert result["items"][0]["password"] == "pw1"
        assert result["items"][1]["password"] == "pw2"
