"""
布林带 指标告警条件（独立文件）
"""

from typing import Optional, Dict, Any
from ..models import AlertEvent, AlertLevel, SoundConfig
from .base_condition import BaseAlertCondition


class BollingerBandsAlertCondition(BaseAlertCondition):
    """布林带指标告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # 布林带配置
        self.upper_breakout_threshold = config.get("upper_breakout_threshold", 0.5)  # 上轨突破阈值(%)
        self.lower_breakout_threshold = config.get("lower_breakout_threshold", 0.5)  # 下轨突破阈值(%)
        self.squeeze_threshold = config.get("squeeze_threshold", 2.0)  # 挤压阈值(%)
        self.expansion_threshold = config.get("expansion_threshold", 5.0)  # 扩张阈值(%)

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查布林带指标条件"""
        trend_indicators = data.get("trend_indicators", {})
        current_price = data.get("price", 0)

        # 获取布林带指标
        bb_data = trend_indicators.get("bollinger_bands", {})
        if not bb_data or current_price <= 0:
            return None

        upper = bb_data.get("upper", 0)
        middle = bb_data.get("middle", 0)
        lower = bb_data.get("lower", 0)
        width = bb_data.get("width", 0)

        if upper <= 0 or middle <= 0 or lower <= 0:
            return None

        # 计算价格相对位置
        price_position = (current_price - lower) / (upper - lower) * 100

        # 检查上轨突破
        if current_price > upper * (1 + self.upper_breakout_threshold / 100):
            message = f"{symbol} 布林带上轨突破 - 价格: {current_price:.2f}, 上轨: {upper:.2f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.HIGH,
                data={
                    "price": current_price,
                    "upper": upper,
                    "signal_type": "upper_breakout",
                },
            )

        # 检查下轨突破
        if current_price < lower * (1 - self.lower_breakout_threshold / 100):
            message = f"{symbol} 布林带下轨突破 - 价格: {current_price:.2f}, 下轨: {lower:.2f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.HIGH,
                data={
                    "price": current_price,
                    "lower": lower,
                    "signal_type": "lower_breakout",
                },
            )

        # 检查布林带挤压（窄通道）
        if width <= self.squeeze_threshold:
            message = f"{symbol} 布林带挤压 - 宽度: {width:.2f}%"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.MEDIUM,
                data={"width": width, "signal_type": "squeeze"},
            )

        # 检查布林带扩张（宽通道）
        if width >= self.expansion_threshold:
            message = f"{symbol} 布林带扩张 - 宽度: {width:.2f}%"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.MEDIUM,
                data={"width": width, "signal_type": "expansion"},
            )

        return None
