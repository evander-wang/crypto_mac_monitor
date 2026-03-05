"""
价格相关告警条件模块

此文件已弃用。所有价格条件已拆分到独立文件中:
- Strong Breakout: strong_breakout_condition.py
- Price Impact: price_impact_condition.py
- Trend Reversal: trend_reversal_condition.py

请使用独立的条件文件。
"""

# 此文件保留以向后兼容，从独立文件重新导出类
from typing import Any, Dict, Optional

from ..models import AlertEvent, AlertLevel, SoundConfig
from .base_condition import BaseAlertCondition
from .price_impact_condition import PriceImpactCondition
from .strong_breakout_condition import StrongBreakoutCondition
from .trend_reversal_condition import TrendReversalCondition


# 导出所有类以保持向后兼容
__all__ = [
    "StrongBreakoutCondition",
    "PriceImpactCondition",
    "TrendReversalCondition",
]
