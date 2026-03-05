"""
Notification Channels Module

通知渠道模块，提供各种通知渠道的实现。
"""

from .desktop_channel import DesktopChannel
from .webhook_channel import WebhookChannel


__all__ = [
    "WebhookChannel",
    "DesktopChannel",
]
