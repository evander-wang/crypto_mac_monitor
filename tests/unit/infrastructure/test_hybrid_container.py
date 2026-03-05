"""测试 HybridContainer 混合容器"""

from unittest.mock import Mock, patch
import pytest
from app.infrastructure.hybrid_container import HybridContainer


def test_hybrid_container_initialization():
    """验证混合容器可以正确初始化"""
    container = HybridContainer()
    assert container.infrastructure is not None
    assert container._old_container is None  # 懒加载


def test_hybrid_container_new_components():
    """验证可以访问新架构组件"""
    container = HybridContainer()

    # 获取配置提供者
    config = container.config()
    assert config is not None

    # 获取应用门面
    application = container.application()
    assert application is not None


def test_hybrid_container_symbols():
    """验证可以获取交易对列表"""
    container = HybridContainer()
    symbols = container.get_symbols()
    assert isinstance(symbols, list)
    assert len(symbols) > 0


@patch("app.core.di_container.DIContainerManager")
def test_hybrid_container_old_components(mock_old_container_cls):
    """验证可以访问旧组件（兼容层）"""
    # Mock 旧容器
    mock_old_container = Mock()
    mock_component = Mock()
    mock_old_container.get_component.return_value = mock_component
    mock_old_container_cls.return_value = mock_old_container

    container = HybridContainer()

    # 访问旧组件（触发懒加载）
    _ = container.old_container

    # 验证旧容器被创建
    mock_old_container_cls.assert_called_once()
