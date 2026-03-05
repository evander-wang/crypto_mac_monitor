"""
应用配置类

管理应用级别的配置，主要包括UI配置和基本应用信息
注意：API、网络、交易、日志等配置类已删除（未使用）
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .base_config import BaseConfig
from .ui_config import UIConfig


# 注意：APIConfig、NetworkConfig、TradingConfig、LoggingConfig 已删除
# 这些配置类在当前项目中未被实际使用


@dataclass
class AppConfig(BaseConfig):
    """应用配置"""

    # 各模块配置
    ui: UIConfig = field(default_factory=UIConfig)

    # 资源配置
    icon_path: str = "btc-line.png"
    # 是否启用 ticker 价格更新 任务， ui 里面需要， monitor 里面不需要
    enable_ticker_task: bool = True
    # 是否启用世界时钟服务（Linux 下通常不需要）
    enable_world_clock_service: bool = True

    # 时区配置
    timezones: Dict[str, Dict[str, str]] = field(default_factory=lambda: {})

    def get_section_name(self) -> str:
        return "app"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """从字典创建应用配置实例"""
        # 创建默认实例
        instance = cls()

        # 更新字段
        for key, value in data.items():
            if key == "ui" and isinstance(value, dict):
                # 处理UI配置
                instance.ui = UIConfig(**value)
            elif key == "timezones" and isinstance(value, dict):
                # 处理时区配置
                instance.timezones = value
            elif hasattr(instance, key):
                setattr(instance, key, value)

        return instance

    def validate(self) -> bool:
        """验证应用配置"""
        if hasattr(self.ui, "validate") and not self.ui.validate():
            return False

        return True

    def get_icon_path(self) -> str:
        """获取图标路径"""
        return self.icon_path

    def get_timezones(self) -> Dict[str, Tuple[str, str]]:
        """
        获取时区配置，转换为原有格式

        Returns:
            Dict[str, Tuple[str, str]]: 时区配置字典，格式为 {name: (timezone, flag)}
        """
        result = {}
        for name, config in self.timezones.items():
            result[name] = (config["timezone"], config["flag"])
        return result
