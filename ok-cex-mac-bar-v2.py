"""
OKX CEX Mac 菜单栏应用 - 事件驱动版本
基于新的事件驱动架构重构的主入口文件
"""

from typing import TypeVar
import argparse
import asyncio
import threading
import time

from dotenv import load_dotenv
import rumps

from app.analysis.realtime_analysis import RealtimeAnalysis
from app.config.config_manager import ConfigManager
from app.consts.consts import (
    COMPONENTS_APP_SERVICES,
    COMPONENTS_FLOATING_WINDOW,
    COMPONENTS_ORDER_MANAGER,
    COMPONENTS_POSITION_MANAGER,
    COMPONENTS_REALTIME_HELPER,
    COMPONENTS_STATUS_MENU,
    EVENT_UI_ENABLE_WINDOW,
)
from app.core.mac_bar_container import (
    MacBarContainer,
    cleanup_mac_bar_container,
    create_mac_bar_container,
    get_mac_bar_component_typed,
    initialize_mac_bar_container,
)
from app.events import get_bridge_manager, initialize_event_bridges, shutdown_event_bridges
from app.menu.status_menu import StatusBarMenu
from app.services.app_lifecycle_service import AppLifecycleService
from app.ui.mac_floating_window import FloatingWindow
from app.utils import LogLevel, log_error, log_info, log_success, log_warn, set_log_level_from_string


# 加载 .env 文件中的环境变量（优先级：环境变量 > .env 文件 > 配置文件）
load_dotenv()

T = TypeVar("T")


class EventDrivenCryptoApp(rumps.App):
    """事件驱动的加密货币菜单栏应用"""

    # 依赖注入容器和组件
    container: MacBarContainer | None

    def __init__(self):
        # 初始化依赖注入容器
        self.container = create_mac_bar_container()

        # 先获取配置
        self._config: ConfigManager = self.container.config()

        # 使用symbol_names初始化组件
        initialize_mac_bar_container(self._config.get_data_config().get_symbols())

        # 初始化rumps应用
        super(EventDrivenCryptoApp, self).__init__("加载中...", icon=self._config.get_app_config().get_icon_path())

        # 初始化UI组件
        log_info("准备调用_init_ui_components", "APP")
        try:
            self._init_ui_components()
        except Exception as e:
            log_error(f"_init_ui_components调用失败: {e}", "APP")
            import traceback

            log_error(f"详细错误信息: {traceback.format_exc()}", "APP")
            raise
        log_success("事件驱动加密货币菜单栏应用初始化完成", "APP")

    def _init_ui_components(self):
        """初始化UI组件"""
        try:
            # 获取悬浮窗组件
            self.floating_window = get_mac_bar_component_typed(COMPONENTS_FLOATING_WINDOW, FloatingWindow)
            self.realtime_helper = get_mac_bar_component_typed(COMPONENTS_REALTIME_HELPER, RealtimeAnalysis)
            log_success("UI组件初始化完成", "UI")
        except Exception as e:
            log_error(f"初始化UI组件失败: {e}", "UI")
            import traceback

            log_error(f"详细错误信息: {traceback.format_exc()}", "UI")
            raise

        # 初始化状态菜单（通过注入的菜单管理模块）
        try:
            self.status_menu = get_mac_bar_component_typed(COMPONENTS_STATUS_MENU, StatusBarMenu)
            if self.status_menu:
                self.status_menu.attach_to_app(self)
                log_success("状态菜单通过注入模块初始化完成", "UI")
        except Exception as e:
            log_error(f"通过注入模块初始化状态菜单失败: {e}", "UI")

    # ===== 接口要求的属性实现 =====
    @property
    def config(self) -> ConfigManager:
        """配置对象"""
        return self._config


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="OKX CEX Mac 菜单栏应用 - 事件驱动版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
可用的日志级别:
  {", ".join(LogLevel.list_levels())}

