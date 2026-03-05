"""
多指标综合 告警条件（独立文件）
"""

from typing import Optional, Dict, Any, List
from ..models import AlertEvent, AlertLevel, SoundConfig
from .base_condition import BaseAlertCondition


class MultiIndicatorAlertCondition(BaseAlertCondition):
    """多指标综合告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # 综合配置
        self.min_indicators = config.get("min_indicators", 3)  # 最少指标数量
        self.bullish_indicators = config.get("bullish_indicators", [])  # 看涨指标列表
        self.bearish_indicators = config.get("bearish_indicators", [])  # 看跌指标列表

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查多指标综合条件"""
        trend_indicators = data.get("trend_indicators", {})

        bullish_count = 0
        bearish_count = 0
        triggered_indicators = []

        # 检查看涨指标
        for indicator in self.bullish_indicators:
            if self._check_indicator_bullish(trend_indicators, indicator):
                bullish_count += 1
                triggered_indicators.append(f"看涨_{indicator}")

        # 检查看跌指标
        for indicator in self.bearish_indicators:
            if self._check_indicator_bearish(trend_indicators, indicator):
                bearish_count += 1
                triggered_indicators.append(f"看跌_{indicator}")

        # 判断综合信号
        if bullish_count >= self.min_indicators:
            message = f"{symbol} 多指标看涨信号 - 触发指标: {', '.join(triggered_indicators)}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.HIGH,
                data={
                    "bullish_count": bullish_count,
                    "indicators": triggered_indicators,
                    "signal_type": "multi_bullish",
                },
            )

        elif bearish_count >= self.min_indicators:
            message = f"{symbol} 多指标看跌信号 - 触发指标: {', '.join(triggered_indicators)}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.HIGH,
                data={
                    "bearish_count": bearish_count,
                    "indicators": triggered_indicators,
                    "signal_type": "multi_bearish",
                },
            )

        return None

    def _check_indicator_bullish(self, trend_indicators: Dict, indicator: str) -> bool:
        """检查指标是否看涨"""
        if indicator == "macd_golden_cross":
            return trend_indicators.get("macd", {}).get("golden_cross", False)
        elif indicator == "rsi_oversold_rebound":
            rsi_data = trend_indicators.get("rsi", {})
            return rsi_data.get("oversold", False) and rsi_data.get("rsi", 50) > 25
        elif indicator == "bb_lower_bounce":
            # 布林带下轨反弹
            return False  # 需要实现具体逻辑
        return False

    def _check_indicator_bearish(self, trend_indicators: Dict, indicator: str) -> bool:
        """检查指标是否看跌"""
        if indicator == "macd_death_cross":
            return trend_indicators.get("macd", {}).get("death_cross", False)
        elif indicator == "rsi_overbought_fall":
            rsi_data = trend_indicators.get("rsi", {})
            return rsi_data.get("overbought", False) and rsi_data.get("rsi", 50) < 75
        elif indicator == "bb_upper_rejection":
            # 布林带上轨回落
            return False  # 需要实现具体逻辑
        return False
