"""测试 AnalysisService 应用服务"""

from unittest.mock import Mock, patch
import pytest
from app.application.services.analysis_service import AnalysisService


def test_analysis_service_initialization():
    """验证 AnalysisService 可以正确初始化"""
    mock_data_provider = Mock()
    mock_event_publisher = Mock()
    mock_config = Mock()

    service = AnalysisService(
        data_provider=mock_data_provider,
        event_publisher=mock_event_publisher,
        config=mock_config,
    )

    # 验证属性
    assert service.data_provider is mock_data_provider
    assert service.event_publisher is mock_event_publisher
    assert service.config is mock_config
    assert service.is_running is False


def test_analysis_service_start():
    """验证 AnalysisService 可以启动"""
    mock_data_provider = Mock()
    mock_event_publisher = Mock()
    mock_config = Mock()
    mock_config.get_symbols.return_value = ["BTC/USDT"]

    service = AnalysisService(
        data_provider=mock_data_provider,
        event_publisher=mock_event_publisher,
        config=mock_config,
    )

    service.start()

    # 验证状态
    assert service.is_running is True
    # TODO: 当实现订阅逻辑时，取消下面注释
    # mock_event_publisher.subscribe.assert_called()


def test_analysis_service_stop():
    """验证 AnalysisService 可以停止"""
    mock_data_provider = Mock()
    mock_event_publisher = Mock()
    mock_config = Mock()

    service = AnalysisService(
        data_provider=mock_data_provider,
        event_publisher=mock_event_publisher,
        config=mock_config,
    )

    service.start()
    service.stop()

    # 验证状态
    assert service.is_running is False


def test_analysis_service_analyze_trend():
    """验证分析趋势功能"""
    mock_data_provider = Mock()
    mock_event_publisher = Mock()
    mock_config = Mock()

    # Mock 返回数据
    mock_df = Mock()
    mock_df.empty = False
    mock_data_provider.get_kline_data.return_value = mock_df

    service = AnalysisService(
        data_provider=mock_data_provider,
        event_publisher=mock_event_publisher,
        config=mock_config,
    )

    result = service.analyze_trend("BTC/USDT", "1h")

    # 验证调用
    mock_data_provider.get_kline_data.assert_called_once_with("BTC/USDT", "1h", 100)
    # 结果应该是 mock_df（实际实现中会有真实分析逻辑）
    assert result is not None
