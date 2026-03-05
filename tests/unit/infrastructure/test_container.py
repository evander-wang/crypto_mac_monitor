"""测试基础设施容器"""

import pytest
from app.infrastructure.container import InfrastructureContainer


def test_container_has_config_provider():
    """验证容器有 config 提供者"""
    container = InfrastructureContainer()
    assert hasattr(container, "config")
    assert callable(container.config)


def test_container_has_data_provider():
    """验证容器有 data_provider"""
    container = InfrastructureContainer()
    assert hasattr(container, "data_provider")
    assert callable(container.data_provider)


def test_container_has_event_publisher():
    """验证容器有 event_publisher"""
    container = InfrastructureContainer()
    assert hasattr(container, "event_publisher")
    assert callable(container.event_publisher)


def test_container_has_application():
    """验证容器有 application"""
    container = InfrastructureContainer()
    assert hasattr(container, "application")
    assert callable(container.application)
