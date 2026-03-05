"""测试 EventPublisher 接口定义"""

import pytest

from app.domain.events.publisher import EventPublisher


def test_event_publisher_is_abstract():
    """验证 EventPublisher 是抽象类"""
    with pytest.raises(TypeError):
        EventPublisher()


def test_event_publisher_has_required_methods():
    """验证必需方法存在"""
    abstract_methods = EventPublisher.__abstractmethods__
    assert "publish_ui" in abstract_methods
    assert "publish_alert" in abstract_methods
    assert "subscribe" in abstract_methods
