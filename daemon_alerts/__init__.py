"""
告警系统模块

包含告警管理器、告警条件、告警渠道等组件
支持传统模式和事件驱动模式
"""

from .models import AlertEvent, AlertLevel
from .conditions.base_condition import BaseAlertCondition
from .event_alert_manager import EventDrivenAlertManager, EventAlertCondition

__all__ = [
    # 传统告警组件
    "AlertEvent",
    "AlertLevel",
    "BaseAlertCondition",
    # 事件驱动告警组件
    "EventDrivenAlertManager",
    "EventAlertCondition",
]

# 版本信息
__version__ = "1.0.0"
