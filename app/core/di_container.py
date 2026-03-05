from app.data_manager import DataScheduler


"""
独立的依赖注入容器管理模块

该模块提供通用的依赖注入容器管理功能，不与任何特定的应用类绑定。
支持容器的创建、初始化、组件管理和清理等核心功能。
"""

from typing import Any, Dict, Optional, Type
import threading

from cachetools import TTLCache
from dependency_injector import containers, providers
from pyee import EventEmitter

from app.analysis.realtime_analysis import RealtimeAnalysis
from app.analysis.trend_analysis import TrendAnalysis
from app.config.config_manager import get_config_manager
from app.consts.consts import (
    COMPONENTS_ALERT_MANAGER,
    COMPONENTS_ANALYSIS_CACHE,
    COMPONENTS_ANALYSIS_RUNNER,
    COMPONENTS_CACHE_LOCK,
    COMPONENTS_CONFIG,
    COMPONENTS_DATA_MANAGER,
    COMPONENTS_EVENT_BUS,
    COMPONENTS_LIMIT_ORDER_SERVICE,
    COMPONENTS_NOTIFICATION_MANAGER,
    COMPONENTS_ORDER_MANAGER,
    COMPONENTS_POSITION_MANAGER,
    COMPONENTS_REALTIME_HELPER,
    COMPONENTS_THREAD_MEMORY_DATA_CACHE_MANAGER,
    COMPONENTS_TREND_ANALYZER,
)
from app.data_manager import EventDrivenDataManager, ThreadMemoryDataCacheManager
from app.notifications_v2 import NotificationManager
from app.notifications_v2.channels.channel_manager import ChannelManager
from app.trading.limit_order_service import LimitOrderService
from app.trading.order_manager import OrderManager
from app.trading.position_manager import PositionManager
from app.trend_analysis import TrendAnalyzer
from app.utils import log_error, log_info, log_success
from daemon_alerts.event_alert_manager import EventDrivenAlertManager


class BaseContainer(containers.DeclarativeContainer):
    """基础依赖注入容器，定义核心组件"""

    # 配置管理器
    config_manager = providers.Singleton(get_config_manager)

    # 配置工厂
    config = providers.Factory(lambda config_manager: config_manager, config_manager=config_manager)

    # 事件总线
    event_bus = providers.Singleton(EventEmitter)

    # 缓存系统
    analysis_cache = providers.Singleton(TTLCache, maxsize=100, ttl=300)
    cache_lock = providers.Singleton(threading.RLock)

    # 全局内存数据缓存管理器
    thread_memory_data_cache_manager = providers.Singleton(ThreadMemoryDataCacheManager, config_manager=config_manager)

    # 通知系统（优先从配置文件加载，失败则退回默认配置）
    notification_config = providers.Singleton(
        lambda config_manager: config_manager.get_notification_v2_config(),
        config_manager=config_manager,
    )

    # 通知渠道
    channel_manager = providers.Singleton(ChannelManager, config=notification_config)

    # 通知管理器
    notification_manager = providers.Singleton(NotificationManager, channel_manager=channel_manager)

    # 数据调度器
    data_scheduler = providers.Singleton(
        DataScheduler,
        cache_manager=thread_memory_data_cache_manager,
        config_manager=config_manager,
        notification_manager=notification_manager,
    )

    # 数据管理器
    data_manager = providers.Singleton(
        EventDrivenDataManager,
        config_manager=config_manager,
        cache_manager=thread_memory_data_cache_manager,
        scheduler=data_scheduler,
        notification_manager=notification_manager,
    )

    # 告警系统
    alert_manager = providers.Singleton(EventDrivenAlertManager, notification_manager=notification_manager)

    # 趋势分析器
    trend_analyzer = providers.Singleton(TrendAnalyzer, data_manager=data_manager)

    # 分析运行器
    analysis_runner = providers.Singleton(
        TrendAnalysis,
        trend_analyzer=trend_analyzer,
        config_manager=config_manager,
        symbol_names=providers.Factory(
            lambda data_manager: data_manager.get_supported_symbols(),
            data_manager=data_manager,
        ),
    )

    # 实时助手（注入通知管理器用于指标告警）
    realtime_helper = providers.Singleton(
        RealtimeAnalysis,
        trend_analyzer=trend_analyzer,
        notification_manager=notification_manager,
        config_manager=config_manager,
    )

    # 订单管理器（使用数据调度器的交易所实例）
    order_manager = providers.Singleton(
        OrderManager,
        exchange=providers.Factory(lambda data_scheduler: data_scheduler.exchange, data_scheduler=data_scheduler),
        update_interval=30,  # 30秒更新间隔
    )

    # 仓位管理器（使用数据调度器的交易所实例）
    position_manager = providers.Singleton(
        PositionManager,
        exchange=providers.Factory(lambda data_scheduler: data_scheduler.exchange, data_scheduler=data_scheduler),
        update_interval=5,  # 30秒更新间隔
    )

    # 限价卖出服务（使用数据调度器的交易所实例）
    limit_order_service = providers.Singleton(
        LimitOrderService,
        exchange=providers.Factory(lambda data_scheduler: data_scheduler.exchange, data_scheduler=data_scheduler),
    )


