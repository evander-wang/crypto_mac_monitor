"""
价格相关告警条件
包括突破、冲击等价格变动告警
"""

import re
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


class PriceImpactCondition(BaseAlertCondition):
    """价格冲击告警条件"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.threshold = config.get("threshold", 3.0)  # 冲击阈值，默认3%
        self.high_threshold = config.get("high_threshold", 5.0)  # 高级别阈值
        self.check_realtime_range = config.get("check_realtime_range", True)  # 是否同时检查实时波动
        self.range_threshold = config.get("range_threshold", 4.0)  # 实时波动阈值

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """检查价格冲击条件"""
        extras = data.get("extras", {}).get("5m", {})
        if not extras:
            return None

        impulse_text = extras.get("impulse", "")
        range_text = extras.get("range", "")

        # 解析冲击数据
        impulse_pct = 0
        impulse_direction = None
        is_approximated = False

        if "⚡3x" in impulse_text:
            # 提取百分比
            match = re.search(r"(\d+\.?\d*)%", impulse_text)
            if match:
                impulse_pct = float(match.group(1))

                # 确定方向
                if "↑" in impulse_text:
                    impulse_direction = "上涨"
                elif "↓" in impulse_text:
                    impulse_direction = "下跌"

                # 检查是否为近似值
                is_approximated = "≈" in impulse_text

        # 解析实时波动数据
        range_pct = 0
        if range_text and "R:" in range_text:
            match = re.search(r"R:(\d+\.?\d*)%", range_text)
            if match:
                range_pct = float(match.group(1))

        # 判断是否触发告警
        triggered_by_impulse = impulse_pct >= self.threshold
        triggered_by_range = self.check_realtime_range and range_pct >= self.range_threshold

        if not (triggered_by_impulse or triggered_by_range):
            return None

        # 构建消息
        message_parts = []
        if triggered_by_impulse:
            approx_text = "≈" if is_approximated else ""
            message_parts.append(f"{approx_text}3x5m冲击{impulse_direction} {impulse_pct:.1f}%")

        if triggered_by_range:
            message_parts.append(f"实时波动 {range_pct:.1f}%")

        message = f"{symbol} {' + '.join(message_parts)}"

        # 确定告警级别
        max_pct = max(impulse_pct, range_pct)
        if max_pct >= self.high_threshold:
            level = AlertLevel.HIGH
        elif max_pct >= self.threshold:
            level = AlertLevel.MEDIUM
        else:
            level = AlertLevel.LOW

        # 根据冲击强度调整声音
        repeat_count = 1
        if max_pct >= self.high_threshold:
            repeat_count = 3
        elif max_pct >= self.threshold * 1.5:
            repeat_count = 2

        sound_config = SoundConfig(
            enabled=self.sound_config.enabled,
            file=self.sound_config.file,
            repeat=repeat_count,
            volume=self.sound_config.volume,
        )

        return self.create_alert_event(
            symbol=symbol,
            message=message,
            level=level,
            data={
                "impulse_pct": impulse_pct,
                "impulse_direction": impulse_direction,
                "range_pct": range_pct,
                "is_approximated": is_approximated,
                "triggered_by_impulse": triggered_by_impulse,
                "triggered_by_range": triggered_by_range,
            },
            custom_sound_config=sound_config,
        )


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
