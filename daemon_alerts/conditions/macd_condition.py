"""
MACD 指标告警条件（独立文件）
"""

from typing import Optional, Dict, Any
from ..models import AlertEvent, AlertLevel, SoundConfig
from .base_condition import BaseAlertCondition


class MACDAlertCondition(BaseAlertCondition):
    """MACD指标告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # MACD配置
        self.golden_cross_enabled = config.get("golden_cross_enabled", True)  # 金叉告警
        self.death_cross_enabled = config.get("death_cross_enabled", True)  # 死叉告警
        self.histogram_threshold = config.get("histogram_threshold", 0.01)  # 柱状图阈值
        self.macd_strength_threshold = config.get("macd_strength_threshold", 0.02)  # MACD强度阈值

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查MACD指标条件"""
        trend_indicators = data.get("trend_indicators", {})

        # 获取MACD指标
        macd_data = trend_indicators.get("macd", {})
        if not macd_data:
            return None

        # 检查金叉
        if self.golden_cross_enabled and macd_data.get("golden_cross", False):
            # 金叉确认：MACD线在零轴上方且柱状图放大
            macd_value = macd_data.get("macd", 0)
            histogram = macd_data.get("histogram", 0)

            if macd_value > 0 and histogram > self.histogram_threshold:
                message = f"{symbol} MACD金叉确认 - MACD: {macd_value:.4f}, 柱状图: {histogram:.4f}"
                return self.create_alert_event(
                    symbol=symbol,
                    message=message,
                    level=AlertLevel.HIGH,
                    data={
                        "macd_value": macd_value,
                        "histogram": histogram,
                        "signal_type": "golden_cross",
                    },
                )

        # 检查死叉
        if self.death_cross_enabled and macd_data.get("death_cross", False):
            # 死叉确认：MACD线在零轴下方且柱状图放大
            macd_value = macd_data.get("macd", 0)
            histogram = macd_data.get("histogram", 0)

            if macd_value < 0 and abs(histogram) > self.histogram_threshold:
                message = f"{symbol} MACD死叉确认 - MACD: {macd_value:.4f}, 柱状图: {histogram:.4f}"
                return self.create_alert_event(
                    symbol=symbol,
                    message=message,
                    level=AlertLevel.HIGH,
                    data={
                        "macd_value": macd_value,
                        "histogram": histogram,
                        "signal_type": "death_cross",
                    },
                )

        return None
