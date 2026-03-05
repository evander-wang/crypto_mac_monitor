"""
Notifications V2 Configuration Module

通知系统V2配置模块，提供统一的配置管理和依赖注入设置。

主要功能:
- 通知配置管理 (NotificationConfig)
- 渠道配置 (WebhookConfig, DesktopConfig)

主要组件:
- NotificationConfig: 主配置类
- ChannelConfigs: 各渠道配置类
"""

from .notification_config import (
    DEFAULT_NOTIFICATION_CONFIG,
    DesktopConfig,
    EmailConfig,
    NotificationConfig,
    WebhookConfig,
)


__all__ = [
    # 配置类
    "NotificationConfig",
    "WebhookConfig",
    "DesktopConfig",
    "EmailConfig",
    # 默认配置
    "DEFAULT_NOTIFICATION_CONFIG",
]
