"""
价格冲击告警条件（单文件）
从原 price_conditions.py 拆分
"""

import re
from typing import Optional, Dict, Any

from ..models import AlertEvent, AlertLevel, SoundConfig
from .base_condition import BaseAlertCondition


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
