"""
Factory Functions - 命名工厂函数

使用命名函数替代 lambda，提供清晰的组件创建逻辑。
"""

from app.domain.events import EventPublisher
from app.domain.repositories import ConfigProvider, DataProvider


def create_data_provider(config_provider: ConfigProvider) -> DataProvider:
    """
    创建数据提供者

    Args:
        config_provider: 配置提供者

    Returns:
        DataProvider 实例
    """
    # TODO: Task 2.x 实现 KlineRepository
    raise NotImplementedError("To be implemented in Task 2.x")


def create_event_publisher(config_provider: ConfigProvider) -> EventPublisher:
    """
    创建事件发布者

    Args:
        config_provider: 配置提供者

    Returns:
        EventPublisher 实例
    """
    # TODO: Task 2.x 实现 EventBusPublisher
    raise NotImplementedError("To be implemented in Task 2.x")


def create_application(
    data_provider: DataProvider,
    event_publisher: EventPublisher,
    config_provider: ConfigProvider,
) -> object:
    """
    创建应用层实例

    这是关键的组合点，将所有依赖组装成 Application。

    Args:
        data_provider: 数据提供者
        event_publisher: 事件发布者
        config_provider: 配置提供者

    Returns:
        Application 实例（TODO: Task 3.x 实现）
    """
    # TODO: Task 3.x 实现 Application 类
    raise NotImplementedError("To be implemented in Task 3.x")
