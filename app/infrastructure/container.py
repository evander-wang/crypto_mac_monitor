"""
Infrastructure Container - 基础设施容器

简化的 DI 容器，只管理基础设施组件的创建。
使用命名工厂函数代替 lambda。
"""

from dependency_injector import containers, providers

from app.infrastructure.config import YamlConfigProvider
from app.infrastructure.factory import (
    create_data_provider,
    create_event_publisher,
    create_application,
)


class InfrastructureContainer(containers.DeclarativeContainer):
    """
    基础设施容器

    职责：
    - 只管理基础设施组件（Config, DataProvider, EventPublisher）
    - 使用命名工厂函数组合 Application
    - 不知晓应用层或领域层的业务逻辑
    """

    # 配置提供者 - 单例
    config = providers.Singleton(YamlConfigProvider)

    # 数据提供者 - 使用命名函数
    data_provider = providers.Factory(
        create_data_provider,
        config_provider=config,
    )

    # 事件发布者 - 使用命名函数
    event_publisher = providers.Factory(
        create_event_publisher,
        config_provider=config,
    )

    # 应用层实例 - 使用命名函数组合
    application = providers.Factory(
        create_application,
        data_provider=data_provider,
        event_publisher=event_publisher,
        config_provider=config,
    )
