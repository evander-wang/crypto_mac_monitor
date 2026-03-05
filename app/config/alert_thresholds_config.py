"""
告警阈值配置

集中管理实时指标告警的阈值与基础设置，支持通过 app_config.yaml 动态配置。
"""

from dataclasses import dataclass
from typing import Any, Dict

from app.consts.consts import (
    ALERT_BREAKOUT_CHANGE_PCT_MIN,
    ALERT_BREAKOUT_CONSECUTIVE_MIN,
    ALERT_COOLDOWN_SEC,
    ALERT_IMPULSE_PCT_THRESHOLD,
    ALERT_NOTIFICATION_TITLE_PREFIX,
    ALERT_REALTIME_RANGE_PCT_MIN,
)

from .base_config import BaseConfig


@dataclass
class AlertThresholdsConfig(BaseConfig):
    """实时指标告警阈值配置"""

    # 阈值设置
    impulse_pct_threshold: float = ALERT_IMPULSE_PCT_THRESHOLD
    breakout_consecutive_min: int = ALERT_BREAKOUT_CONSECUTIVE_MIN
    breakout_change_pct_min: float = ALERT_BREAKOUT_CHANGE_PCT_MIN
    realtime_range_pct_min: float = ALERT_REALTIME_RANGE_PCT_MIN

    # 其他设置
    cooldown_sec: int = ALERT_COOLDOWN_SEC
    notification_title_prefix: str = ALERT_NOTIFICATION_TITLE_PREFIX

    def get_section_name(self) -> str:
        return "alert_thresholds"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlertThresholdsConfig":
        """从字典创建配置实例，包含类型转换与默认值回退"""

        def _to_float(val: Any, default: float) -> float:
            try:
                return float(val)
            except Exception:
                return default

        def _to_int(val: Any, default: int) -> int:
            try:
                return int(val)
            except Exception:
                try:
                    return int(float(val))
                except Exception:
                    return default

        return cls(
            impulse_pct_threshold=_to_float(data.get("impulse_pct_threshold", ALERT_IMPULSE_PCT_THRESHOLD), ALERT_IMPULSE_PCT_THRESHOLD),
            breakout_consecutive_min=_to_int(
                data.get("breakout_consecutive_min", ALERT_BREAKOUT_CONSECUTIVE_MIN), ALERT_BREAKOUT_CONSECUTIVE_MIN
            ),
            breakout_change_pct_min=_to_float(
                data.get("breakout_change_pct_min", ALERT_BREAKOUT_CHANGE_PCT_MIN), ALERT_BREAKOUT_CHANGE_PCT_MIN
            ),
            realtime_range_pct_min=_to_float(
                data.get("realtime_range_pct_min", ALERT_REALTIME_RANGE_PCT_MIN), ALERT_REALTIME_RANGE_PCT_MIN
            ),
            cooldown_sec=_to_int(data.get("cooldown_sec", ALERT_COOLDOWN_SEC), ALERT_COOLDOWN_SEC),
            notification_title_prefix=str(data.get("notification_title_prefix", ALERT_NOTIFICATION_TITLE_PREFIX)),
        )

    def validate(self) -> bool:
        """简单验证配置的合理性"""
        try:
            return (
                self.impulse_pct_threshold >= 0.0
                and self.breakout_consecutive_min >= 1
                and self.breakout_change_pct_min >= 0.0
                and self.realtime_range_pct_min >= 0.0
                and self.cooldown_sec >= 0
                and isinstance(self.notification_title_prefix, str)
            )
        except Exception:
            return False
