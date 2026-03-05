"""
强突破告警条件（单文件）
从原 price_conditions.py 拆分
"""

from typing import Optional, Dict, Any

from ..models import AlertEvent, AlertLevel, SoundConfig
from .base_condition import BaseAlertCondition


class StrongBreakoutCondition(BaseAlertCondition):
    """强突破告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.min_confidence = config.get("min_confidence", 0.8)
        self.required_timeframes = config.get("required_timeframes", ["5m"])  # 需要触发的时间周期
        self.multi_timeframe_bonus = config.get("multi_timeframe_bonus", True)  # 多周期共振加分

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查强突破条件"""
        trend_indicators = data.get("trend_indicators", {})

        triggered_timeframes = []
        max_confidence = 0
        breakout_direction = None

        # 检查各个时间周期
        for tf in ["5m", "1h", "4h"]:
            if tf not in trend_indicators:
                continue

            trends = trend_indicators[tf]
            if not trends:
                continue

            # 查找突破信号和置信度
            has_breakout = False
            confidence = 0
            direction = None

            for trend in trends:
                if isinstance(trend, dict):
                    # 检查是否包含突破符号
                    trend_direction = trend.get("direction", "")
                    if "⚡" in trend_direction:
                        has_breakout = True

                        # 确定方向
                        if "↑" in trend_direction:
                            direction = "上涨"
                        elif "↓" in trend_direction:
                            direction = "下跌"

                    # 获取置信度
                    if "_meta" in trend:
                        meta = trend["_meta"]
                        confidence = meta.get("confidence", 0)

            # 如果满足条件
            if has_breakout and confidence >= self.min_confidence:
                triggered_timeframes.append({"timeframe": tf, "confidence": confidence, "direction": direction})

                if confidence > max_confidence:
                    max_confidence = confidence
                    breakout_direction = direction

        # 判断是否触发告警
        if not triggered_timeframes:
            return None

        # 检查是否满足必需的时间周期
        triggered_tf_names = [tf["timeframe"] for tf in triggered_timeframes]
        if not any(tf in triggered_tf_names for tf in self.required_timeframes):
            return None

        # 构建消息
        tf_info = []
        for tf_data in triggered_timeframes:
            tf = tf_data["timeframe"]
            conf = tf_data["confidence"]
            tf_info.append(f"{tf}({conf:.1f})")

        message = f"{symbol} 强突破{breakout_direction} - {', '.join(tf_info)}"

        # 确定告警级别
        level = AlertLevel.HIGH
        if len(triggered_timeframes) >= 2:
            level = AlertLevel.HIGH  # 多周期共振，高级别
        elif max_confidence >= 0.9:
            level = AlertLevel.HIGH
        elif max_confidence >= 0.8:
            level = AlertLevel.MEDIUM
        else:
            level = AlertLevel.LOW

        # 自定义声音配置（突破用更响亮的声音）
        sound_config = SoundConfig(
            enabled=self.sound_config.enabled,
            file=self.sound_config.file,
            repeat=min(3, len(triggered_timeframes)),  # 根据触发周期数重复
            volume=min(1.0, self.sound_config.volume + 0.1),  # 稍微提高音量
        )

        return self.create_alert_event(
            symbol=symbol,
            message=message,
            level=level,
            data={
                "triggered_timeframes": triggered_timeframes,
                "max_confidence": max_confidence,
                "direction": breakout_direction,
            },
            custom_sound_config=sound_config,
        )
