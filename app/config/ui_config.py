"""
UI配置类

管理用户界面相关的配置
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .base_config import BaseConfig


@dataclass
class DisplayConfig:
    """显示配置"""

    # 悬浮窗显示设置
    current_opacity: float = 0.9
    current_bg_style: str = "dark"

    # 多显示器支持
    display_mode: str = "auto"  # auto: 自动检测鼠标所在显示器, main: 主显示器, index: 指定显示器索引
    display_index: int = 0  # 当display_mode为"index"时使用的显示器索引

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "current_opacity": self.current_opacity,
            "current_bg_style": self.current_bg_style,
            "display_mode": self.display_mode,
            "display_index": self.display_index,
        }


@dataclass
class UIConfig(BaseConfig):
    """UI配置"""

    display: DisplayConfig = field(default_factory=DisplayConfig)

    def get_section_name(self) -> str:
        return "ui"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UIConfig":
        """从字典创建UI配置实例"""
        # 创建默认实例
        instance = cls()

        # 更新字段
        for key, value in data.items():
            if key == "display" and isinstance(value, dict):
                # 处理显示配置
                instance.display = DisplayConfig(**value)
            elif hasattr(instance, key):
                setattr(instance, key, value)

        return instance

    def get_current_settings(self) -> Dict[str, Any]:
        """获取当前设置"""
        return {
            "opacity": self.display.current_opacity,
            "bg_style": self.display.current_bg_style,
            "display_mode": self.display.display_mode,
            "display_index": self.display.display_index,
        }

    def update_setting(self, key: str, value: Any) -> None:
        """更新单个设置"""
        setting_map = {
            "opacity": "current_opacity",
            "bg_style": "current_bg_style",
            "display_mode": "display_mode",
            "display_index": "display_index",
        }

        if key in setting_map:
            setattr(self.display, setting_map[key], value)
        else:
            raise ValueError(f"Unknown setting: {key}")

    def validate(self) -> bool:
        """验证UI配置"""
        # 验证显示配置
        if not (0.0 <= self.display.current_opacity <= 1.0):
            return False
        if self.display.current_bg_style not in ["light", "dark", "deep", "auto"]:
            return False
        if self.display.display_mode not in ["auto", "main", "index"]:
            return False
        if self.display.display_index < 0:
            return False

        return True

    # 兼容旧配置的属性访问
    @property
    def floating_window_opacity(self) -> float:
        """兼容旧配置：浮动窗口透明度"""
        return self.display.current_opacity
