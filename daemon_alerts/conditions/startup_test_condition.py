"""
应用启动测试 告警条件（独立文件）
在应用启动后的首次告警检查中触发一次，用于钉钉启动通知。
"""

from typing import Optional, Dict, Any
from ..models import AlertEvent, AlertLevel
from .base_condition import BaseAlertCondition


class StartupTestCondition(BaseAlertCondition):
    """应用启动测试条件：每次应用启动触发一次告警"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.message = config.get("message", "应用启动测试通知")
        # 支持自定义告警级别，默认LOW
        level_str = config.get("level", "LOW").upper()
        self.level = getattr(AlertLevel, level_str, AlertLevel.LOW)
        # 仅在本次运行触发一次
        self._triggered_once = False
        # 可选：自定义symbol显示（部分渠道需要）
        self.default_symbol = config.get("symbol", "BTC/USDT")

    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        # 若已经在本次运行中触发过，则不再触发
        if self._triggered_once:
            return None

        # 若未触发过，则触发一次，并标记
        self._triggered_once = True
        used_symbol = symbol or self.default_symbol
        message = f"{self.message} - 应用已启动"

        return self.create_alert_event(
            symbol=used_symbol,
            message=message,
            level=self.level,
            data={"signal_type": "startup_test", "source": "app_startup"},
        )
