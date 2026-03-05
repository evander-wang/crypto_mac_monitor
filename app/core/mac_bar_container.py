"""
Mac Bar应用专用的依赖注入容器

该模块扩展基础容器，添加Mac Bar应用特有的组件，如悬浮窗等UI组件。
"""

from typing import Any, Dict, List, Optional, Type, TypeVar

from dependency_injector import providers

from app.analysis.realtime_analysis import RealtimeAnalysis
from app.analysis.trend_analysis import TrendAnalysis
from app.consts.consts import (
    COMPONENTS_ANALYSIS_RUNNER,
    COMPONENTS_APP_SERVICES,
    COMPONENTS_DATA_MANAGER,
    COMPONENTS_FLOATING_WINDOW,
    COMPONENTS_REALTIME_HELPER,
    COMPONENTS_STATUS_MENU,
    COMPONENTS_THREAD_MEMORY_DATA_CACHE_MANAGER,
    COMPONENTS_TREND_ANALYZER,
    COMPONENTS_WORLD_CLOCK_SERVICE,
)
from app.core.di_container import BaseContainer, ComponentManager, DIContainerManager
from app.data_manager import EventDrivenDataManager, ThreadMemoryDataCacheManager
from app.menu.status_menu import StatusBarMenu
from app.services.app_lifecycle_service import AppLifecycleService
from app.services.world_clock_service import WorldClockService
from app.trend_analysis import TrendAnalyzer
from app.ui.mac_floating_window import FloatingWindow
from app.utils import log_error, log_success


class MacBarContainer(BaseContainer):
    """Mac菜单栏应用专用容器，扩展基础容器"""

    # UI组件 - 使用Singleton确保整个应用生命周期中只有一个悬浮窗实例
    floating_window = providers.Singleton(
        FloatingWindow,
        config_manager=BaseContainer.config_manager,
        opacity=providers.Callable(
            lambda config_manager: config_manager.get_ui_config().display.current_opacity,
            config_manager=BaseContainer.config_manager,
        ),
        bg_style=providers.Callable(
            lambda config_manager: config_manager.get_ui_config().display.current_bg_style,
            config_manager=BaseContainer.config_manager,
        ),
        thread_memory_data_cache_manager=BaseContainer.thread_memory_data_cache_manager,
        analysis_runner=BaseContainer.analysis_runner,
        realtime_helper=BaseContainer.realtime_helper,
    )

    # 状态栏菜单管理器
    status_menu = providers.Singleton(
        StatusBarMenu,
        config_manager=BaseContainer.config_manager,
        floating_window=floating_window,
    )

    # 世界时钟服务
    world_clock_service = providers.Singleton(
        WorldClockService,
        config_manager=BaseContainer.config_manager,
        floating_window=floating_window,
    )

    # 应用生命周期服务
    app_services = providers.Singleton(
        AppLifecycleService,
        analysis_runner=BaseContainer.analysis_runner,
        realtime_helper=BaseContainer.realtime_helper,
        data_manager=BaseContainer.data_manager,
        alert_manager=BaseContainer.alert_manager,
        world_clock_service=world_clock_service,
    )


