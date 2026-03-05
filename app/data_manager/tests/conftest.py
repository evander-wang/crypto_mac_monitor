"""
Data manager module test configuration and shared fixtures.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from app.data_manager.thread_memory_data_cache_manager import ThreadMemoryDataCacheManager
from app.models.dto import ReturnTickerDTO


@pytest.fixture
def mock_config_manager():
    """提供模拟的配置管理器."""
    config_manager = Mock()

    # 模拟 DataConfig
    data_config = Mock()
    data_config.cache.max_size = 100
    data_config.cache.data_expiry = 300

    time_configs = {
        "1m": Mock(min_periods=10),
        "5m": Mock(min_periods=20),
        "1h": Mock(min_periods=10),
    }
    data_config.timeframes = time_configs

    config_manager.get_data_config = Mock(return_value=data_config)

    return config_manager


@pytest.fixture
def cache_manager(mock_config_manager):
    """提供 ThreadMemoryDataCacheManager 实例."""
    manager = ThreadMemoryDataCacheManager(mock_config_manager)
    return manager


@pytest.fixture
def sample_kline_data():
    """提供示例 K 线数据."""
    now = datetime.now()
    timestamps = pd.date_range(start=now - timedelta(hours=1), periods=50, freq="1min")

    data = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": np.linspace(50000, 50100, 50),
            "high": np.linspace(50010, 50120, 50),
            "low": np.linspace(49990, 50080, 50),
            "close": np.linspace(50000, 50100, 50),
            "volume": np.random.uniform(100, 1000, 50),
        }
    )

    return data


@pytest.fixture
def sample_ticker_dto():
    """提供示例 TickerDTO."""
    return ReturnTickerDTO(
        symbol="BTC-USDT-SWAP",
        last=50000.0,
        open24h=49500.0,
        high24h=51000.0,
        low24h=49000.0,
        vol_base_24h=1000.0,
        vol_quote_24h=50000000.0,
        timestamp_ms=int(datetime.now().timestamp() * 1000),
    )
