"""
趋势反转告警条件（单文件）
从原 price_conditions.py 拆分
"""

from typing import Optional, Dict, Any

from ..models import AlertEvent, AlertLevel, SoundConfig
from .base_condition import BaseAlertCondition


class TrendReversalCondition(BaseAlertCondition):
    """趋势反转告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.min_confidence = config.get("min_confidence", 0.7)
        self.required_timeframe = config.get("required_timeframe", "1h")  # 主要观察的时间周期
        self.confirmation_needed = config.get("confirmation_needed", True)  # 是否需要其他周期确认

        # 存储上次的趋势状态
        self.last_trends = {}

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查趋势反转条件"""
        trend_indicators = data.get("trend_indicators", {})

        if self.required_timeframe not in trend_indicators:
            return None

        trends = trend_indicators[self.required_timeframe]
        if not trends:
            return None

        # 获取当前趋势方向和置信度
        current_direction = None
        current_confidence = 0

        for trend in trends:
            if isinstance(trend, dict):
                if "_meta" in trend:
                    meta = trend["_meta"]
                    current_confidence = meta.get("confidence", 0)

                    # 从其他趋势指标判断方向
                    trend_direction = trend.get("direction", "")
                    if "↑" in trend_direction:
                        current_direction = "up"
                    elif "↓" in trend_direction:
                        current_direction = "down"
                    elif "→" in trend_direction:
                        current_direction = "sideways"

                    break

        if not current_direction or current_confidence < self.min_confidence:
            return None

        # 检查是否有反转
        last_direction = self.last_trends.get(symbol)
        self.last_trends[symbol] = current_direction

        if last_direction is None or last_direction == current_direction:
            return None

        # 确认反转（不是从横盘状态的变化）
        if last_direction == "sideways" or current_direction == "sideways":
            return None

        # 构建反转消息
        direction_names = {"up": "上涨", "down": "下跌", "sideways": "横盘"}

        message = f"{symbol} {self.required_timeframe} 趋势反转: {direction_names[last_direction]} → {direction_names[current_direction]} (置信度: {current_confidence:.1f})"

        # 趋势反转通常是高级别告警
        level = AlertLevel.HIGH

        # 反转告警使用特殊的声音配置
        sound_config = SoundConfig(
            enabled=self.sound_config.enabled,
            file=self.sound_config.file or "trend_reversal.wav",  # 使用特殊的反转声音
            repeat=2,  # 重复2次强调
            volume=min(1.0, self.sound_config.volume + 0.2),  # 提高音量
        )

        return self.create_alert_event(
            symbol=symbol,
            message=message,
            level=level,
            data={
                "timeframe": self.required_timeframe,
                "from_direction": last_direction,
                "to_direction": current_direction,
                "confidence": current_confidence,
            },
            custom_sound_config=sound_config,
        )
