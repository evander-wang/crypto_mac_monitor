"""
技术指标告警条件模块

此文件已弃用。所有指标条件已拆分到独立文件中:
- MACD: macd_condition.py
- RSI: rsi_condition.py
- Bollinger Bands: bollinger_bands_condition.py
- ADX: adx_condition.py
- Volume: volume_condition.py
- Moving Average: moving_average_condition.py
- Multi Indicator: multi_indicator_condition.py

请使用独立的条件文件。
"""

# 此文件保留以向后兼容，从独立文件重新导出类
from typing import Any, Dict, Optional

from ..models import AlertEvent, AlertLevel
from .adx_condition import ADXAlertCondition
from .base_condition import BaseAlertCondition
from .bollinger_bands_condition import BollingerBandsAlertCondition
from .macd_condition import MACDAlertCondition
from .moving_average_condition import MovingAverageAlertCondition
from .multi_indicator_condition import MultiIndicatorAlertCondition
from .rsi_condition import RSIAlertCondition
from .volume_condition import VolumeAlertCondition


# 导出所有类以保持向后兼容
__all__ = [
    "MACDAlertCondition",
    "RSIAlertCondition",
    "BollingerBandsAlertCondition",
    "ADXAlertCondition",
    "VolumeAlertCondition",
    "MovingAverageAlertCondition",
    "MultiIndicatorAlertCondition",
]
