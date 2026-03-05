"""
移动平均线 指标告警条件（独立文件）
"""

from typing import Optional, Dict, Any
from ..models import AlertEvent, AlertLevel, SoundConfig
from .base_condition import BaseAlertCondition


class MovingAverageAlertCondition(BaseAlertCondition):
    """移动平均线指标告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # 移动平均线配置
        self.sma_cross_enabled = config.get("sma_cross_enabled", True)  # SMA交叉
        self.ema_cross_enabled = config.get("ema_cross_enabled", True)  # EMA交叉
        self.price_ma_threshold = config.get("price_ma_threshold", 0.5)  # 价格与均线距离阈值(%)

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查移动平均线指标条件"""
        trend_indicators = data.get("trend_indicators", {})
        current_price = data.get("price", 0)

        if current_price <= 0:
            return None

        # 获取移动平均线
        sma_20 = trend_indicators.get("sma_20", 0)
        sma_50 = trend_indicators.get("sma_50", 0)
        ema_20 = trend_indicators.get("ema_20", 0)

        if sma_20 <= 0 or sma_50 <= 0 or ema_20 <= 0:
            return None

        # 检查SMA金叉
        if self.sma_cross_enabled and sma_20 > sma_50:
            # 检查是否刚刚发生金叉（需要历史数据判断）
            message = f"{symbol} SMA金叉 - SMA20: {sma_20:.2f}, SMA50: {sma_50:.2f}"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.MEDIUM,
                data={
                    "sma_20": sma_20,
                    "sma_50": sma_50,
                    "signal_type": "sma_golden_cross",
                },
            )

        # 检查价格与均线关系
        price_sma20_diff = abs(current_price - sma_20) / sma_20 * 100
        if price_sma20_diff >= self.price_ma_threshold:
            direction = "上方" if current_price > sma_20 else "下方"
            message = f"{symbol} 价格偏离SMA20 - 价格: {current_price:.2f}, SMA20: {sma_20:.2f}, 偏离: {price_sma20_diff:.2f}%"
            return self.create_alert_event(
                symbol=symbol,
                message=message,
                level=AlertLevel.LOW,
                data={
                    "price": current_price,
                    "sma_20": sma_20,
                    "deviation": price_sma20_diff,
                    "signal_type": "price_ma_deviation",
                },
            )

        return None
