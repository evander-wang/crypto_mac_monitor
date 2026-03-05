"""DataProvider 接口 - 数据提供者抽象"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class DataProvider(ABC):
    """
    数据提供者抽象接口

    领域层定义，由基础设施层实现。
    封装所有数据访问逻辑，使领域层不依赖具体实现。
    """

    @abstractmethod
    def get_kline_data(
        self, symbol: str, timeframe: str, limit: int
    ) -> Optional[pd.DataFrame]:
        """
        获取 K 线数据

        Args:
            symbol: 交易对符号，如 'BTC-USDT'
            timeframe: 时间周期，如 '5m', '1h'
            limit: 数据条数

        Returns:
            K线数据 DataFrame，或 None（数据不可用）
        """
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        获取当前价格

        Args:
            symbol: 交易对符号

        Returns:
            当前价格，或 None（价格不可用）
        """
        pass

    @abstractmethod
    def is_data_ready(self, symbol: str, timeframe: str) -> bool:
        """
        检查数据是否就绪

        Args:
            symbol: 交易对符号
            timeframe: 时间周期

        Returns:
            True 如果数据可用且足够
        """
        pass
