"""
Notifications V2 Module

A modern, flexible notification system with support for multiple channels,
configurable message formatting, and comprehensive error handling.
"""

from .channels.channel_manager import ChannelManager
from .config.notification_config import NotificationConfig
from .notification_manager import NotificationManager


__all__ = [
    "ChannelManager",
    "NotificationConfig",
    "NotificationManager",
]

__version__ = "2.0.0"
