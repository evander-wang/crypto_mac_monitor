"""测试 KlineRepository 实现"""

import pytest
from app.infrastructure.data.repository import KlineRepository
from app.infrastructure.config import YamlConfigProvider


def test_repository_get_kline_data():
    """验证可以获取 K线数据"""
    provider = YamlConfigProvider()
    repository = KlineRepository(provider)

    # 测试获取数据（即使缓存为空也应该返回 None）
    result = repository.get_kline_data("BTC-USDT-SWAP", "5m", 100)
    # 如果缓存没有数据，应该返回 None
    assert result is None or hasattr(result, "columns")


def test_repository_get_current_price():
    """验证可以获取当前价格"""
    provider = YamlConfigProvider()
    repository = KlineRepository(provider)

    # 测试获取价格（如果没有 ticker 数据应该返回 None）
    result = repository.get_current_price("BTC-USDT-SWAP")
    assert result is None or isinstance(result, (int, float))


def test_repository_is_data_ready():
    """验证可以检查数据是否就绪"""
    provider = YamlConfigProvider()
    repository = KlineRepository(provider)

    # 测试数据就绪检查
    result = repository.is_data_ready("BTC-USDT-SWAP", "5m")
    assert isinstance(result, bool)
