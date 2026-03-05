"""测试工厂函数"""

from app.infrastructure.factory import (
    create_application,
    create_data_provider,
    create_event_publisher,
)


def test_factory_functions_exist():
    """验证工厂函数存在且可调用"""
    assert callable(create_data_provider)
    assert callable(create_event_publisher)
    assert callable(create_application)


def test_factory_functions_have_docstrings():
    """验证工厂函数有文档字符串"""
    assert create_data_provider.__doc__ is not None
    assert create_event_publisher.__doc__ is not None
    assert create_application.__doc__ is not None
