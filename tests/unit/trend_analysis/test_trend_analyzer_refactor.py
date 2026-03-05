"""测试 TrendAnalyzer DDD 重构"""

from unittest.mock import Mock, MagicMock
import pytest
import pandas as pd
from app.trend_analysis.trend_analyzer import TrendAnalyzer


def test_trend_analyzer_uses_data_provider():
    """验证 TrendAnalyzer 使用 DataProvider 接口"""
    mock_data_provider = Mock()

    # Mock 数据就绪检查
    mock_data_provider.is_data_ready.return_value = True

    # Mock K线数据
    mock_df = pd.DataFrame({
        "open": [100] * 30,
        "high": [105] * 30,
        "low": [95] * 30,
        "close": [100] * 30,
        "volume": [1000] * 30,
    })
    mock_data_provider.get_kline_data.return_value = mock_df

    analyzer = TrendAnalyzer(data_provider=mock_data_provider)

    # 验证可以调用方法
    assert analyzer.is_ready("BTC/USDT", "5m") is True
    mock_data_provider.is_data_ready.assert_called_once_with("BTC/USDT", "5m")


def test_trend_analyzer_get_kline_through_provider():
    """验证 TrendAnalyzer 通过 DataProvider 获取 K线数据"""
    mock_data_provider = Mock()

    mock_df = pd.DataFrame({
        "open": [100] * 30,
        "high": [105] * 30,
        "low": [95] * 30,
        "close": [100] * 30,
        "volume": [1000] * 30,
    })
    mock_data_provider.get_kline_data.return_value = mock_df

    analyzer = TrendAnalyzer(data_provider=mock_data_provider)

    # 调用分析方法
    result = analyzer.analyze_trend("BTC/USDT", bar="5m")

    # 验证通过 provider 获取数据
    mock_data_provider.get_kline_data.assert_called()
    # 注意：由于模型可能不返回结果，result 可能为 None
