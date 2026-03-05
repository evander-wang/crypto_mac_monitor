"""
ADX 指标告警条件（独立文件）
"""

from typing import Optional, Dict, Any
from ..models import AlertEvent, AlertLevel, SoundConfig
from .base_condition import BaseAlertCondition


class ADXAlertCondition(BaseAlertCondition):
    """ADX趋势强度指标告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # ADX配置
        self.strong_trend_threshold = config.get("strong_trend_threshold", 25)  # 强趋势阈值
        self.very_strong_trend_threshold = config.get("very_strong_trend_threshold", 40)  # 极强趋势阈值
        self.trend_change_threshold = config.get("trend_change_threshold", 5)  # 趋势变化阈值

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查ADX指标条件"""
        trend_indicators = data.get("trend_indicators", {})

        # 获取ADX指标
        adx_value = trend_indicators.get("adx", 0)

        if adx_value <= 0:
            return None

        # 检查极强趋势
        if adx_value >= self.very_strong_trend_threshold:
            message = f"{symbol} ADX极强趋势 - ADX: {adx_value:.1f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.HIGH,
                data={"adx_value": adx_value, "signal_type": "very_strong_trend"},
            )

        # 检查强趋势
        elif adx_value >= self.strong_trend_threshold:
            message = f"{symbol} ADX强趋势 - ADX: {adx_value:.1f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.MEDIUM,
                data={"adx_value": adx_value, "signal_type": "strong_trend"},
            )

        return None