class ComponentManager:
    """组件管理器，负责组件的初始化和清理"""

    def __init__(self, container: BaseContainer):
        self.container = container
        self.components: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def initialize_core_components(self) -> Dict[str, Any]:
        """初始化核心组件"""
        with self._lock:
            try:
                # 初始化事件总线
                self.components[COMPONENTS_EVENT_BUS] = self.container.event_bus()
                log_success("事件总线初始化成功", "DI_CONTAINER")

                # 初始化配置
                self.components[COMPONENTS_CONFIG] = self.container.config()
                log_success("配置系统初始化成功", "DI_CONTAINER")

                # 初始化缓存
                self.components[COMPONENTS_ANALYSIS_CACHE] = self.container.analysis_cache()
                log_success("缓存系统初始化成功", "DI_CONTAINER")

                # 初始化缓存锁
                self.components[COMPONENTS_CACHE_LOCK] = self.container.cache_lock()
                log_success("缓存锁初始化成功", "DI_CONTAINER")

                # 初始化数据管理器
                self.components[COMPONENTS_DATA_MANAGER] = self.container.data_manager()
                log_success("事件驱动数据管理器初始化成功", "DI_CONTAINER")

                # 初始化通知系统
                self.components[COMPONENTS_NOTIFICATION_MANAGER] = self.container.notification_manager()
                log_success("通知系统V2初始化成功", "DI_CONTAINER")

                # 初始化告警系统
                self.components[COMPONENTS_ALERT_MANAGER] = self.container.alert_manager()
                log_success("事件驱动告警管理器初始化成功", "DI_CONTAINER")

                # 初始化趋势分析器
                self.components[COMPONENTS_TREND_ANALYZER] = self.container.trend_analyzer()
                log_success("趋势分析器初始化成功", "DI_CONTAINER")

                # 初始化实时助手
                self.components[COMPONENTS_REALTIME_HELPER] = self.container.realtime_helper()
                log_success("实时助手初始化成功", "DI_CONTAINER")

                # 初始化分析运行器
                self.components[COMPONENTS_ANALYSIS_RUNNER] = self.container.analysis_runner()
                log_success("分析运行器初始化成功", "DI_CONTAINER")

                # 初始化全局内存数据缓存管理器
                self.components[COMPONENTS_THREAD_MEMORY_DATA_CACHE_MANAGER] = self.container.thread_memory_data_cache_manager()
                log_success("全局内存数据缓存管理器初始化成功", "DI_CONTAINER")

                # 初始化订单管理器
                self.components[COMPONENTS_ORDER_MANAGER] = self.container.order_manager()
                log_success("订单管理器初始化成功", "DI_CONTAINER")

                # 初始化仓位管理器
                self.components[COMPONENTS_POSITION_MANAGER] = self.container.position_manager()
                log_success("仓位管理器初始化成功", "DI_CONTAINER")

                # 初始化限价卖出服务
                self.components[COMPONENTS_LIMIT_ORDER_SERVICE] = self.container.limit_order_service()
                log_success("限价卖出服务初始化成功", "DI_CONTAINER")

                log_success("核心组件初始化完成", "DI_CONTAINER")
                return self.components.copy()

            except Exception as e:
                log_error(f"核心组件初始化失败: {e}", "DI_CONTAINER")
                raise

    def get_component(self, component_name: str) -> Optional[Any]:
        """获取指定组件"""
        return self.components.get(component_name)

    def add_component(self, component_name: str, component: Any) -> None:
        """添加组件"""
        with self._lock:
            self.components[component_name] = component
            log_info(f"组件 {component_name} 已添加", "DI_CONTAINER")

    def cleanup_components(self) -> None:
        """清理所有组件资源"""
        cleanup_order = [
            COMPONENTS_ORDER_MANAGER,
            COMPONENTS_ANALYSIS_RUNNER,
            COMPONENTS_ALERT_MANAGER,
            COMPONENTS_TREND_ANALYZER,
            COMPONENTS_DATA_MANAGER,
            COMPONENTS_NOTIFICATION_MANAGER,
        ]

        for component_name in cleanup_order:
            if component_name in self.components:
                component = self.components[component_name]
                try:
                    if hasattr(component, "stop"):
                        component.stop()
                        log_info(f"{component_name} 已停止", "DI_CONTAINER")
                    elif hasattr(component, "cleanup"):
                        component.cleanup()
                        log_info(f"{component_name} 已清理", "DI_CONTAINER")
                except Exception as e:
                    log_error(f"清理 {component_name} 失败: {e}", "DI_CONTAINER")

        self.components.clear()
        log_success("组件清理完成", "DI_CONTAINER")