示例:
  python ok-cex-mac-bar-v2.py --log-level INFO
  python ok-cex-mac-bar-v2.py --log-level WARN
  python ok-cex-mac-bar-v2.py --log-level ERROR
        """,
    )

    parser.add_argument(
        "--log-level", "-l", type=str, default="DEBUG", choices=LogLevel.list_levels(), help="设置日志输出级别 (默认: INFO)"
    )

    return parser.parse_args()


def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()

        # 配置日志系统
        set_log_level_from_string(args.log_level)
        log_info(f"日志级别设置为: {args.log_level}", "CONFIG")

        app = EventDrivenCryptoApp()

        # 设置告警线程和事件循环
        alert_loop = asyncio.new_event_loop()

        def run_alert_loop():
            asyncio.set_event_loop(alert_loop)
            alert_loop.run_forever()

        alert_thread = threading.Thread(target=run_alert_loop, daemon=True, name="AlertLoopThread")
        alert_thread.start()

        # 等待事件循环启动
        time.sleep(0.1)

        # 初始化事件桥接器
        def ui_timer_func(interval, callback):
            return rumps.Timer(callback, interval)

        initialize_event_bridges(ui_timer_func, alert_loop)
        log_success("事件桥接器初始化完成", "EVENT")

        # 启动服务（使用依赖注入的生命周期服务）
        app_services = get_mac_bar_component_typed(COMPONENTS_APP_SERVICES, AppLifecycleService)
        if app_services is None:
            raise RuntimeError("生命周期服务未初始化")
        app_services.start_services()

        # 启动订单管理器
        try:
            from app.trading.order_manager import OrderManager

            order_manager = get_mac_bar_component_typed(COMPONENTS_ORDER_MANAGER, OrderManager)
            if order_manager:
                order_manager.start()
                log_success("订单管理器启动成功", "APP")
            else:
                log_warn("订单管理器未找到，跳过启动", "APP")
        except Exception as e:
            log_error(f"启动订单管理器失败: {e}", "APP")

        # 启动仓位管理器
        try:
            from app.trading.position_manager import PositionManager

            position_manager = get_mac_bar_component_typed(COMPONENTS_POSITION_MANAGER, PositionManager)
            if position_manager:
                position_manager.start()
                log_success("仓位管理器启动成功", "APP")
            else:
                log_warn("仓位管理器未找到，跳过启动", "APP")
        except Exception as e:
            log_error(f"启动仓位管理器失败: {e}", "APP")

        # 发布当前线程事件以启用/刷新UI窗口
        get_bridge_manager().publish_cur_thread(EVENT_UI_ENABLE_WINDOW, None)

        # 运行应用
        log_success("应用启动完成，开始运行主循环", "APP")
        app.run()

    except KeyboardInterrupt:
        log_info("应用程序被用户中断", "APP")
    except Exception as e:
        log_error(f"应用程序发生错误: {e}", "APP")
    finally:
        try:
            # 停止订单管理器
            try:
                from app.trading.order_manager import OrderManager

                order_manager = get_mac_bar_component_typed(COMPONENTS_ORDER_MANAGER, OrderManager)
                if order_manager:
                    order_manager.stop()
                    log_info("订单管理器已停止", "APP")
            except Exception as e:
                log_error(f"停止订单管理器失败: {e}", "APP")

            # 停止服务（使用依赖注入的生命周期服务）
            if "app_services" in locals() and app_services is not None:
                app_services.stop_services()

                # 清理容器和所有组件
                cleanup_mac_bar_container()
                log_info("容器和组件清理完成", "SERVICE")

            # 关闭事件桥接器
            shutdown_event_bridges()

            # 停止告警循环
            if "alert_loop" in locals():
                alert_loop.call_soon_threadsafe(alert_loop.stop)

            log_info("应用程序已退出", "APP")
        except Exception as e:
            log_error(f"清理资源失败: {e}", "APP")


if __name__ == "__main__":
    main()
