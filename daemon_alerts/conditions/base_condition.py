"""
基础告警条件类
所有具体告警条件的基类
"""

import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from ..models import AlertEvent, AlertLevel, SoundConfig


class BaseAlertCondition(ABC):
    """基础告警条件类"""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", True)
        self.cooldown = config.get("cooldown", 300)  # 默认5分钟冷却
        self.last_trigger_time = 0

        # 解析声音配置
        sound_config_data = config.get("sound_config", {})
        self.sound_config = SoundConfig(
            enabled=sound_config_data.get("enabled", True),
            file=sound_config_data.get("file"),
            repeat=sound_config_data.get("repeat", 1),
            volume=sound_config_data.get("volume", 0.8),
        )

    @abstractmethod
    def check(self, symbol: str, data: Dict[str, Any]) -> Optional[AlertEvent]:
        """
        检查是否满足告警条件

        Args:
            symbol: 交易对符号
            data: 包含价格、趋势等信息的数据字典

        Returns:
            如果满足条件返回AlertEvent，否则返回None
        """
        pass

    def is_enabled(self) -> bool:
        """检查条件是否启用"""
        return self.enabled

    def is_in_cooldown(self) -> bool:
        """检查是否在冷却期内"""
        return time.time() - self.last_trigger_time < self.cooldown

    def update_trigger_time(self) -> None:
        """更新触发时间"""
        self.last_trigger_time = time.time()

    def create_alert_event(
        self,
        symbol: str,
        message: str,
        level: AlertLevel,
        data: Optional[Dict[str, Any]] = None,
        custom_sound_config: Optional[SoundConfig] = None,
    ) -> AlertEvent:
        """
        创建告警事件

        Args:
            symbol: 交易对符号
            message: 告警消息
            level: 告警级别
            data: 附加数据
            custom_sound_config: 自定义声音配置，如果不提供则使用条件的默认配置

        Returns:
            AlertEvent实例
        """
        sound_config = custom_sound_config or self.sound_config

        return AlertEvent(
            condition=self.name,
            symbol=symbol,
            message=message,
            level=level,
            data=data or {},
            sound_config=sound_config,
        )

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.config.get(key, default)

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """更新配置"""
        self.config.update(new_config)

        # 更新基础属性
        self.enabled = self.config.get("enabled", True)
        self.cooldown = self.config.get("cooldown", 300)

        # 更新声音配置
        sound_config_data = self.config.get("sound_config", {})
        self.sound_config = SoundConfig(
            enabled=sound_config_data.get("enabled", True),
            file=sound_config_data.get("file"),
            repeat=sound_config_data.get("repeat", 1),
            volume=sound_config_data.get("volume", 0.8),
        )

    def get_status_info(self) -> Dict[str, Any]:
        """获取条件状态信息"""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "in_cooldown": self.is_in_cooldown(),
            "last_trigger_time": self.last_trigger_time,
            "cooldown_remaining": max(0, self.cooldown - (time.time() - self.last_trigger_time)),
            "config": self.config,
        }
