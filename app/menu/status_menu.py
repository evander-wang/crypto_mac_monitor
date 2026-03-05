"""
状态栏菜单管理模块

将菜单构建与行为回调从应用入口解耦，使用依赖注入提供可重用的菜单服务。
"""

from __future__ import annotations

from typing import List, Optional

import rumps

from app.config.config_manager import ConfigManager
from app.ui.mac_floating_window import FloatingWindow
from app.utils import log_error, log_success


class StatusBarMenu:
    """状态栏菜单管理器

    负责构建菜单项并处理菜单行为，将具体逻辑与入口文件解耦。
    """

    def __init__(self, config_manager: ConfigManager, floating_window: FloatingWindow):
        """初始化菜单管理器

        Args:
            config_manager: 应用配置管理器
            floating_window: 悬浮窗组件实例
        """
        self._config = config_manager
        self._floating_window = floating_window

        self._app: Optional[rumps.App] = None
        self._menu_toggle_floating: Optional[rumps.MenuItem] = None
        self._menu_toggle_orders: Optional[rumps.MenuItem] = None
        self._menu_toggle_positions: Optional[rumps.MenuItem] = None

    def attach_to_app(self, app: rumps.App) -> None:
        """将菜单应用到 rumps.App，并保存引用以便后续刷新。

        Args:
            app: rumps 应用实例
        """
        try:
            self._app = app
            items = self._build_menu_items()
            # 放到菜单顶部
            self._app.menu = items
            log_success("状态栏菜单已附加到应用", "UI")
        except Exception as e:
            log_error(f"附加菜单到应用失败: {e}", "UI")

    def _build_menu_items(self) -> List[rumps.MenuItem]:
        """构建菜单项列表

        Returns:
            菜单项列表（包含显示/隐藏悬浮窗和订单状态）
        """
        is_shown = bool(getattr(self._floating_window, "window", None)) and bool(self._floating_window.is_visible)
        initial_title = "隐藏悬浮窗" if is_shown else "显示悬浮窗"

        # 获取订单状态显示标题
        orders_title = self._get_orders_menu_title()

        # 获取仓位状态显示标题
        positions_title = self._get_positions_menu_title()

        self._menu_toggle_floating = rumps.MenuItem(title=initial_title, callback=self._on_toggle_floating)
        self._menu_toggle_orders = rumps.MenuItem(title=orders_title, callback=self._on_toggle_orders)
        self._menu_toggle_positions = rumps.MenuItem(title=positions_title, callback=self._on_toggle_positions)

        return [self._menu_toggle_floating, self._menu_toggle_orders, self._menu_toggle_positions]

    def _on_toggle_floating(self, _: rumps.MenuItem) -> None:
        """菜单项回调：显示/隐藏悬浮窗"""
        try:
            if not self._floating_window:
                log_error("悬浮窗组件不存在", "UI")
                return
            self._floating_window.toggle_visibility()
            self.refresh_toggle_title()
        except Exception as e:
            log_error(f"切换悬浮窗显示失败: {e}", "UI")

    def _on_toggle_orders(self, _: rumps.MenuItem) -> None:
        """菜单项回调：显示/隐藏订单状态"""
        try:
            if not self._floating_window:
                log_error("悬浮窗组件不存在", "UI")
                return
            self._floating_window.toggle_order_display()
            self._menu_toggle_orders.title = self._get_orders_menu_title()
        except Exception as e:
            log_error(f"切换订单状态显示失败: {e}", "UI")

    def _on_toggle_positions(self, _: rumps.MenuItem) -> None:
        """菜单项回调：显示/隐藏仓位状态"""
        try:
            if not self._floating_window:
                log_error("悬浮窗组件不存在", "UI")
                return
            self._floating_window.toggle_position_display()
            self._menu_toggle_positions.title = self._get_positions_menu_title()
        except Exception as e:
            log_error(f"切换仓位状态显示失败: {e}", "UI")

    def _get_orders_menu_title(self) -> str:
        """获取订单状态菜单项标题"""
        try:
            if hasattr(self._floating_window, "order_display"):
                return self._floating_window.order_display.get_menu_title()
            return "订单状态: 未知"
        except Exception as e:
            log_error(f"获取订单菜单标题失败: {e}", "UI")
            return "订单状态: 错误"

    def _get_positions_menu_title(self) -> str:
        """获取仓位状态菜单项标题"""
        try:
            if hasattr(self._floating_window, "position_display"):
                return self._floating_window.position_display.get_menu_title()
            return "仓位状态: 未知"
        except Exception as e:
            log_error(f"获取仓位菜单标题失败: {e}", "UI")
            return "仓位状态: 错误"

    def refresh_toggle_title(self) -> None:
        """刷新显示/隐藏菜单项标题"""
        try:
            if not self._menu_toggle_floating:
                return
            is_shown = bool(getattr(self._floating_window, "window", None)) and bool(self._floating_window.is_visible)
            self._menu_toggle_floating.title = "隐藏悬浮窗" if is_shown else "显示悬浮窗"

            # 同时刷新订单状态菜单标题
            if self._menu_toggle_orders:
                self._menu_toggle_orders.title = self._get_orders_menu_title()

            # 同时刷新仓位状态菜单标题
            if self._menu_toggle_positions:
                self._menu_toggle_positions.title = self._get_positions_menu_title()
        except Exception as e:
            log_error(f"刷新菜单标题失败: {e}", "UI")
