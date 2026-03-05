"""
ThreadMemoryDataCacheManager 单元测试.

测试基于 cachetools 的内存缓存管理器,包括:
- K 线数据存储和获取
- Ticker 数据存储和获取
- 数据新鲜度检查
- 缓存合并
- 线程安全性
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import time

import numpy as np
import pandas as pd
import pytest

from app.data_manager.thread_memory_data_cache_manager import ThreadMemoryDataCacheManager
from app.models.dto import ReturnTickerDTO


class TestCacheManagerInit:
    """测试缓存管理器初始化."""

    def test_init_with_config(self, mock_config_manager):
        """测试使用配置初始化."""
        manager = ThreadMemoryDataCacheManager(mock_config_manager)

        assert manager.config_manager == mock_config_manager
        assert manager._lock is not None
        assert manager._kline_cache is not None
        assert manager._ticker_cache is not None
        assert manager._trend_cache is not None

    def test_cache_configuration(self, cache_manager):
        """测试缓存配置."""
        # 验证缓存大小和 TTL
        assert cache_manager._kline_cache.maxsize == 100
        assert cache_manager._kline_cache.ttl == 300
        assert cache_manager._ticker_cache.maxsize == 50  # max_size // 2
        assert cache_manager._ticker_cache.ttl == 300


class TestKlineDataOperations:
    """测试 K 线数据操作."""

    def test_put_kline_data_success(self, cache_manager, sample_kline_data):
        """测试成功存储 K 线数据."""
        result = cache_manager.put_kline_data("BTC-USDT-SWAP", "5m", sample_kline_data)

        assert result is True
        # 验证数据已缓存
        cached_data = cache_manager.get_kline_data("BTC-USDT-SWAP", "5m")
        assert cached_data is not None
        assert len(cached_data) == len(sample_kline_data)

    def test_put_kline_data_empty_dataframe(self, cache_manager):
        """测试存储空的 DataFrame."""
        empty_df = pd.DataFrame()
        result = cache_manager.put_kline_data("BTC-USDT-SWAP", "5m", empty_df)

        assert result is False

    def test_put_kline_data_none(self, cache_manager):
        """测试存储 None 数据."""
        result = cache_manager.put_kline_data("BTC-USDT-SWAP", "5m", None)

        assert result is False

    def test_put_kline_data_merge_existing(self, cache_manager, sample_kline_data):
        """测试合并已存在的 K 线数据."""
        # 第一次存储
        cache_manager.put_kline_data("BTC-USDT-SWAP", "5m", sample_kline_data.iloc[:30])

        # 第二次存储更多数据
        cache_manager.put_kline_data("BTC-USDT-SWAP", "5m", sample_kline_data.iloc[30:])

        # 验证数据已合并
        cached_data = cache_manager.get_kline_data("BTC-USDT-SWAP", "5m")
        assert cached_data is not None
        assert len(cached_data) == 50

    def test_get_kline_data_success(self, cache_manager, sample_kline_data):
        """测试成功获取 K 线数据."""
        cache_manager.put_kline_data("BTC-USDT-SWAP", "5m", sample_kline_data)

        result = cache_manager.get_kline_data("BTC-USDT-SWAP", "5m")

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 50
        assert "timestamp" in result.columns
        assert "close" in result.columns

    def test_get_kline_data_not_found(self, cache_manager):
        """测试获取不存在的 K 线数据."""
        result = cache_manager.get_kline_data("NON-EXISTENT", "5m")

        assert result is None

    def test_get_kline_data_with_limit(self, cache_manager, sample_kline_data):
        """测试限制返回数量的 K 线数据."""
        cache_manager.put_kline_data("BTC-USDT-SWAP", "5m", sample_kline_data)

        result = cache_manager.get_kline_data("BTC-USDT-SWAP", "5m", limit=10)

        assert result is not None
        assert len(result) == 10

    def test_get_kline_data_with_limit_larger_than_cached(self, cache_manager, sample_kline_data):
        """测试请求数量大于缓存数量."""
        cache_manager.put_kline_data("BTC-USDT-SWAP", "5m", sample_kline_data)

        result = cache_manager.get_kline_data("BTC-USDT-SWAP", "5m", limit=100)

        assert result is not None
        assert len(result) == 50  # 返回所有缓存的数据


class TestTickerDataOperations:
    """测试 Ticker 数据操作."""

    def test_put_ticker_data_from_dict(self, cache_manager):
        """测试从字典存储 Ticker 数据."""
        ticker_dict = {
            "instId": "BTC-USDT-SWAP",
            "last": "50000",
            "open24h": "49500",
            "high24h": "51000",
            "low24h": "49000",
            "volCcy24h": "1000",
            "vol24h": "50000000",
            "ts": "1705123456789",
        }

        result = cache_manager.put_ticker_data("BTC-USDT-SWAP", ticker_dict)

        assert result is True

    def test_put_ticker_data_from_dto(self, cache_manager, sample_ticker_dto):
        """测试从 DTO 存储 Ticker 数据."""
        result = cache_manager.put_ticker_data("BTC-USDT-SWAP", sample_ticker_dto)

        assert result is True

    def test_get_ticker_data_success(self, cache_manager, sample_ticker_dto):
        """测试成功获取 Ticker 数据."""
        cache_manager.put_ticker_data("BTC-USDT-SWAP", sample_ticker_dto)

        result = cache_manager.get_ticker_data("BTC-USDT-SWAP")

        assert result is not None
        assert result.symbol == "BTC-USDT-SWAP"
        assert result.last == 50000.0

    def test_get_ticker_data_not_found(self, cache_manager):
        """测试获取不存在的 Ticker 数据."""
        result = cache_manager.get_ticker_data("NON-EXISTENT")

        assert result is None

    def test_get_ticker_data_returns_copy(self, cache_manager, sample_ticker_dto):
        """测试获取的是数据的副本,不是引用."""
        cache_manager.put_ticker_data("BTC-USDT-SWAP", sample_ticker_dto)

        ticker1 = cache_manager.get_ticker_data("BTC-USDT-SWAP")
        ticker2 = cache_manager.get_ticker_data("BTC-USDT-SWAP")

        # 修改其中一个不应该影响另一个
        ticker1.last = 60000.0

        assert ticker2.last == 50000.0


class TestDataFreshness:
    """测试数据新鲜度检查."""

    def test_is_data_fresh_cached(self, cache_manager, sample_kline_data):
        """测试缓存中的数据被认为是新鲜的."""
        cache_manager.put_kline_data("BTC-USDT-SWAP", "5m", sample_kline_data)

        result = cache_manager.is_data_fresh("BTC-USDT-SWAP", "5m")

        assert result is True

    def test_is_data_fresh_not_cached(self, cache_manager):
        """测试未缓存的数据被认为是不新鲜的."""
        result = cache_manager.is_data_fresh("NON-EXISTENT", "5m")

        assert result is False

    def test_is_ticker_fresh_cached(self, cache_manager, sample_ticker_dto):
        """测试缓存中的 ticker 是新鲜的."""
        cache_manager.put_ticker_data("BTC-USDT-SWAP", sample_ticker_dto)

        result = cache_manager.is_ticker_fresh("BTC-USDT-SWAP")

        assert result is True

    def test_is_ticker_fresh_not_cached(self, cache_manager):
        """测试未缓存的 ticker 是不新鲜的."""
        result = cache_manager.is_ticker_fresh("NON-EXISTENT")

        assert result is False

    def test_is_kline_data_ready_with_enough_data(self, cache_manager, sample_kline_data):
        """测试有足够数据时返回 True."""
        cache_manager.put_kline_data("BTC-USDT-SWAP", "5m", sample_kline_data)

        result = cache_manager.is_kline_data_ready("BTC-USDT-SWAP", "5m", min_periods=30)

        assert result is True

    def test_is_kline_data_ready_not_enough_data(self, cache_manager, sample_kline_data):
        """测试数据不足时返回 False."""
        cache_manager.put_kline_data("BTC-USDT-SWAP", "5m", sample_kline_data)

        result = cache_manager.is_kline_data_ready("BTC-USDT-SWAP", "5m", min_periods=100)

        assert result is False

    def test_is_kline_data_ready_no_data(self, cache_manager):
        """测试无数据时返回 False."""
        result = cache_manager.is_kline_data_ready("NON-EXISTENT", "5m")

        assert result is False


class TestDataInfo:
    """测试数据信息获取."""

    def test_get_data_info_cached(self, cache_manager, sample_kline_data):
        """测试获取缓存数据的信息."""
        cache_manager.put_kline_data("BTC-USDT-SWAP", "5m", sample_kline_data)

        info = cache_manager.get_data_info("BTC-USDT-SWAP", "5m")

        assert info["symbol"] == "BTC-USDT-SWAP"
        assert info["timeframe"] == "5m"
        assert info["data_count"] == 50
        assert info["cached"] is True
        assert "timestamp" in info["columns"]

    def test_get_data_info_not_cached(self, cache_manager):
        """测试获取未缓存数据的信息."""
        info = cache_manager.get_data_info("NON-EXISTENT", "5m")

        assert info["symbol"] == "NON-EXISTENT"
        assert info["timeframe"] == "5m"
        assert info["data_count"] == 0
        assert info["cached"] is False

    def test_get_cache_info(self, cache_manager, sample_kline_data, sample_ticker_dto):
        """测试获取缓存详细信息."""
        cache_manager.put_kline_data("BTC-USDT-SWAP", "5m", sample_kline_data)
        cache_manager.put_ticker_data("BTC-USDT-SWAP", sample_ticker_dto)

        info = cache_manager.get_cache_info()

        assert "kline_cache" in info
        assert "ticker_cache" in info
        assert info["kline_cache"]["size"] == 1
        assert info["ticker_cache"]["size"] == 1


class TestCacheCleanup:
    """测试缓存清理."""

    def test_cleanup_stops_timer(self, cache_manager):
        """测试清理操作停止定时器."""
        # 启动定时器
        cache_manager._start_info_timer()
        assert cache_manager._info_timer is not None

        # 清理
        cache_manager.cleanup()

        # 验证定时器已停止
        assert cache_manager._info_timer is None or not cache_manager._info_timer.is_alive()


class TestThreadSafety:
    """测试线程安全性."""

    def test_concurrent_put_operations(self, cache_manager, sample_kline_data):
        """测试并发写入操作的线程安全."""
        import threading

        errors = []

        def put_data():
            try:
                for i in range(10):
                    cache_manager.put_kline_data(f"SYMBOL-{i}", "5m", sample_kline_data)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=put_data) for _ in range(3)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=5)

        assert len(errors) == 0

    def test_concurrent_get_operations(self, cache_manager, sample_kline_data):
        """测试并发读取操作的线程安全."""
        import threading

        cache_manager.put_kline_data("BTC-USDT-SWAP", "5m", sample_kline_data)

        results = []
        errors = []

        def get_data():
            try:
                for i in range(10):
                    data = cache_manager.get_kline_data("BTC-USDT-SWAP", "5m")
                    results.append(data is not None)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_data) for _ in range(3)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=5)

        assert len(errors) == 0
        assert all(results)  # 所有读取都应该成功
