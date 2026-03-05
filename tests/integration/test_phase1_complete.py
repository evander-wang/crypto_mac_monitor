"""阶段 1 完成检查 - 验证基础层建立"""

from app.infrastructure.container import InfrastructureContainer
from app.domain.repositories import DataProvider, ConfigProvider
from app.domain.events import EventPublisher


def test_phase1_container_exists():
    """验证容器可以创建"""
    container = InfrastructureContainer()
    assert container is not None


def test_phase1_interfaces_defined():
    """验证所有领域接口已定义"""
    # DataProvider
    assert hasattr(DataProvider, "__abstractmethods__")
    assert "get_kline_data" in DataProvider.__abstractmethods__

    # ConfigProvider
    assert hasattr(ConfigProvider, "__abstractmethods__")
    assert "get_symbols" in ConfigProvider.__abstractmethods__

    # EventPublisher
    assert hasattr(EventPublisher, "__abstractmethods__")
    assert "publish_ui" in EventPublisher.__abstractmethods__


def test_phase1_factory_functions_exist():
    """验证工厂函数存在"""
    from app.infrastructure.factory import (
        create_data_provider,
        create_event_publisher,
        create_application,
    )

    assert callable(create_data_provider)
    assert callable(create_event_publisher)
    assert callable(create_application)


def test_phase1_no_implementation_yet():
    """验证实现尚未完成（按计划）"""
    from app.infrastructure.factory import (
        create_data_provider,
        create_event_publisher,
        create_application,
    )
    import pytest

    with pytest.raises(NotImplementedError):
        create_data_provider(None)

    with pytest.raises(NotImplementedError):
        create_event_publisher(None)

    with pytest.raises(NotImplementedError):
        create_application(None, None, None)
