"""
Notification Configuration

通知系统配置管理，包括各种渠道的配置和依赖注入设置。
"""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import os

import yaml

from app.notifications_v2.notification_level import NotificationLevel
from app.utils import log_error, log_info, log_warn

from ..channels.desktop_channel import DesktopConfig
from ..channels.email_channel import EmailConfig, EmailProviderConfig
from ..channels.webhook_channel import WebhookConfig


@dataclass
class NotificationConfig:
    """通知系统配置"""

    # 通用设置
    enabled: bool = True
    min_level: NotificationLevel = NotificationLevel.INFO
    max_queue_size: int = 1000
    queue_timeout: float = 30.0

    # 渠道配置
    webhook: Optional[WebhookConfig] = None
    desktop: Optional[DesktopConfig] = None
    email: Optional[EmailConfig] = None

    # 高级设置
    enable_statistics: bool = True
    enable_health_check: bool = True
    health_check_interval: float = 300.0  # 5分钟

    # 事件设置
    enable_events: bool = True
    max_event_callbacks: int = 10

    # 自动重试设置
    auto_retry: bool = True
    max_retry_attempts: int = 3
    retry_delay: float = 5.0

    def __post_init__(self):
        """初始化后处理"""
        # 确保至少有一个渠道启用
        if not any(
            [
                self.webhook and self.webhook.enabled,
                self.desktop and self.desktop.enabled,
                self.email and self.email.enabled,
            ]
        ):
            log_warn("没有启用的通知渠道", "NOTIFICATION_CONFIG")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        from enum import Enum

        def convert_value(value):
            """递归转换值，处理枚举类型"""
            if isinstance(value, Enum):
                return value.value
            elif isinstance(value, dict):
                return {k: convert_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [convert_value(item) for item in value]
            elif hasattr(value, "__dict__"):
                # 处理dataclass对象
                if hasattr(value, "__dataclass_fields__"):
                    return {k: convert_value(v) for k, v in asdict(value).items()}
                else:
                    return {k: convert_value(v) for k, v in value.__dict__.items()}
            else:
                return value

        result = {}
        for key, value in asdict(self).items():
            result[key] = convert_value(value)

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationConfig":
        """从字典创建配置"""
        from ..channels.desktop_channel import DesktopConfig
        from ..channels.email_channel import EmailConfig
        from ..channels.webhook_channel import AuthType, MessageFormat

        # 处理主配置的枚举类型
        if "min_level" in data and isinstance(data["min_level"], str):
            data["min_level"] = NotificationLevel(data["min_level"].lower())

        # 处理渠道配置
        if "webhook" in data and data["webhook"]:
            raw = data["webhook"].copy()
            # 允许字段白名单（避免未知字段导致初始化失败）
            allowed_keys = {
                "url",
                "method",
                "message_format",
                "auth_type",
                "auth_token",
                "auth_username",
                "auth_password",
                "api_key_header",
                "api_key_value",
                "custom_headers",
                "timeout",
                "retry_count",
                "retry_delay",
                "enabled",
                "title_template",
                "content_template",
                "rate_limit_requests",
                "rate_limit_window",
            }
            webhook_data = {k: v for k, v in raw.items() if k in allowed_keys}
            # 枚举转换
            if "message_format" in webhook_data and isinstance(webhook_data["message_format"], str):
                webhook_data["message_format"] = MessageFormat(webhook_data["message_format"].lower())
            if "auth_type" in webhook_data and isinstance(webhook_data["auth_type"], str):
                webhook_data["auth_type"] = AuthType(webhook_data["auth_type"].lower())
            # 数值修正
            for key in ("retry_count", "rate_limit_requests", "rate_limit_window"):
                if key in webhook_data:
                    try:
                        webhook_data[key] = int(webhook_data[key])
                    except (TypeError, ValueError):
                        pass
            for key in ("timeout", "retry_delay"):
                if key in webhook_data:
                    try:
                        webhook_data[key] = float(webhook_data[key])
                    except (TypeError, ValueError):
                        pass
            data["webhook"] = WebhookConfig(**webhook_data)

        if "desktop" in data and data["desktop"]:
            raw = data["desktop"].copy()
            allowed_keys = {
                "enabled",
                "use_system_notification",
                "notification_timeout",
                "app_name",
                "app_icon",
                "enable_sound",
                "sound_file",
                "min_level",
                "rate_limit_requests",
                "rate_limit_window",
            }
            desktop_data = {k: v for k, v in raw.items() if k in allowed_keys}
            # 枚举转换
            if "min_level" in desktop_data and isinstance(desktop_data["min_level"], str):
                desktop_data["min_level"] = NotificationLevel(desktop_data["min_level"].lower())
            # 类型修正
            if "notification_timeout" in desktop_data:
                try:
                    desktop_data["notification_timeout"] = int(desktop_data["notification_timeout"])
                except (TypeError, ValueError):
                    pass
            for key in ("rate_limit_requests", "rate_limit_window"):
                if key in desktop_data:
                    try:
                        desktop_data[key] = int(desktop_data[key])
                    except (TypeError, ValueError):
                        pass
            data["desktop"] = DesktopConfig(**desktop_data)

        if "email" in data and data["email"]:
            raw = data["email"].copy()
            # 仅允许严格的字段集合
            allowed_keys = {"enabled", "rate_limit_requests", "rate_limit_window", "providers"}
            email_data = {k: v for k, v in raw.items() if k in allowed_keys}

            # 数值修正
            for key in ("rate_limit_requests", "rate_limit_window"):
                if key in email_data:
                    try:
                        email_data[key] = int(email_data[key])
                    except (TypeError, ValueError):
                        pass

            # 解析 providers 列表
            providers_cfg = raw.get("providers")
            if isinstance(providers_cfg, list) and providers_cfg:
                parsed_providers: List[EmailProviderConfig] = []
                for prov in providers_cfg:
                    if not isinstance(prov, dict):
                        continue
                    prov_raw = prov.copy()
                    prov_allowed_keys = {
                        "smtp_server",
                        "smtp_port",
                        "use_tls",
                        "username",
                        "password",
                        "from_address",
                        "to_addresses",
                        "subject_prefix",
                    }
                    prov_data = {k: v for k, v in prov_raw.items() if k in prov_allowed_keys}
                    # 类型修正
                    if "smtp_port" in prov_data:
                        try:
                            prov_data["smtp_port"] = int(prov_data["smtp_port"])
                        except (TypeError, ValueError):
                            pass
                    # 列表修正
                    if "to_addresses" in prov_data and isinstance(prov_data["to_addresses"], str):
                        prov_data["to_addresses"] = [addr.strip() for addr in prov_data["to_addresses"].split(",") if addr.strip()]
                    try:
                        parsed_providers.append(EmailProviderConfig(**prov_data))
                    except (TypeError, ValueError):
                        # 忽略非法 provider
                        pass
                if parsed_providers:
                    email_data["providers"] = parsed_providers

            data["email"] = EmailConfig(**email_data)

        return cls(**data)

    def to_yaml(self) -> str:
        """转换为YAML字符串"""
        return yaml.dump(self.to_dict(), default_flow_style=False, allow_unicode=True)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "NotificationConfig":
        """从YAML字符串创建配置"""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "NotificationConfig":
        """从文件加载配置"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.suffix.lower() in [".yml", ".yaml"]:
                data = yaml.safe_load(f)
            else:
                raise ValueError(f"不支持的配置文件格式: {file_path.suffix}")

        return cls.from_dict(data)

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """保存配置到文件"""
        file_path = Path(file_path)

        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            if file_path.suffix.lower() in [".yml", ".yaml"]:
                yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True)
            else:
                raise ValueError(f"不支持的配置文件格式: {file_path.suffix}")

    def validate(self) -> bool:
        """验证配置"""
        try:
            # 验证基本设置
            if self.max_queue_size <= 0:
                log_error("队列大小必须大于0", "NOTIFICATION_CONFIG")
                return False

            if self.queue_timeout <= 0:
                log_error("队列超时时间必须大于0", "NOTIFICATION_CONFIG")
                return False

            if self.health_check_interval <= 0:
                log_error("健康检查间隔必须大于0", "NOTIFICATION_CONFIG")
                return False

            # 验证渠道配置
            enabled_channels = []

            if self.webhook and self.webhook.enabled:
                if not self.webhook.url:
                    log_error("Webhook URL未配置", "NOTIFICATION_CONFIG")
                    return False
                enabled_channels.append("webhook")

            if self.desktop and self.desktop.enabled:
                enabled_channels.append("desktop")

            if self.email and self.email.enabled:
                # 基本配置检查（多提供者）
                if not self.email.providers or len(self.email.providers) == 0:
                    log_error("Email 未配置任何提供者", "NOTIFICATION_CONFIG")
                    return False
                # 校验每个提供者的关键字段
                for p in self.email.providers:
                    if not p.smtp_server:
                        log_error("Email Provider SMTP 服务器未配置", "NOTIFICATION_CONFIG")
                        return False
                    if not (p.from_address or p.username):
                        log_error("Email Provider 发件人未配置", "NOTIFICATION_CONFIG")
                        return False
                    if not p.to_addresses or len(p.to_addresses) == 0:
                        log_error("Email Provider 收件人未配置", "NOTIFICATION_CONFIG")
                        return False
                enabled_channels.append("email")

            if not enabled_channels:
                log_warn("没有启用的通知渠道", "NOTIFICATION_CONFIG")
            else:
                log_info(
                    f"已启用的通知渠道: {', '.join(enabled_channels)}",
                    "NOTIFICATION_CONFIG",
                )

            return True

        except Exception as e:
            log_error(f"配置验证失败: {e}", "NOTIFICATION_CONFIG")
            return False

    def get_enabled_channels(self) -> List[str]:
        """获取启用的渠道列表"""
        enabled = []

        if self.webhook and self.webhook.enabled:
            enabled.append("webhook")
        if self.desktop and self.desktop.enabled:
            enabled.append("desktop")
        if self.email and self.email.enabled:
            enabled.append("email")

        return enabled


# 默认配置
DEFAULT_NOTIFICATION_CONFIG = NotificationConfig(
    enabled=True,
    min_level=NotificationLevel.INFO,
    max_queue_size=1000,
    queue_timeout=30.0,
    desktop=DesktopConfig(enabled=True, min_level=NotificationLevel.WARNING),
    webhook=WebhookConfig(enabled=False, url="", method="POST"),
    email=EmailConfig(enabled=False),
    enable_statistics=True,
    enable_health_check=True,
    health_check_interval=300.0,
    enable_events=True,
    auto_retry=True,
)


def load_config_from_env() -> NotificationConfig:
    """从环境变量加载配置"""
    config = DEFAULT_NOTIFICATION_CONFIG

    # 通用设置
    if os.getenv("NOTIFICATION_ENABLED"):
        config.enabled = os.getenv("NOTIFICATION_ENABLED", "true").lower() == "true"

    if os.getenv("NOTIFICATION_MIN_LEVEL"):
        try:
            config.min_level = NotificationLevel(os.getenv("NOTIFICATION_MIN_LEVEL"))
        except ValueError:
            log_warn(
                f"无效的通知级别: {os.getenv('NOTIFICATION_MIN_LEVEL')}",
                "NOTIFICATION_CONFIG",
            )

    # Webhook配置
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        config.webhook = WebhookConfig(
            enabled=True,
            url=webhook_url,
            method=os.getenv("WEBHOOK_METHOD", "POST"),
            message_format=os.getenv("WEBHOOK_FORMAT", "JSON"),
        )

    return config
