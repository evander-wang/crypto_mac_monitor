"""测试 YamlConfigProvider 实现"""

import pytest
from app.infrastructure.config.yaml_provider import YamlConfigProvider


def test_yaml_config_provider_get_symbols():
    """验证可以获取交易对列表"""
    provider = YamlConfigProvider()
    symbols = provider.get_symbols()
    assert isinstance(symbols, list)
    assert len(symbols) > 0
    # 默认配置包含 BTC-USDT-SWAP 和 ETH-USDT-SWAP
    assert any("BTC" in s for s in symbols)


def test_yaml_config_provider_get_timeframes():
    """验证可以获取时间周期配置"""
    provider = YamlConfigProvider()
    timeframes = provider.get_timeframes()
    assert isinstance(timeframes, dict)
    assert "5m" in timeframes
    assert "1h" in timeframes


def test_yaml_config_provider_get_trend_min_confidence():
    """验证可以获取趋势最小置信度"""
    provider = YamlConfigProvider()
    confidence_5m = provider.get_trend_min_confidence("5m")
    assert isinstance(confidence_5m, float)
    assert 0.0 <= confidence_5m <= 1.0

    confidence_1h = provider.get_trend_min_confidence("1h")
    assert isinstance(confidence_1h, float)
    assert 0.0 <= confidence_1h <= 1.0
