"""测试 Application 门面"""

from unittest.mock import Mock
import pytest
from app.application.application import Application


def test_application_initialization():
    """验证 Application 可以正确初始化"""
    # 创建 mock 依赖
    mock_data_provider = Mock()
    mock_event_publisher = Mock()
    mock_config = Mock()

    # 创建 Application
    app = Application(
        data_provider=mock_data_provider,
        event_publisher=mock_event_publisher,
        config=mock_config,
    )

    # 验证属性
    assert app.data_provider is mock_data_provider
    assert app.event_publisher is mock_event_publisher
    assert app.config is mock_config


def test_application_has_services():
    """验证 Application 包含服务"""
    mock_data_provider = Mock()
    mock_event_publisher = Mock()
    mock_config = Mock()

    app = Application(
        data_provider=mock_data_provider,
        event_publisher=mock_event_publisher,
        config=mock_config,
    )

    # 验证服务属性存在
    assert hasattr(app, "analysis")
    assert hasattr(app, "realtime")


def test_application_start_stop():
    """验证 Application 可以启动和停止"""
    mock_data_provider = Mock()
    mock_event_publisher = Mock()
    mock_config = Mock()

    # 创建 mock 服务
    mock_analysis_service = Mock()
    mock_realtime_service = Mock()

    app = Application(
        data_provider=mock_data_provider,
        event_publisher=mock_event_publisher,
        config=mock_config,
    )
    app.analysis = mock_analysis_service
    app.realtime = mock_realtime_service

    # 调用 start 和 stop
    app.start()
    mock_analysis_service.start.assert_called_once()
    mock_realtime_service.start.assert_called_once()

    app.stop()
    mock_analysis_service.stop.assert_called_once()
    mock_realtime_service.stop.assert_called_once()
