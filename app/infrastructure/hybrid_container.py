"""
Hybrid Container - 混合容器

过渡方案：新 DDD 架构 + 旧组件兼容层
用于渐进式迁移入口点。
"""

from app.infrastructure.container import InfrastructureContainer


class HybridContainer:
    """
    混合容器

    提供新旧组件的统一访问接口，支持渐进式迁移。
    """

    def __init__(self, config_file: str = None):
        """
        初始化混合容器

        Args:
            config_file: 配置文件路径
        """
        # 新 DDD 架构容器
        self.infrastructure = InfrastructureContainer()

        # 旧容器组件（延迟导入避免循环依赖）
        self._old_container = None

    @property
    def old_container(self):
        """获取旧容器（懒加载）"""
        if self._old_container is None:
            from app.core.di_container import BaseContainer, ComponentManager, DIContainerManager

            self._old_container = DIContainerManager()
        return self._old_container

    # 新架构组件访问
    def config(self):
        """获取配置提供者（新架构）"""
        return self.infrastructure.config()

    def data_provider(self):
        """获取数据提供者（新架构）"""
        return self.infrastructure.data_provider()

    def event_publisher(self):
        """获取事件发布者（新架构）"""
        return self.infrastructure.event_publisher()

    def application(self):
        """获取应用门面（新架构）"""
        return self.infrastructure.application()

    # 旧组件访问（兼容层）
    def get_old_component(self, component_name: str):
        """
        获取旧组件（兼容层）

        Args:
            component_name: 组件名称

        Returns:
            组件实例
        """
        return self.old_container.get_component(component_name)

    # 便捷方法
    def get_symbols(self):
        """获取交易对列表"""
        return self.config().get_symbols()

    def get_current_price(self, symbol: str):
        """获取当前价格"""
        return self.application().get_current_price(symbol)
