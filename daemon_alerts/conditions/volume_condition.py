"""
成交量 指标告警条件（独立文件）
"""

from typing import Optional, Dict, Any
from ..models import AlertEvent, AlertLevel, SoundConfig
from .base_condition import BaseAlertCondition


class VolumeAlertCondition(BaseAlertCondition):
    """成交量指标告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # 成交量配置
        self.volume_surge_threshold = config.get("volume_surge_threshold", 2.0)  # 放量阈值
        self.volume_dry_threshold = config.get("volume_dry_threshold", 0.5)  # 缩量阈值
        self.volume_ma_period = config.get("volume_ma_period", 20)  # 成交量均线周期

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查成交量指标条件"""
        trend_indicators = data.get("trend_indicators", {})

        # 获取成交量指标
        volume_surge = trend_indicators.get("volume_surge", False)
        volume_sma = trend_indicators.get("volume_sma", 0)
        current_volume = data.get("volume", 0)

        if volume_sma <= 0 or current_volume <= 0:
            return None

        volume_ratio = current_volume / volume_sma

        # 检查放量
        if volume_ratio >= self.volume_surge_threshold:
            message = f"{symbol} 成交量放大 - 量比: {volume_ratio:.2f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.MEDIUM,
                data={"volume_ratio": volume_ratio, "signal_type": "volume_surge"},
            )

        # 检查缩量
        elif volume_ratio <= self.volume_dry_threshold:
            message = f"{symbol} 成交量萎缩 - 量比: {volume_ratio:.2f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.LOW,
                data={"volume_ratio": volume_ratio, "signal_type": "volume_dry"},
            )

        return None
