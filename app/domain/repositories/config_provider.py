"""ConfigProvider 接口 - 配置提供者抽象"""

from abc import ABC, abstractmethod
from typing import Dict, List


class ConfigProvider(ABC):
    """
    配置提供者抽象接口

    领域层定义，由基础设施层实现。
    封装所有配置访问逻辑。
    """

    @abstractmethod
    def get_symbols(self) -> List[str]:
        """获取配置的交易对列表"""
        pass

    @abstractmethod
    def get_timeframes(self) -> Dict[str, any]:
        """获取配置的时间周期"""
        pass

    @abstractmethod
    def get_trend_min_confidence(self, timeframe: str) -> float:
        """获取指定时间周期的最小置信度阈值"""
        pass
