from app.utils.logger import log_success


"""
Webhook Notification Channel

Webhook通知渠道实现，支持多种消息格式和认证方式。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import time

import requests

from app.notifications_v2.channels.notification_channel_interface import INotificationChannel
from app.notifications_v2.notification_level import NotificationLevel
from app.utils import log_debug, log_error, log_info, log_warn


class MessageFormat(Enum):
    """消息格式"""

    PLAIN = "plain"
    JSON = "json"
    SLACK = "slack"
    DINGTALK = "dingtalk"
    FEISHU = "feishu"
    WECHAT_WORK = "wechat_work"


class AuthType(Enum):
    """认证类型"""

    NONE = "none"
    BEARER = "bearer"
    BASIC = "basic"
    API_KEY = "api_key"
    CUSTOM = "custom"


@dataclass
class WebhookConfig:
    """Webhook配置"""

    url: str
    method: str = "POST"
    message_format: MessageFormat = MessageFormat.JSON
    auth_type: AuthType = AuthType.NONE
    auth_token: Optional[str] = None
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    api_key_header: Optional[str] = None
    api_key_value: Optional[str] = None
    custom_headers: Optional[Dict[str, str]] = None
    timeout: float = 30.0
    retry_count: int = 3
    retry_delay: float = 1.0
    enabled: bool = True

    # 消息模板配置
    title_template: Optional[str] = None
    content_template: Optional[str] = None

    # 频率限制
    rate_limit_requests: int = 60
    rate_limit_window: int = 60  # 秒


class WebhookChannel(INotificationChannel):
    """
    Webhook通知渠道

    支持多种消息格式和认证方式的Webhook通知。
    """

    def __init__(self, **config: Any):
        self.config = WebhookConfig(**config)
        self.channel_name = "webhook"
        self._request_times: List[float] = []

    def send(
        self,
        message: str,
        title: str = "Notification",
        level: NotificationLevel = NotificationLevel.INFO,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if not self.config.enabled:
            return False

        if not self._check_rate_limit():
            log_warn("Webhook sending frequency exceeded limit", "WEBHOOK_CHANNEL")
            return False

        try:
            prepared_message = self._prepare_message(title, message, level, data)
            headers = self._prepare_headers()

            success = self._send_with_retry(prepared_message, headers)

            if success:
                self._record_request()
                log_success("Webhook notification sent successfully", "WEBHOOK_CHANNEL")
            else:
                log_warn("Webhook notification failed to send", "WEBHOOK_CHANNEL")

            return success

        except Exception as e:
            log_error(f"Webhook notification sending exception: {e}", "WEBHOOK_CHANNEL")
            return False

    def _prepare_message(
        self,
        title: str,
        content: str,
        level: NotificationLevel,
        data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """准备消息内容"""
        # 应用模板
        if self.config.title_template:
            title = self.config.title_template.format(
                title=title,
                level=level.value,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )

        if self.config.content_template:
            content = self.config.content_template.format(
                content=content,
                level=level.value,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )

        # 根据消息格式准备内容
        if self.config.message_format == MessageFormat.PLAIN:
            return f"{title}\n{content}"

        elif self.config.message_format == MessageFormat.JSON:
            return {
                "title": title,
                "content": content,
                "level": level.value,
                "timestamp": time.time(),
                "data": data or {},
            }

        elif self.config.message_format == MessageFormat.SLACK:
            return self._prepare_slack_message(title, content, level, data)

        elif self.config.message_format == MessageFormat.DINGTALK:
            return self._prepare_dingtalk_message(title, content, level, data)

        elif self.config.message_format == MessageFormat.FEISHU:
            return self._prepare_feishu_message(title, content, level, data)

        elif self.config.message_format == MessageFormat.WECHAT_WORK:
            return self._prepare_wechat_work_message(title, content, level, data)

        else:
            # 默认JSON格式
            return {
                "title": title,
                "content": content,
                "level": level.value,
                "timestamp": time.time(),
            }

    def _prepare_slack_message(
        self,
        title: str,
        content: str,
        level: NotificationLevel,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """准备Slack消息格式"""
        color_map = {
            NotificationLevel.DEBUG: "#36a64f",
            NotificationLevel.INFO: "#36a64f",
            NotificationLevel.SUCCESS: "#36a64f",
            NotificationLevel.WARNING: "#ff9500",
            NotificationLevel.ERROR: "#ff0000",
            NotificationLevel.CRITICAL: "#ff0000",
        }

        return {
            "attachments": [
                {
                    "color": color_map.get(level, "#36a64f"),
                    "title": title,
                    "text": content,
                    "fields": [
                        {"title": "级别", "value": level.value, "short": True},
                        {
                            "title": "时间",
                            "value": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "short": True,
                        },
                    ],
                    "footer": "BTC Trading Bot",
                    "ts": int(time.time()),
                }
            ]
        }

    def _prepare_dingtalk_message(
        self,
        title: str,
        content: str,
        level: NotificationLevel,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """准备钉钉消息格式"""
        emoji_map = {
            NotificationLevel.DEBUG: "🔍",
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.SUCCESS: "✅",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.CRITICAL: "🚨",
        }

        emoji = emoji_map.get(level, "ℹ️")
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        markdown_text = f"""
{emoji} **{title}**

