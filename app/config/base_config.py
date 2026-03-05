"""
基础配置类

定义所有配置类的基础接口和通用功能
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class BaseConfig(ABC):
    """配置基类"""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseConfig":
        """从字典创建配置实例"""
        try:
            return cls(**data)
        except TypeError:
            # 如果直接创建失败，使用默认实例然后更新字段
            instance = cls()
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            return instance

    def update(self, **kwargs) -> None:
        """更新配置项"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"Unknown config key: {key}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return getattr(self, key, default)

    def validate(self) -> bool:
        """验证配置有效性"""
        return True  # 子类可以重写此方法

    @abstractmethod
    def get_section_name(self) -> str:
        """获取配置节名称"""
        pass
