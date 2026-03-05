"""
RSI 指标告警条件（独立文件）
"""

from typing import Optional, Dict, Any
from ..models import AlertEvent, AlertLevel, SoundConfig
from .base_condition import BaseAlertCondition


class RSIAlertCondition(BaseAlertCondition):
    """RSI指标告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # RSI配置
        self.oversold_threshold = config.get("oversold_threshold", 20)  # 超卖阈值
        self.overbought_threshold = config.get("overbought_threshold", 80)  # 超买阈值
        self.extreme_oversold = config.get("extreme_oversold", 15)  # 极度超卖
        self.extreme_overbought = config.get("extreme_overbought", 85)  # 极度超买
        self.divergence_check = config.get("divergence_check", False)  # 背离检测

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查RSI指标条件"""
        trend_indicators = data.get("trend_indicators", {})

        # 获取RSI指标
        rsi_data = trend_indicators.get("rsi", {})
        if not rsi_data:
            return None

        rsi_value = rsi_data.get("rsi", 50)

        # 检查极度超卖
        if rsi_value <= self.extreme_oversold:
            message = f"{symbol} RSI极度超卖 - RSI: {rsi_value:.1f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.HIGH,
                data={"rsi_value": rsi_value, "signal_type": "extreme_oversold"},
            )

        # 检查极度超买
        if rsi_value >= self.extreme_overbought:
            message = f"{symbol} RSI极度超买 - RSI: {rsi_value:.1f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.HIGH,
                data={"rsi_value": rsi_value, "signal_type": "extreme_overbought"},
            )

        # 检查超卖反弹
        if rsi_data.get("oversold", False) and rsi_value > self.oversold_threshold + 5:
            message = f"{symbol} RSI超卖反弹 - RSI: {rsi_value:.1f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.MEDIUM,
                data={"rsi_value": rsi_value, "signal_type": "oversold_rebound"},
            )

        # 检查超买回落
        if rsi_data.get("overbought", False) and rsi_value < self.overbought_threshold - 5:
            message = f"{symbol} RSI超买回落 - RSI: {rsi_value:.1f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.MEDIUM,
                data={"rsi_value": rsi_value, "signal_type": "overbought_fall"},
            )

        return None