**内容:** {content}

**级别:** {level.value}
**时间:** {timestamp}

**power by:** jm_alarm
"""

        return {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": markdown_text},
        }

    def _prepare_feishu_message(
        self,
        title: str,
        content: str,
        level: NotificationLevel,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """准备飞书消息格式"""
        color_map = {
            NotificationLevel.DEBUG: "blue",
            NotificationLevel.INFO: "blue",
            NotificationLevel.SUCCESS: "green",
            NotificationLevel.WARNING: "orange",
            NotificationLevel.ERROR: "red",
            NotificationLevel.CRITICAL: "red",
        }

        return {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": color_map.get(level, "blue"),
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "plain_text", "content": content}},
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "plain_text",
                                    "content": f"级别: {level.value}",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "plain_text",
                                    "content": f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                                },
                            },
                        ],
                    },
                ],
            },
        }

    def _prepare_wechat_work_message(
        self,
        title: str,
        content: str,
        level: NotificationLevel,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """准备企业微信消息格式"""
        return {
            "msgtype": "markdown",
            "markdown": {
                "content": f"""
**{title}**

{content}

> 级别: {level.value}
> 时间: {time.strftime("%Y-%m-%d %H:%M:%S")}
"""
            },
        }

    def _prepare_headers(self) -> Dict[str, str]:
        """准备请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "BTC-Trading-Bot/1.0",
        }

        # 添加认证头
        if self.config.auth_type == AuthType.BEARER and self.config.auth_token:
            headers["Authorization"] = f"Bearer {self.config.auth_token}"

        elif self.config.auth_type == AuthType.API_KEY and self.config.api_key_header and self.config.api_key_value:
            headers[self.config.api_key_header] = self.config.api_key_value

        # 添加自定义头
        if self.config.custom_headers:
            headers.update(self.config.custom_headers)

        return headers

    def _send_with_retry(self, message: Any, headers: Dict[str, str]) -> bool:
        """带重试的发送"""
        for attempt in range(self.config.retry_count + 1):
            try:
                auth = None
                if self.config.auth_type == AuthType.BASIC:
                    auth = (
                        self.config.auth_username or "",
                        self.config.auth_password or "",
                    )

                if isinstance(message, str):
                    data = message
                    headers["Content-Type"] = "text/plain"
                else:
                    data = json.dumps(message, ensure_ascii=False).encode("utf-8")

                response = requests.request(
                    method=self.config.method,
                    url=self.config.url,
                    data=data,
                    headers=headers,
                    auth=auth,
                    timeout=self.config.timeout,
                )

                if response.status_code < 400:
                    return True
                else:
                    log_warn(
                        f"Webhook response error: {response.status_code}",
                        "WEBHOOK_CHANNEL",
                    )
                    if attempt < self.config.retry_count:
                        time.sleep(self.config.retry_delay * (attempt + 1))
                    continue

            except requests.exceptions.RequestException as e:
                log_error(
                    f"Webhook sending exception (attempt {attempt + 1}): {e}",
                    "WEBHOOK_CHANNEL",
                )
                if attempt < self.config.retry_count:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                continue

        return False

    def _check_rate_limit(self) -> bool:
        """检查频率限制"""
        current_time = time.time()
        window_start = current_time - self.config.rate_limit_window

        # 清理过期的请求记录
        self._request_times = [t for t in self._request_times if t > window_start]

        # 检查是否超过限制
        return len(self._request_times) < self.config.rate_limit_requests

    def _record_request(self) -> None:
        """记录请求时间"""
        self._request_times.append(time.time())

    def is_enabled(self) -> bool:
        """检查渠道是否启用"""
        return self.config.enabled

    def get_channel_name(self) -> str:
        """获取渠道名称"""
        return self.channel_name

    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        # 更新配置对象
        for key, value in config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        log_info("Webhook渠道配置已更新", "WEBHOOK_CHANNEL")

    def test_connection(self) -> bool:
        """测试连接"""

        if not self.config.url:
            log_error("Webhook URL未配置", "WEBHOOK_CHANNEL")
            return False

        return True
