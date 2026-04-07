"""通知模块 - 支持钉钉/飞书/企业微信/邮件/WebHook"""

from __future__ import annotations

import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

import httpx
from loguru import logger


class NotifyError(Exception):
    """通知发送错误"""
    pass


class NotifyResult:
    """通知结果"""
    def __init__(self, success: bool, channel: str, message: str = ""):
        self.success = success
        self.channel = channel
        self.message = message


class BaseNotifier:
    """通知基类"""

    def send(self, title: str, content: str, **kwargs) -> NotifyResult:
        raise NotImplementedError


class DingTalkNotifier(BaseNotifier):
    """钉钉机器人通知"""

    def __init__(self, webhook_url: str, secret: Optional[str] = None, at_mobiles: Optional[list[str]] = None):
        self.webhook_url = webhook_url
        self.secret = secret
        self.at_mobiles = at_mobiles or []

    def _get_signed_url(self) -> str:
        if not self.secret:
            return self.webhook_url

        import hashlib
        import hmac
        import base64
        import time
        import urllib.parse

        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"

    def send(self, title: str, content: str, **kwargs) -> NotifyResult:
        try:
            url = self._get_signed_url()
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": f"## {title}\n\n{content}",
                },
                "at": {
                    "atMobiles": self.at_mobiles,
                    "isAtAll": kwargs.get("at_all", False),
                },
            }

            with httpx.Client(timeout=10) as client:
                resp = client.post(url, json=payload)
                data = resp.json()

            if data.get("errcode") == 0:
                logger.info("钉钉通知发送成功")
                return NotifyResult(True, "dingtalk")
            else:
                msg = data.get("errmsg", "未知错误")
                logger.error(f"钉钉通知发送失败: {msg}")
                return NotifyResult(False, "dingtalk", msg)

        except Exception as e:
            logger.error(f"钉钉通知异常: {e}")
            return NotifyResult(False, "dingtalk", str(e))


class FeishuNotifier(BaseNotifier):
    """飞书机器人通知"""

    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        self.webhook_url = webhook_url
        self.secret = secret

    def send(self, title: str, content: str, **kwargs) -> NotifyResult:
        try:
            payload = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"tag": "plain_text", "content": title},
                        "template": kwargs.get("color", "blue"),
                    },
                    "elements": [
                        {"tag": "markdown", "content": content},
                    ],
                },
            }

            headers = {"Content-Type": "application/json"}

            # 签名
            if self.secret:
                import hashlib
                import hmac
                import base64
                import time

                timestamp = str(int(time.time()))
                string_to_sign = f"{timestamp}\n{self.secret}"
                hmac_code = hmac.new(
                    string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
                ).digest()
                sign = base64.b64encode(hmac_code).decode("utf-8")
                payload["timestamp"] = timestamp
                payload["sign"] = sign

            with httpx.Client(timeout=10) as client:
                resp = client.post(self.webhook_url, json=payload, headers=headers)
                data = resp.json()

            if data.get("code") == 0 or data.get("StatusCode") == 0:
                logger.info("飞书通知发送成功")
                return NotifyResult(True, "feishu")
            else:
                msg = data.get("msg", str(data))
                logger.error(f"飞书通知发送失败: {msg}")
                return NotifyResult(False, "feishu", msg)

        except Exception as e:
            logger.error(f"飞书通知异常: {e}")
            return NotifyResult(False, "feishu", str(e))


