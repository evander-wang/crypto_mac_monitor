"""测试 DataProvider 接口定义"""

from abc import ABC

import pytest

from app.domain.repositories.data_provider import DataProvider


def test_data_provider_is_abstract():
    """验证 DataProvider 是抽象类，无法直接实例化"""
    with pytest.raises(TypeError):
        DataProvider()


def test_data_provider_has_required_methods():
    """验证 DataProvider 定义了必需的方法"""
    abstract_methods = DataProvider.__abstractmethods__
    assert "get_kline_data" in abstract_methods
    assert "get_current_price" in abstract_methods
    assert "is_data_ready" in abstract_methods


def test_data_provider_method_signatures():
    """验证方法签名正确"""
    import inspect

    # get_kline_data
    sig = inspect.signature(DataProvider.get_kline_data)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "symbol" in params
    assert "timeframe" in params
    assert "limit" in params

    # get_current_price
    sig = inspect.signature(DataProvider.get_current_price)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "symbol" in params

    # is_data_ready
    sig = inspect.signature(DataProvider.is_data_ready)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "symbol" in params
    assert "timeframe" in params
