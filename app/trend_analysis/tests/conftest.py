"""
共享 fixtures 和测试工具.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, Mock

import numpy as np
import pandas as pd
import pytest

from app.data_manager.thread_memory_data_cache_manager import ThreadMemoryDataCacheManager
from app.models.dto import ReturnTickerDTO


@pytest.fixture
def mock_config_manager():
    """提供模拟的配置管理器."""
    config = Mock()
    config.max_size = 100
    config.default_ttl = 300

    # Mock 数据配置
    data_config = Mock()
    data_config.timeframes = {
        "1m": Mock(min_periods=20),
        "5m": Mock(min_periods=50),
        "1h": Mock(min_periods=30),
    }
    data_config.trend_analyzer_fetch_periods = 30
    data_config.trend_models = None

    config.data_config = data_config
    return config


@pytest.fixture
def mock_data_manager(mock_config_manager):
    """提供模拟的数据管理器."""
    manager = Mock(spec=ThreadMemoryDataCacheManager)

    # 设置 data_config 属性
    manager.data_config = mock_config_manager.data_config

    # Mock get_kline_data 方法
    def mock_get_kline(symbol, bar, limit=None):
        # 生成示例 K 线数据
        now = datetime.now()
        periods = limit if limit else 50
        timestamps = pd.date_range(start=now - timedelta(hours=1), periods=periods, freq="1min")

        # 生成有趋势的数据
        close_prices = np.linspace(50000, 50500, periods) + np.random.normal(0, 50, periods)

        df = pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": close_prices * 0.999,
                "high": close_prices * 1.001,
                "low": close_prices * 0.998,
                "close": close_prices,
                "volume": np.random.uniform(100, 1000, periods),
            }
        )
        return df

    manager.get_kline_data = mock_get_kline

    # Mock is_kline_data_ready 方法
    manager.is_kline_data_ready = Mock(return_value=True)

    # Mock get_supported_symbols 方法
    manager.get_supported_symbols = Mock(return_value=["BTC-USDT-SWAP", "ETH-USDT-SWAP"])

    return manager


@pytest.fixture
def sample_kline_data():
    """提供示例 K 线数据."""
    now = datetime.now()
    periods = 50
    timestamps = pd.date_range(start=now - timedelta(hours=1), periods=periods, freq="1min")

    # 生成有趋势的数据(上涨趋势)
    close_prices = np.linspace(50000, 50500, periods) + np.random.normal(0, 30, periods)

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": close_prices * 0.999,
            "high": close_prices * 1.001,
            "low": close_prices * 0.998,
            "close": close_prices,
            "volume": np.random.uniform(100, 1000, periods),
        }
    )

    return df


@pytest.fixture
def sample_kline_data_uptrend():
    """提供上涨趋势的 K 线数据."""
    now = datetime.now()
    periods = 50
    timestamps = pd.date_range(start=now - timedelta(hours=1), periods=periods, freq="1min")

    # 明显的上涨趋势
    close_prices = np.linspace(50000, 51000, periods)

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": close_prices * 0.999,
            "high": close_prices * 1.002,
            "low": close_prices * 0.997,
            "close": close_prices,
            "volume": np.linspace(100, 200, periods),  # 成交量也增加
        }
    )

    return df


@pytest.fixture
def sample_kline_data_sideways():
    """提供横盘震荡的 K 线数据."""
    now = datetime.now()
    periods = 50
    timestamps = pd.date_range(start=now - timedelta(hours=1), periods=periods, freq="1min")

    # 横盘震荡
    close_prices = 50000 + np.random.normal(0, 100, periods)

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": close_prices * 0.999,
            "high": close_prices * 1.002,
            "low": close_prices * 0.997,
            "close": close_prices,
            "volume": np.random.uniform(100, 150, periods),
        }
    )

    return df


@pytest.fixture
def sample_kline_data_breakout():
    """提供突破形态的 K 线数据."""
    now = datetime.now()
    periods = 50
    timestamps = pd.date_range(start=now - timedelta(hours=1), periods=periods, freq="1min")

    # 前期横盘,后期突破
    base_prices = np.concatenate(
        [
            np.full(30, 50000) + np.random.normal(0, 50, 30),  # 前30根横盘
            np.linspace(50000, 50500, 20),  # 后20根突破上涨
        ]
    )

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": base_prices * 0.999,
            "high": base_prices * 1.002,
            "low": base_prices * 0.997,
            "close": base_prices,
            "volume": np.concatenate(
                [
                    np.random.uniform(100, 150, 30),  # 前期成交量较小
                    np.random.uniform(200, 300, 20),  # 突破时成交量放大
                ]
            ),
        }
    )

    return df
