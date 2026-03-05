"""
告警系统数据模型
定义告警事件、级别等基础数据结构
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional


class AlertLevel(Enum):
    """告警级别枚举"""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @property
    def priority(self) -> int:
        """获取优先级数值，数值越大优先级越高"""
        priority_map = {AlertLevel.LOW: 1, AlertLevel.MEDIUM: 2, AlertLevel.HIGH: 3}
        return priority_map[self]

    @property
    def display_name(self) -> str:
        """获取显示名称"""
        display_map = {
            AlertLevel.HIGH: "高",
            AlertLevel.MEDIUM: "中",
            AlertLevel.LOW: "低",
        }
        return display_map[self]


@dataclass
class SoundConfig:
    """声音配置"""

    enabled: bool = True
    file: Optional[str] = None  # 自定义音频文件路径
    repeat: int = 1  # 重复次数
    volume: float = 0.8  # 音量 0.0-1.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "enabled": self.enabled,
            "file": self.file,
            "repeat": self.repeat,
            "volume": self.volume,
        }


@dataclass
class AlertEvent:
    """告警事件"""

    condition: str  # 触发条件名称
    symbol: str  # 交易对符号
    message: str  # 告警消息
    level: AlertLevel  # 告警级别
    timestamp: float = field(default_factory=time.time)  # 时间戳
    data: Dict[str, Any] = field(default_factory=dict)  # 附加数据
    sound_config: SoundConfig = field(default_factory=SoundConfig)  # 声音配置

    @property
    def formatted_time(self) -> str:
        """格式化时间"""
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")

    @property
    def formatted_datetime(self) -> str:
        """格式化完整日期时间"""
        return datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于序列化"""
        return {
            "condition": self.condition,
            "symbol": self.symbol,
            "message": self.message,
            "level": self.level.value,
            "timestamp": self.timestamp,
            "formatted_time": self.formatted_time,
            "data": self.data,
            "sound_config": self.sound_config.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlertEvent":
        """从字典创建告警事件"""
        sound_config_data = data.get("sound_config", {})
        sound_config = SoundConfig(
            enabled=sound_config_data.get("enabled", True),
            file=sound_config_data.get("file"),
            repeat=sound_config_data.get("repeat", 1),
            volume=sound_config_data.get("volume", 0.8),
        )

        return cls(
            condition=data["condition"],
            symbol=data["symbol"],
            message=data["message"],
            level=AlertLevel(data["level"]),
            timestamp=data.get("timestamp", time.time()),
            data=data.get("data", {}),
            sound_config=sound_config,
        )


@dataclass
class AlertConditionConfig:
    """告警条件配置"""

    name: str
    condition_type: str
    enabled: bool = True
    cooldown: int = 300  # 冷却时间（秒）
    sound_config: SoundConfig = field(default_factory=SoundConfig)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.condition_type,
            "enabled": self.enabled,
            "cooldown": self.cooldown,
            "sound_config": self.sound_config.to_dict(),
            "parameters": self.parameters,
        }


@dataclass
class AlertChannelConfig:
    """告警渠道配置"""

    name: str
    channel_type: str
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.channel_type,
            "enabled": self.enabled,
            "parameters": self.parameters,
        }
