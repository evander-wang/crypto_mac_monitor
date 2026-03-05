"""
from utils.logger import log_error

趋势检测模型基类
定义所有趋势检测模型的通用接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd


@dataclass
class TrendResult:
    """趋势分析结果"""

    trend_type: str  # "突破", "宽通道", "窄通道", "震荡"
    confidence: float  # 置信度 0-1
    direction: str  # "上涨", "下跌", "横盘"
    strength: float  # 强度 0-3
    details: Dict  # 详细信息


class BaseTrendModel(ABC):
    """趋势检测模型基类"""

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化模型

        Args:
            config: 配置参数字典
        """
        self.config = config or {}
        self.name = self.__class__.__name__

    @abstractmethod
    def analyze(self, df: pd.DataFrame, indicators: Dict) -> Optional[TrendResult]:
        """
        分析趋势

        Args:
            df: OHLCV数据
            indicators: 技术指标字典

        Returns:
            趋势分析结果，如果无法分析返回None
        """
        pass

    @abstractmethod
    def get_required_periods(self) -> int:
        """返回分析所需的最小数据周期数"""
        pass

    def is_data_sufficient(self, df: pd.DataFrame) -> bool:
        """检查数据是否足够进行分析"""
        return len(df) >= self.get_required_periods()

    def get_latest_values(self, series: pd.Series, count: int = 1):
        """获取最新的N个值，处理NaN"""
        if series is None or series.empty:
            return None

        # 过滤NaN值
        valid_data = series.dropna()
        if len(valid_data) < count:
            return None

        if count == 1:
            return valid_data.iloc[-1]
        else:
            return valid_data.tail(count)
