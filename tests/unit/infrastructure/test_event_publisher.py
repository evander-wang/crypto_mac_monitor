"""测试 EventBusPublisher 实现"""

from unittest.mock import Mock, MagicMock
import pytest
from app.infrastructure.events.publisher import EventBusPublisher


def test_event_publisher_publish_ui():
    """验证可以发布到 UI 线程"""
    # Mock UIEventBridge
    mock_config = Mock()
    publisher = EventBusPublisher(mock_config)
    publisher.ui_bridge = Mock()
    publisher.ui_bridge.publish_to_ui = Mock()

    # 发布事件
    publisher.publish_ui("test_event", {"data": "test"})

    # 验证调用了桥接器
    publisher.ui_bridge.publish_to_ui.assert_called_once_with("test_event", {"data": "test"})


def test_event_publisher_publish_alert():
    """验证可以发布到告警线程"""
    # Mock AlertEventBridge
    mock_config = Mock()
    publisher = EventBusPublisher(mock_config)
    publisher.alert_bridge = Mock()
    publisher.alert_bridge.publish_to_alerts = Mock()

    # 发布事件
    publisher.publish_alert("test_alert", {"alert": "data"})

    # 验证调用了桥接器
    publisher.alert_bridge.publish_to_alerts.assert_called_once_with("test_alert", {"alert": "data"})


def test_event_publisher_subscribe():
    """验证可以订阅事件"""
    mock_config = Mock()
    publisher = EventBusPublisher(mock_config)
    publisher.analysis_bus = Mock()
    publisher.analysis_bus.on = Mock(return_value=lambda callback: None)

    # 订阅事件
    handler = lambda data: None
    publisher.subscribe("test_event", handler)

    # 验证调用了总线订阅
    publisher.analysis_bus.on.assert_called_once_with("test_event", handler)