class MacBarComponentManager(ComponentManager):
    """Mac Bar应用专用组件管理器"""

    def __init__(self, container: MacBarContainer):
        super().__init__(container)
        self.container: MacBarContainer = container

    def initialize_ui_components(self, symbol_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """初始化UI组件"""
        try:
            # 确保数据管理器已初始化
            if COMPONENTS_FLOATING_WINDOW not in self.components:
                data_manager = self.get_component("data_manager")
                if data_manager is None:
                    raise ValueError("数据管理器未初始化，无法创建悬浮窗")

                # 获取symbol_names
                if symbol_names is None:
                    symbol_names = data_manager.get_supported_symbols()

                # 初始化悬浮窗
                self.components[COMPONENTS_FLOATING_WINDOW] = self.container.floating_window(symbol_names=symbol_names)
                log_success("悬浮窗初始化成功", "MAC_BAR_CONTAINER")

            # 初始化状态栏菜单管理器
            if COMPONENTS_STATUS_MENU not in self.components:
                self.components[COMPONENTS_STATUS_MENU] = self.container.status_menu()
                log_success("状态栏菜单管理器初始化成功", "MAC_BAR_CONTAINER")

            # 初始化世界时钟服务
            if COMPONENTS_WORLD_CLOCK_SERVICE not in self.components:
                self.components[COMPONENTS_WORLD_CLOCK_SERVICE] = self.container.world_clock_service()
                log_success("世界时钟服务初始化成功", "MAC_BAR_CONTAINER")

            # 初始化应用生命周期服务
            if COMPONENTS_APP_SERVICES not in self.components:
                self.components[COMPONENTS_APP_SERVICES] = self.container.app_services()
                log_success("应用生命周期服务初始化成功", "MAC_BAR_CONTAINER")

            return self.components.copy()

        except Exception as e:
            log_error(f"UI组件初始化失败: {e}", "MAC_BAR_CONTAINER")
            raise

    def initialize_all_components(self, symbol_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """初始化所有组件（核心组件 + UI组件）"""
        # 先初始化核心组件
        components = self.initialize_core_components()

        # 再初始化UI组件
        self.initialize_ui_components(symbol_names)

        return components


class MacBarContainerManager(DIContainerManager):
    """Mac Bar应用专用容器管理器"""

    def __init__(self):
        super().__init__(MacBarContainer)
        self.component_manager: MacBarComponentManager = None

    def create_container(self) -> MacBarContainer:
        """创建Mac Bar专用容器"""
        if self.container is not None:
            return self.container

        self.container = MacBarContainer()
        self.container.wire(modules=[__name__])
        self.component_manager = MacBarComponentManager(self.container)

        log_success("Mac Bar依赖注入容器创建成功", "MAC_BAR_CONTAINER")
        return self.container

    def initialize_with_symbols(self, symbol_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """初始化容器和所有组件（包括UI组件）"""
        if self._initialized:
            return self.component_manager.components.copy()

        if self.container is None:
            self.create_container()

        components = self.component_manager.initialize_all_components(symbol_names)
        self._initialized = True

        return components

    def get_floating_window(self) -> Optional[Any]:
        """获取悬浮窗组件的便捷方法"""
        return self.get_component(COMPONENTS_FLOATING_WINDOW)


# Mac Bar应用专用的全局容器管理器
_mac_bar_container_manager: Optional[MacBarContainerManager] = None


def get_mac_bar_container_manager() -> MacBarContainerManager:
    """获取Mac Bar专用容器管理器实例"""
    global _mac_bar_container_manager
    if _mac_bar_container_manager is None:
        _mac_bar_container_manager = MacBarContainerManager()
    return _mac_bar_container_manager


def create_mac_bar_container() -> MacBarContainer:
    """创建Mac Bar容器的便捷函数"""
    return get_mac_bar_container_manager().create_container()


def initialize_mac_bar_container(symbol_names: Optional[List[str]] = None) -> Dict[str, Any]:
    """初始化Mac Bar容器的便捷函数"""
    return get_mac_bar_container_manager().initialize_with_symbols(symbol_names)


def get_mac_bar_component(component_name: str) -> Optional[Any]:
    """获取Mac Bar组件的便捷函数"""
    return get_mac_bar_container_manager().get_component(component_name)


T = TypeVar("T")


def get_mac_bar_component_typed(component_name: str, expected_type: Type[T]) -> Optional[T]:
    """按期望类型获取组件，提供明确返回类型。

    Args:
        component_name: 组件名称常量，如 `COMPONENTS_DATA_MANAGER`。
        expected_type: 期望组件类型，例如 `EventDrivenDataManager`。

    Returns:
        如果组件存在且类型匹配，返回该类型；否则返回 `None`。
    """
    component = get_mac_bar_container_manager().get_component(component_name)
    if component is None:
        return None
    if isinstance(component, expected_type):
        return component
    # 类型不匹配时返回 None，并记录错误便于定位
    log_error(
        f"组件 {component_name} 类型不匹配: 实际 {type(component).__name__}, 期望 {expected_type.__name__}",
        "MAC_BAR_CONTAINER",
    )
    return None


def get_realtime_helper() -> Optional[RealtimeAnalysis]:
    """获取实时助手组件"""
    return get_mac_bar_component_typed(COMPONENTS_REALTIME_HELPER, RealtimeAnalysis)


def get_trend_analyzer() -> Optional[TrendAnalyzer]:
    """获取趋势分析器组件"""
    return get_mac_bar_component_typed(COMPONENTS_TREND_ANALYZER, TrendAnalyzer)


def get_data_manager() -> Optional[EventDrivenDataManager]:
    """获取数据管理器组件"""
    return get_mac_bar_component_typed(COMPONENTS_DATA_MANAGER, EventDrivenDataManager)


def get_analysis_runner() -> Optional[TrendAnalysis]:
    """获取分析运行器组件"""
    return get_mac_bar_component_typed(COMPONENTS_ANALYSIS_RUNNER, TrendAnalysis)


def get_floating_window() -> Optional[FloatingWindow]:
    """获取浮动窗口组件"""
    return get_mac_bar_component_typed(COMPONENTS_FLOATING_WINDOW, FloatingWindow)


def get_real_time_helper() -> Optional[RealtimeAnalysis]:
    """获取实时助手组件"""
    return get_mac_bar_component_typed(COMPONENTS_REALTIME_HELPER, RealtimeAnalysis)


def get_thread_memory_data_cache_manager() -> Optional[ThreadMemoryDataCacheManager]:
    """获取线程内存数据缓存管理器组件"""
    return get_mac_bar_component_typed(COMPONENTS_THREAD_MEMORY_DATA_CACHE_MANAGER, ThreadMemoryDataCacheManager)


def cleanup_mac_bar_container() -> None:
    """清理Mac Bar容器的便捷函数"""
    get_mac_bar_container_manager().cleanup()
