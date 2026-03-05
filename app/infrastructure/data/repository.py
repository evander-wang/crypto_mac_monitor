"""KlineRepository - K线数据仓储实现"""

from typing import Optional

import pandas as pd

from app.config.config_manager import ConfigManager
from app.data_manager.thread_memory_data_cache_manager import ThreadMemoryDataCacheManager
from app.domain.repositories.config_provider import ConfigProvider
from app.domain.repositories.data_provider import DataProvider


class KlineRepository(DataProvider):
    """
    K线数据仓储实现

    基础设施层实现 DataProvider 接口。
    委托给 ThreadMemoryDataCacheManager 进行实际数据访问。
    """

    def __init__(self, config: ConfigProvider, cache_ttl: int = 300):
        """
        初始化仓储

        Args:
            config: 配置提供者
            cache_ttl: 缓存过期时间（秒）
        """
        self._config = config
        # 创建 ConfigManager 实例
        self._config_manager = ConfigManager()
        # 创建缓存管理器
        self._cache_manager = ThreadMemoryDataCacheManager(self._config_manager)

    def get_kline_data(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """
        获取 K线数据

        Args:
            symbol: 交易对符号
            timeframe: 时间周期
            limit: 数据条数

        Returns:
            K线数据 DataFrame，或 None（数据不可用）
        """
        return self._cache_manager.get_kline_data(symbol, timeframe, limit)

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        获取当前价格

        Args:
            symbol: 交易对符号

        Returns:
            当前价格，或 None（价格不可用）
        """
        ticker_data = self._cache_manager.get_ticker_data(symbol)
        if ticker_data is None:
            return None

        # 尝试获取 last 价格
        return getattr(ticker_data, "last", None)

    def is_data_ready(self, symbol: str, timeframe: str) -> bool:
        """
        检查数据是否就绪

        Args:
            symbol: 交易对符号
            timeframe: 时间周期

        Returns:
            True 如果数据可用且足够
        """
        # 从配置获取最小周期数
        data_config = self._config_manager.get_data_config()
        min_periods = data_config.timeframes.get(timeframe)
        if min_periods is not None:
            min_periods_value = min_periods.min_periods
        else:
            min_periods_value = 50

        return self._cache_manager.is_kline_data_ready(symbol, timeframe, min_periods_value)