class WeChatWorkNotifier(BaseNotifier):
    """企业微信机器人通知"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, title: str, content: str, **kwargs) -> NotifyResult:
        try:
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"## {title}\n\n{content}",
                },
            }

            with httpx.Client(timeout=10) as client:
                resp = client.post(self.webhook_url, json=payload)
                data = resp.json()

            if data.get("errcode") == 0:
                logger.info("企业微信通知发送成功")
                return NotifyResult(True, "wechat_work")
            else:
                msg = data.get("errmsg", "未知错误")
                logger.error(f"企业微信通知发送失败: {msg}")
                return NotifyResult(False, "wechat_work", msg)

        except Exception as e:
            logger.error(f"企业微信通知异常: {e}")
            return NotifyResult(False, "wechat_work", str(e))


class EmailNotifier(BaseNotifier):
    """邮件通知"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 465,
        username: str = "",
        password: str = "",
        sender: str = "",
        receivers: Optional[list[str]] = None,
        cc: Optional[list[str]] = None,
        use_ssl: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender = sender or username
        self.receivers = receivers or []
        self.cc = cc or []
        self.use_ssl = use_ssl

    def send(self, title: str, content: str, **kwargs) -> NotifyResult:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = title
            msg["From"] = self.sender
            msg["To"] = ", ".join(self.receivers)
            if self.cc:
                msg["Cc"] = ", ".join(self.cc)

            # HTML 内容
            html_content = kwargs.get("html", f"<h2>{title}</h2><pre>{content}</pre>")
            msg.attach(MIMEText(content, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            all_recipients = self.receivers + self.cc

            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()

            server.login(self.username, self.password)
            server.sendmail(self.sender, all_recipients, msg.as_string())
            server.quit()

            logger.info(f"邮件通知发送成功: {', '.join(self.receivers)}")
            return NotifyResult(True, "email")

        except Exception as e:
            logger.error(f"邮件通知异常: {e}")
            return NotifyResult(False, "email", str(e))


class WebHookNotifier(BaseNotifier):
    """WebHook 通知"""

    def __init__(self, url: str, method: str = "POST", headers: Optional[dict] = None):
        self.url = url
        self.method = method.upper()
        self.headers = headers or {"Content-Type": "application/json"}

    def send(self, title: str, content: str, **kwargs) -> NotifyResult:
        try:
            payload = {
                "title": title,
                "content": content,
                "timestamp": __import__("time").time(),
                **kwargs.get("extra", {}),
            }

            with httpx.Client(timeout=10) as client:
                resp = client.request(
                    method=self.method,
                    url=self.url,
                    json=payload,
                    headers=self.headers,
                )

            if 200 <= resp.status_code < 300:
                logger.info(f"WebHook 通知发送成功: {self.url}")
                return NotifyResult(True, "webhook")
            else:
                logger.error(f"WebHook 通知失败: HTTP {resp.status_code}")
                return NotifyResult(False, "webhook", f"HTTP {resp.status_code}")

        except Exception as e:
            logger.error(f"WebHook 通知异常: {e}")
            return NotifyResult(False, "webhook", str(e))


class NotifyManager:
    """通知管理器"""

    def __init__(self):
        self.notifiers: list[BaseNotifier] = []
        self.conditions: dict[str, Any] = {}

    def add_notifier(self, notifier: BaseNotifier):
        """添加通知渠道"""
        self.notifiers.append(notifier)

    def set_conditions(
        self,
        on_complete: bool = True,
        on_failure: bool = True,
        min_failures: int = 0,
        max_pass_rate: float = 100.0,
    ):
        """设置通知触发条件"""
        self.conditions = {
            "on_complete": on_complete,
            "on_failure": on_failure,
            "min_failures": min_failures,
            "max_pass_rate": max_pass_rate,
        }

    def should_notify(self, total: int, passed: int, failed: int) -> bool:
        """判断是否需要发送通知"""
        if not self.conditions:
            return True

        if self.conditions.get("on_complete"):
            return True

        if self.conditions.get("on_failure") and failed > 0:
            return True

        min_failures = self.conditions.get("min_failures", 0)
        if min_failures > 0 and failed >= min_failures:
            return True

        max_pass_rate = self.conditions.get("max_pass_rate", 100.0)
        pass_rate = (passed / total * 100) if total > 0 else 100
        if pass_rate < max_pass_rate:
            return True

        return False

    def format_report(self, total: int, passed: int, failed: int, total_time: float) -> tuple[str, str]:
        """格式化通知报告内容"""
        pass_rate = round(passed / total * 100, 1) if total > 0 else 0
        status = "✅ 全部通过" if failed == 0 else "❌ 存在失败"

        title = f"SmartAPI-Test 测试报告 {status}"
        content = (
            f"**执行结果**: {status}\n\n"
            f"- 总用例: **{total}**\n"
            f"- 通过: **{passed}** ✅\n"
            f"- 失败: **{failed}** ❌\n"
            f"- 通过率: **{pass_rate}%**\n"
            f"- 总耗时: **{round(total_time, 2)}s**\n"
        )

        return title, content

    def notify(self, total: int, passed: int, failed: int, total_time: float) -> list[NotifyResult]:
        """发送通知"""
        if not self.should_notify(total, passed, failed):
            logger.info("未达到通知触发条件，跳过发送")
            return []

        title, content = self.format_report(total, passed, failed, total_time)
        results = []

        for notifier in self.notifiers:
            result = notifier.send(title, content)
            results.append(result)

        return results
