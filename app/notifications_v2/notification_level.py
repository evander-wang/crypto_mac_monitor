"""
通知发送器接口定义
"""

from enum import Enum


class NotificationLevel(Enum):
    """通知级别"""

    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
