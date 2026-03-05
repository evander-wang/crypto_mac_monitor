"""测试 ConfigProvider 接口定义"""

import pytest
from app.domain.repositories.config_provider import ConfigProvider


def test_config_provider_is_abstract():
    """验证 ConfigProvider 是抽象类"""
    with pytest.raises(TypeError):
        ConfigProvider()


def test_config_provider_has_required_methods():
    """验证必需方法存在"""
    abstract_methods = ConfigProvider.__abstractmethods__
    assert "get_symbols" in abstract_methods
    assert "get_timeframes" in abstract_methods
    assert "get_trend_min_confidence" in abstract_methods