class DIContainerManager:
    """依赖注入容器管理器"""

    def __init__(self, container_class: Type[BaseContainer] = BaseContainer):
        self.container_class = container_class
        self.container: Optional[BaseContainer] = None
        self.component_manager: Optional[ComponentManager] = None
        self._initialized = False

    def create_container(self) -> BaseContainer:
        """创建并配置依赖注入容器"""
        if self.container is not None:
            log_info("容器已存在，返回现有容器", "DI_CONTAINER")
            return self.container

        self.container = self.container_class()
        self.container.wire(modules=[__name__])
        self.component_manager = ComponentManager(self.container)

        log_success("依赖注入容器创建成功", "DI_CONTAINER")
        return self.container

    def initialize(self) -> Dict[str, Any]:
        """初始化容器和核心组件"""
        if self._initialized:
            log_info("容器已初始化", "DI_CONTAINER")
            return self.component_manager.components.copy()

        if self.container is None:
            self.create_container()

        components = self.component_manager.initialize_core_components()
        self._initialized = True

        return components

    def get_component(self, component_name: str) -> Optional[Any]:
        """获取组件"""
        if self.component_manager is None:
            log_error("容器未初始化", "DI_CONTAINER")
            return None

        return self.component_manager.get_component(component_name)

    def add_component(self, component_name: str, component: Any) -> None:
        """添加组件"""
        if self.component_manager is None:
            log_error("容器未初始化", "DI_CONTAINER")
            return

        self.component_manager.add_component(component_name, component)

    def cleanup(self) -> None:
        """清理容器和所有组件"""
        if self.component_manager is not None:
            self.component_manager.cleanup_components()

        self.container = None
        self.component_manager = None
        self._initialized = False

        log_success("容器管理器清理完成", "DI_CONTAINER")

    @property
    def is_initialized(self) -> bool:
        """检查容器是否已初始化"""
        return self._initialized


# 全局容器管理器实例
_global_container_manager: Optional[DIContainerManager] = None


def get_container_manager() -> DIContainerManager:
    """获取全局容器管理器实例"""
    global _global_container_manager
    if _global_container_manager is None:
        _global_container_manager = DIContainerManager()
    return _global_container_manager


def create_container() -> BaseContainer:
    """创建容器的便捷函数"""
    return get_container_manager().create_container()


def initialize_container() -> Dict[str, Any]:
    """初始化容器的便捷函数"""
    return get_container_manager().initialize()


def get_component(component_name: str) -> Optional[Any]:
    """获取组件的便捷函数"""
    return get_container_manager().get_component(component_name)


def cleanup_container() -> None:
    """清理容器的便捷函数"""
    get_container_manager().cleanup()
