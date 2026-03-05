"""测试 RealtimeService 应用服务"""

from unittest.mock import Mock
import pytest
from app.application.services.realtime_service import RealtimeService


def test_realtime_service_initialization():
    """验证 RealtimeService 可以正确初始化"""
    mock_data_provider = Mock()
    mock_event_publisher = Mock()
    mock_config = Mock()

    service = RealtimeService(
        data_provider=mock_data_provider,
        event_publisher=mock_event_publisher,
        config=mock_config,
    )

    # 验证属性
    assert service.data_provider is mock_data_provider
    assert service.event_publisher is mock_event_publisher
    assert service.config is mock_config
    assert service.is_running is False


def test_realtime_service_start():
    """验证 RealtimeService 可以启动"""
    mock_data_provider = Mock()
    mock_event_publisher = Mock()
    mock_config = Mock()
    mock_config.get_symbols.return_value = ["BTC/USDT"]

    service = RealtimeService(
        data_provider=mock_data_provider,
        event_publisher=mock_event_publisher,
        config=mock_config,
    )

    service.start()

    # 验证状态
    assert service.is_running is True


def test_realtime_service_stop():
    """验证 RealtimeService 可以停止"""
    mock_data_provider = Mock()
    mock_event_publisher = Mock()
    mock_config = Mock()

    service = RealtimeService(
        data_provider=mock_data_provider,
        event_publisher=mock_event_publisher,
        config=mock_config,
    )

    service.start()
    service.stop()

    # 验证状态
    assert service.is_running is False


def test_realtime_service_check_signals():
    """验证信号检查功能"""
    mock_data_provider = Mock()
    mock_event_publisher = Mock()
    mock_config = Mock()

    # Mock 价格数据
    mock_data_provider.get_current_price.return_value = 50000.0

    service = RealtimeService(
        data_provider=mock_data_provider,
        event_publisher=mock_event_publisher,
        config=mock_config,
    )

    price = service.check_price("BTC/USDT")

    # 验证调用
    mock_data_provider.get_current_price.assert_called_once_with("BTC/USDT")
    assert price == 50000.0
