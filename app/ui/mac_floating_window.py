from app.analysis.trend_analysis import TrendAnalysis
from app.consts.consts import (
    COMPONENTS_LIMIT_ORDER_SERVICE,
    EVENT_PRICE_UPDATE,
    EVENT_TREND_UPDATE,
    EVENT_UI_ENABLE_WINDOW,
    EVENT_WORLD_CLOCK_UPDATE,
)
from app.data_manager import ThreadMemoryDataCacheManager
from app.events import get_bridge_manager
from app.models import AnalysisTrendDTO, ReturnCryptoSymbolUiInfoDto
from app.trading.limit_order_service import LimitOrderService
from app.ui.order_status_display import OrderStatusDisplay
from app.ui.position_status_display import PositionStatusDisplay


"""
事件驱动的悬浮窗口

基于原有FloatingWindow，集成事件订阅模式
自动响应数据更新事件，实现实时UI更新
"""

from typing import Dict

from AppKit import (
    NSAttributedString,
    NSBezierPath,
    NSColor,
    NSEvent,
    NSFont,
    NSMakeRect,
    NSPoint,
    NSScreen,
    NSString,
    NSView,
    NSWindow,
)
from Foundation import NSOperationQueue
import objc

from app.analysis.realtime_analysis import RealtimeAnalysis
from app.config.config_manager import ConfigManager
from app.models import Return5mExtrasDTO, ReturnCryptoSymbolDisplayDTO
from app.utils import log_debug, log_error, log_info, log_success, log_warn

from .ui_utils import crypto_symbol_Factory


# 常量（与主程序保持一致）
NSBorderlessWindowMask = 0
NSBackingStoreBuffered = 2
NSStatusWindowLevel = 25
NSWindowCollectionBehaviorCanJoinAllSpaces = 1 << 0
NSWindowCollectionBehaviorStationary = 1 << 4

NSFontAttributeName = "NSFont"
NSForegroundColorAttributeName = "NSColor"


class FloatingWindow:
    """悬浮窗口类，用于显示加密货币价格和趋势信息"""

    def __init__(
        self,
        config_manager: ConfigManager,
        opacity: float = 0.9,
        trend_labels=None,
        symbol_names=None,
        bg_style: str = "deep",
        thread_memory_data_cache_manager: ThreadMemoryDataCacheManager | None = None,
        analysis_runner: TrendAnalysis | None = None,
        realtime_helper: RealtimeAnalysis | None = None,
    ):
        """
        初始化事件驱动悬浮窗口

        Args:
            opacity: 窗口透明度
            trend_labels: 趋势标签列表
            symbol_names: 交易对符号列表
            bg_style: 背景样式 (light/medium/deep)
        """
        self.configManager: ConfigManager = config_manager
        self.opacity = opacity
        self.is_visible = True
        self.window = None
        self.trend_labels = trend_labels or []
        self.bg_style = bg_style
        self.crypto_data: Dict[str, ReturnCryptoSymbolDisplayDTO] = {}
        self.thread_memory_data_cache_manager: ThreadMemoryDataCacheManager | None = thread_memory_data_cache_manager
        self.analysis_runner: TrendAnalysis | None = analysis_runner
        self.realtime_helper: RealtimeAnalysis | None = realtime_helper

        # 时间文本
        self.time_texts = {}

        # 订单状态显示组件
        self.order_display = OrderStatusDisplay()

        # 仓位状态显示组件
        self.position_display = PositionStatusDisplay()

        # 设置快速卖出回调
        self.position_display.set_quick_sell_callback(self._on_quick_sell)

        # 连接限价服务（在初始化后）
        self._connect_position_display_to_limit_service()

        # 闪烁状态管理
        self.blink_states = {}  # {symbol: {tf: {'is_blinking': bool, 'blink_count': int, 'blink_on': bool}}}
        self.blink_timer = None
        self.max_blink_count = 6  # 闪烁3次（每次闪烁包含开和关）
        self.blink_interval = 0.3  # 闪烁间隔（秒）

        # 动态获取支持的时间周期并初始化闪烁状态
        supported_timeframes = self.configManager.get_data_config().get_supported_timeframes()

        for symbol in symbol_names or []:
            self.crypto_data[symbol] = ReturnCryptoSymbolDisplayDTO(
                symbol_info=ReturnCryptoSymbolUiInfoDto(symbol=symbol),
                trend_by_tf=AnalysisTrendDTO(symbol=symbol),
                extras_by_tf=Return5mExtrasDTO(),
            )
            # 初始化闪烁状态为动态时间周期
            self.blink_states[symbol] = {tf: {"is_blinking": False, "blink_count": 0, "blink_on": False} for tf in supported_timeframes}

        self._listener_event()
        log_success("事件驱动悬浮窗口初始化完成", "EVENT_FLOATING_WINDOW")

    def start_blink(self, symbol: str, timeframe: str):
        """开始指定时间框架的闪烁效果"""
        if symbol not in self.blink_states:
            return

        if timeframe not in self.blink_states[symbol]:
            return

        # 重置闪烁状态
        self.blink_states[symbol][timeframe] = {"is_blinking": True, "blink_count": 0, "blink_on": True}

        # 启动闪烁定时器（如果还没有启动）
        if self.blink_timer is None:
            import rumps

            self.blink_timer = rumps.Timer(self._blink_tick, self.blink_interval)
            self.blink_timer.start()

        log_debug(f"开始闪烁: {symbol} {timeframe}", "BLINK")

    def _blink_tick(self, timer):
        """闪烁定时器回调"""
        has_active_blink = False

        for symbol in self.blink_states:
            for tf in self.blink_states[symbol]:
                state = self.blink_states[symbol][tf]
                if state["is_blinking"]:
                    has_active_blink = True
                    state["blink_count"] += 1
                    state["blink_on"] = not state["blink_on"]

                    # 检查是否达到最大闪烁次数
                    if state["blink_count"] >= self.max_blink_count:
                        state["is_blinking"] = False
                        state["blink_on"] = False
                        log_debug(f"闪烁结束: {symbol} {tf}", "BLINK")

        # 如果没有活跃的闪烁，停止定时器
        if not has_active_blink:
            if self.blink_timer:
                self.blink_timer.stop()
                self.blink_timer = None

        # 触发重绘
        self._trigger_redraw()

    def is_timeframe_blinking(self, symbol: str, timeframe: str) -> bool:
        """检查指定时间框架是否正在闪烁"""
        if symbol not in self.blink_states:
            return False
        if timeframe not in self.blink_states[symbol]:
            return False
        state = self.blink_states[symbol][timeframe]
        return state["is_blinking"] and state["blink_on"]

    def _listener_event(self):
        get_bridge_manager().get_ui_emitter().on(EVENT_PRICE_UPDATE, self.update_symbols_price)
        get_bridge_manager().get_ui_emitter().on(EVENT_TREND_UPDATE, self.update_trend)
        get_bridge_manager().get_ui_emitter().on(EVENT_WORLD_CLOCK_UPDATE, self.update_world_clock)
        get_bridge_manager().get_cur_thread_emitter().on(EVENT_UI_ENABLE_WINDOW, self._on_enable_ui_window)

    def _on_enable_ui_window(self, *_args):
        """当前线程事件: 启用/刷新悬浮窗口"""
        self.enable_ui_window()

    def update_symbols_price(self, symbol: str):
        if self.thread_memory_data_cache_manager is None:
            log_warn("线程内存数据缓存管理器未初始化，无法更新行情", "EVENT_FLOATING_WINDOW")
            return

        symbol_data = self.thread_memory_data_cache_manager.get_ticker_data(symbol)
        if symbol_data is None:
            log_warn(f"未找到交易对 {symbol} 的行情数据", "EVENT_FLOATING_WINDOW")
            return
        self.crypto_data[symbol].symbol_info = crypto_symbol_Factory(symbol, symbol_data)
        # 触发窗口重绘
        self._trigger_redraw()

    # 回掉处理趋势更新事件
    def update_trend(self, data: AnalysisTrendDTO):
        if self.analysis_runner is None:
            log_warn("分析运行器未初始化，无法更新趋势", "EVENT_FLOATING_WINDOW")
            return

        trend_dto = self.analysis_runner.get_trend_indicators(data.symbol)
        if trend_dto:
            log_info(f"更新趋势数据AA: {data.symbol} {trend_dto}", "EVENT_FLOATING_WINDOW")
            self.crypto_data[data.symbol].trend_by_tf = AnalysisTrendDTO(symbol=data.symbol, data=trend_dto)
            # 只对传入的时间框架进行闪烁处理
            try:
                updated_tf = getattr(data, "timeframe", None)
            except Exception:
                updated_tf = None
            if updated_tf:
                self.start_blink(data.symbol, updated_tf)

        ## 更新 extras 数据
        if self.realtime_helper is None:
            log_warn("实时助手未初始化，无法更新 extras 数据", "EVENT_FLOATING_WINDOW")
            return
        self.crypto_data[data.symbol].extras_by_tf = self.realtime_helper.get_5m_extras(data.symbol)

        # 触发窗口重绘
        self._trigger_redraw()

    def _trigger_redraw(self):
        """触发窗口重绘"""
        try:
            if self.window and self.is_visible:

                def redraw():
                    view = self.window.contentView()
                    if view:
                        view.setNeedsDisplay_(True)

                # 使用 NSOperationQueue 在主线程执行重绘，避免 SEL/函数类型错误
                NSOperationQueue.mainQueue().addOperationWithBlock_(redraw)
        except Exception as e:
            log_error(f"触发窗口重绘失败: {e}", "EVENT_FLOATING_WINDOW")

    def _get_current_screen(self):
        """根据配置获取目标显示器"""
        try:
            ui_config = self.configManager.get_ui_config()
            display_mode = ui_config.display.display_mode

            if display_mode == "main":
                # 强制使用主显示器
                screen = NSScreen.mainScreen()
                log_info("使用主显示器", "EVENT_FLOATING_WINDOW")
                return screen
            elif display_mode == "index":
                # 使用指定索引的显示器
                screens = NSScreen.screens()
                display_index = ui_config.display.display_index
                if 0 <= display_index < len(screens):
                    screen = screens[display_index]
                    screen_frame = screen.frame()
                    log_info(
                        f"使用指定显示器 (索引 {display_index}): {screen_frame.size.width}x{screen_frame.size.height}",
                        "EVENT_FLOATING_WINDOW",
                    )
                    return screen
                else:
                    log_warn(f"指定的显示器索引 {display_index} 超出范围，使用主显示器", "EVENT_FLOATING_WINDOW")
                    return NSScreen.mainScreen()
            else:
                # auto模式：检测鼠标当前所在的显示器
                mouse_location = NSEvent.mouseLocation()
                log_debug(f"auto模式，鼠标位置 ({mouse_location.x}, {mouse_location.y})", "EVENT_FLOATING_WINDOW")

                # 遍历所有显示器，找到包含鼠标的显示器
                screens = NSScreen.screens()

                # 查找鼠标所在的显示器
                for i, screen in enumerate(screens):
                    screen_frame = screen.frame()
                    # 检查鼠标是否在当前显示器范围内
                    if (
                        mouse_location.x >= screen_frame.origin.x
                        and mouse_location.x < screen_frame.origin.x + screen_frame.size.width
                        and mouse_location.y >= screen_frame.origin.y
                        and mouse_location.y < screen_frame.origin.y + screen_frame.size.height
                    ):
                        log_info(
                            f"自动检测到鼠标在显示器: {screen_frame.size.width}x{screen_frame.size.height} "
                            f"位置: ({screen_frame.origin.x}, {screen_frame.origin.y})",
                            "EVENT_FLOATING_WINDOW",
                        )
                        return screen

                # 如果没有找到，返回主显示器
                log_warn("未能检测到鼠标所在显示器，使用主显示器", "EVENT_FLOATING_WINDOW")
                return NSScreen.mainScreen()

        except Exception as e:
            log_error(f"检测显示器失败: {e}，使用主显示器", "EVENT_FLOATING_WINDOW")
            return NSScreen.mainScreen()

    def _calculate_dynamic_height(self):
        """动态计算窗口高度，根据启用的时间框架数量和内容"""
        # 基础边距（上下边界空隙）
        top_margin = 20
        bottom_margin = 20

        # 世界时间区域高度
        time_count = len(self.time_texts) if hasattr(self, "time_texts") else 0
        time_height = (15 + 10) if time_count > 0 else 0  # 15px时间高度 + 10px分隔空间

        # 订单状态区域高度
        order_height = self.order_display.calculate_height() if hasattr(self, "order_display") else 0

        # 仓位状态区域高度
        position_height = self.position_display.calculate_height() if hasattr(self, "position_display") else 0

        # 符号数量
        symbol_count = len(self.crypto_data) if hasattr(self, "crypto_data") else 1

        # 获取启用的时间框架数量
        enabled_tf_count = len(self._get_enabled_timeframes())

        # 每个符号的高度计算
        symbol_base_height = 15  # 符号基本信息行高度
        trend_line_height = 15  # 每行趋势数据高度
        symbol_separator = 15  # 符号间分隔高度

        # 计算每个符号占用的总高度
        per_symbol_height = symbol_base_height + (enabled_tf_count * trend_line_height) + symbol_separator
        total_symbols_height = symbol_count * per_symbol_height

        # 计算总高度
        total_height = top_margin + time_height + order_height + position_height + total_symbols_height + bottom_margin

        # 设置最小和最大高度限制
        min_height = 80
        max_height = 600

        final_height = max(min_height, min(total_height, max_height))

        log_debug(
            f"动态计算窗口高度: {final_height} (启用时间框架: {enabled_tf_count}, 符号数: {symbol_count}, "
            f"时间区域: {time_height}, 订单区域: {order_height}, 仓位区域: {position_height}, "
            f"符号区域: {total_symbols_height}, 边距: {top_margin + bottom_margin})",
            "EVENT_FLOATING_WINDOW",
        )

        return final_height

    def _get_enabled_timeframes(self):
        """获取启用显示的时间框架列表"""
        if hasattr(self, "configManager") and self.configManager:
            return [tf for tf, tf_config in self.configManager.get_data_config().timeframes.items() if tf_config.show_on_ui]
        # 如果配置管理器不可用，返回默认值
        return ["1h", "4h"]

    def ensure_window(self, trend_labels=None):
        """确保窗口已建立"""
        if self.window is None:
            self._setup_window(trend_labels or self.trend_labels)

    def _setup_window(self, trend_labels):
        """设置窗口"""
        screen = self._get_current_screen()
        screen_rect = screen.frame()

        # 窗口尺寸
        window_width = 355
        window_height = self._calculate_dynamic_height()

        # 计算窗口位置：显示器右上角，留出一些边距
        window_x = screen_rect.origin.x + screen_rect.size.width - window_width - 100
        window_y = screen_rect.origin.y + screen_rect.size.height - window_height - 130

        window_rect = NSMakeRect(
            window_x,
            window_y,
            window_width,
            window_height,
        )

        log_info(f"窗口将显示在: ({window_x}, {window_y}) 尺寸: {window_width}x{window_height}", "EVENT_FLOATING_WINDOW")
        log_info(
            f"目标显示器: {screen_rect.size.width}x{screen_rect.size.height} 位置: ({screen_rect.origin.x}, {screen_rect.origin.y})",
            "EVENT_FLOATING_WINDOW",
        )

        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            window_rect, NSBorderlessWindowMask, NSBackingStoreBuffered, False
        )

        self.window.setBackgroundColor_(NSColor.clearColor())
        self.window.setAlphaValue_(self.opacity)
        self.window.setLevel_(NSStatusWindowLevel)
        self.window.setOpaque_(False)
        self.window.setHasShadow_(False)
        self.window.setIgnoresMouseEvents_(False)
        self.window.setMovableByWindowBackground_(True)
        self.window.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorStationary)

        # 内容视图 @todo 这种函数名和参数名段落数量要一致的定义后面学习下
        content = EventDrivenFloatingContentView.alloc().initWithWindow_floatingWindow_configManager_trendLabels_(
            self.window, self, self.configManager, trend_labels
        )
        self.window.setContentView_(content)

        self.adjust_window_size()

        # 显示窗口
        self.window.makeKeyAndOrderFront_(None)
        self.is_visible = True
        log_info("悬浮窗已显示", "EVENT_FLOATING_WINDOW")

    def adjust_window_size(self):
        """调整窗口大小"""
        try:
            if not self.window:
                return

            # 使用动态计算的高度
            total_height = self._calculate_dynamic_height()

            # 获取当前窗口位置
            current_frame = self.window.frame()
            new_frame = NSMakeRect(
                current_frame.origin.x,
                current_frame.origin.y,
                current_frame.size.width,
                total_height,
            )

            self.window.setFrame_display_(new_frame, True)
            log_debug(f"窗口大小调整为: {total_height}", "EVENT_FLOATING_WINDOW")

        except Exception as e:
            log_error(f"调整窗口大小失败: {e}", "EVENT_FLOATING_WINDOW")

    def set_time_texts(self, time_texts):
        """设置时间文本"""
        self.time_texts = time_texts or {}
        self.enable_ui_window()

    def enable_ui_window(self):
        # 当窗口隐藏时不强制创建或重绘，避免隐藏状态被打破
        if not self.is_visible:
            return
        self.ensure_window()
        self.adjust_window_size()
        self._trigger_redraw()

    def redraw(self):
        """触发窗口重绘"""
        # 隐藏时不重绘
        if not self.is_visible or not self.window:
            return
        self.adjust_window_size()
        self._trigger_redraw()

    def update_world_clock(self, time_texts):
        """更新世界时钟 - 兼容主程序接口"""
        self.set_time_texts(time_texts)

    def show_window(self):
        """显示悬浮窗"""
        try:
            self.ensure_window()
            if self.window:
                self.adjust_window_size()
                self.window.makeKeyAndOrderFront_(None)
            self.is_visible = True
            self._trigger_redraw()
            log_info("悬浮窗显示", "EVENT_FLOATING_WINDOW")
        except Exception as e:
            log_error(f"显示悬浮窗失败: {e}", "EVENT_FLOATING_WINDOW")

    def hide_window(self):
        """隐藏悬浮窗"""
        try:
            if self.window:
                self.window.orderOut_(None)
            self.is_visible = False
            log_info("悬浮窗隐藏", "EVENT_FLOATING_WINDOW")
        except Exception as e:
            log_error(f"隐藏悬浮窗失败: {e}", "EVENT_FLOATING_WINDOW")

    def toggle_visibility(self):
        """切换悬浮窗显示/隐藏"""
        if self.is_visible:
            self.hide_window()
        else:
            self.show_window()

    def _update_display_component(self, component, component_name: str, visibility: bool | None = None):
        """
        更新显示组件的可见性并刷新窗口

        Args:
            component: 显示组件对象
            component_name: 组件名称（用于日志）
            visibility: 可见性状态，None表示切换

        Returns:
            如果是切换操作，返回新的可见性状态；否则返回None
        """
        if component is None:
            return None if visibility is not None else False

        if visibility is None:
            # 切换可见性
            is_visible = component.toggle_visibility()
            status_text = "切换为"
            status_value = "显示" if is_visible else "隐藏"
            return_value = is_visible
        else:
            # 设置可见性
            component.set_visibility(visibility)
            status_text = "设置为"
            status_value = "显示" if visibility else "隐藏"
            return_value = None

        self.adjust_window_size()
        self._trigger_redraw()
        log_info(f"{component_name}显示{status_text}: {status_value}", "EVENT_FLOATING_WINDOW")
        return return_value

    def toggle_order_display(self):
        """切换订单状态显示/隐藏"""
        return self._update_display_component(getattr(self, "order_display", None), "订单状态", None)

    def set_order_display_visibility(self, visible: bool):
        """设置订单状态显示/隐藏"""
        self._update_display_component(getattr(self, "order_display", None), "订单状态", visible)

    def toggle_position_display(self):
        """切换仓位状态显示/隐藏"""
        return self._update_display_component(getattr(self, "position_display", None), "仓位状态", None)

    def set_position_display_visibility(self, visible: bool):
        """设置仓位状态显示/隐藏"""
        self._update_display_component(getattr(self, "position_display", None), "仓位状态", visible)

    def _on_quick_sell(self, position):
        """
        快速卖出回调处理

        Args:
            position: 要卖出的仓位信息
        """
        try:
            # 获取限价卖出服务
            from app.consts.consts import COMPONENTS_LIMIT_ORDER_SERVICE
            from app.core.mac_bar_container import get_mac_bar_component_typed
            from app.trading.limit_order_service import LimitOrderService

            limit_order_service = get_mac_bar_component_typed(COMPONENTS_LIMIT_ORDER_SERVICE, LimitOrderService)
            if not limit_order_service:
                log_error("限价卖出服务未找到", "FLOATING_WINDOW")
                return

            # 执行快速卖出
            result = limit_order_service.quick_sell_position(position)
            if result.success:
                log_info(f"快速卖出成功: {position.symbol} 订单ID: {result.order_id}", "FLOATING_WINDOW")
            else:
                log_error(f"快速卖出失败: {result.message}", "FLOATING_WINDOW")

        except Exception as e:
            log_error(f"快速卖出处理失败: {e}", "FLOATING_WINDOW")

    def _connect_position_display_to_limit_service(self):
        """连接仓位显示组件与限价服务"""
        try:
            from app.core.mac_bar_container import get_mac_bar_component_typed
            from app.trading.limit_order_service import LimitOrderService

            # 通过容器获取限价服务
            limit_order_service = get_mac_bar_component_typed(COMPONENTS_LIMIT_ORDER_SERVICE, LimitOrderService)
            if limit_order_service is not None:
                self.position_display.set_limit_order_service(limit_order_service)
                log_info("仓位显示组件已连接到限价服务", "FLOATING_WINDOW")
            else:
                log_warn("无法获取限价服务，仓位显示将无法动态设置执行模式", "FLOATING_WINDOW")

        except Exception as e:
            log_error(f"连接仓位显示与限价服务失败: {e}", "FLOATING_WINDOW")


class EventDrivenFloatingContentView(NSView):
    """事件驱动的悬浮窗口内容视图"""

    def initWithWindow_floatingWindow_configManager_trendLabels_(self, window, floatingWindow, config_manager, trend_labels):
        self = objc.super(EventDrivenFloatingContentView, self).init()
        if self is None:
            return None
        self.window = window
        self.floatingWindow: FloatingWindow = floatingWindow
        self.trend_labels = trend_labels
        self.configManager: ConfigManager = config_manager
        self.enabled_timeframes = [
            tf for tf, tf_config in self.configManager.get_data_config().timeframes.items() if tf_config.show_on_ui
        ]
        return self

    def mouseDown_(self, event):
        """鼠标按下事件"""
        try:
            # 获取点击位置（相对于视图）
            click_location = event.locationInWindow()
            x = click_location.x
            y = click_location.y

            # 检查是否点击了仓位显示的快速卖出按钮
            if hasattr(self.floatingWindow, "position_display"):
                if self.floatingWindow.position_display.handle_click(x, y):
                    # 如果处理了点击事件，不执行窗口拖拽
                    return

            # 如果没有处理点击事件，执行窗口拖拽
            self.window.performWindowDragWithEvent_(event)
        except Exception as e:
            # 出错时默认执行窗口拖拽
            self.window.performWindowDragWithEvent_(event)
            log_error(f"处理鼠标点击事件失败: {e}", "FLOATING_WINDOW")

    def mouseDragged_(self, event):
        """鼠标拖拽事件 - 支持跨显示器拖拽"""
        try:
            # 获取当前鼠标位置
            mouse_location = NSEvent.mouseLocation()

            # 获取窗口当前大小
            window_frame = self.window.frame()
            window_width = window_frame.size.width
            window_height = window_frame.size.height

            # 找到鼠标当前所在的显示器
            current_screen = None
            screens = NSScreen.screens()

            for screen in screens:
                screen_frame = screen.frame()
                if (
                    mouse_location.x >= screen_frame.origin.x
                    and mouse_location.x < screen_frame.origin.x + screen_frame.size.width
                    and mouse_location.y >= screen_frame.origin.y
                    and mouse_location.y < screen_frame.origin.y + screen_frame.size.height
                ):
                    current_screen = screen
                    break

            # 如果没有找到合适的显示器，使用主显示器
            if current_screen is None:
                current_screen = NSScreen.mainScreen()

            screen_frame = current_screen.frame()

            # 计算新的窗口位置，确保窗口在显示器范围内
            # 窗口左上角跟随鼠标，但保持在显示器边界内
            new_x = mouse_location.x - window_width / 2  # 鼠标在窗口中心
            new_y = mouse_location.y - 20  # 鼠标在窗口顶部附近

            # 限制窗口在当前显示器范围内
            new_x = max(screen_frame.origin.x, min(new_x, screen_frame.origin.x + screen_frame.size.width - window_width))
            new_y = max(screen_frame.origin.y, min(new_y, screen_frame.origin.y + screen_frame.size.height - window_height))

            # 设置新的窗口位置
            new_frame = NSMakeRect(new_x, new_y, window_width, window_height)
            self.window.setFrame_display_(new_frame, True)

        except Exception as e:
            log_error(f"拖拽窗口失败: {e}", "EVENT_FLOATING_WINDOW")

    def drawRect_(self, rect):
        """绘制窗口内容"""
        try:
            # 背景样式配置
            bg_colors = {
                "light": {"bg": (0.95, 0.95, 0.95, 0.9), "text": (0.1, 0.1, 0.1)},
                "medium": {"bg": (0.3, 0.3, 0.3, 0.9), "text": (0.9, 0.9, 0.9)},
                "deep": {"bg": (0.1, 0.1, 0.1, 0.9), "text": (0.9, 0.9, 0.9)},
            }

            style = bg_colors.get(self.floatingWindow.bg_style, bg_colors["deep"])

            # 绘制背景
            bg_color = NSColor.colorWithRed_green_blue_alpha_(*style["bg"])
            bg_color.set()

            path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, 10.0, 10.0)
            path.fill()

            # 绘制内容
            y_position = rect.size.height - 20

            # 首先绘制世界时间（顶部，单行显示）
            if self.floatingWindow.time_texts:
                # 将所有时间文本合并为一行，使用空格分隔
                time_texts_list = list(self.floatingWindow.time_texts.values())
                combined_time_text = " ".join(time_texts_list)  # 使用两个空格分隔

                font = NSFont.systemFontOfSize_(11.5)
                text_color = NSColor.colorWithRed_green_blue_alpha_(*style["text"], 0.7)

                attributes = {
                    NSFontAttributeName: font,
                    NSForegroundColorAttributeName: text_color,
                }

                attr_string = NSAttributedString.alloc().initWithString_attributes_(combined_time_text, attributes)

                text_rect = NSMakeRect(11, y_position, rect.size.width - 20, 12)
                attr_string.drawInRect_(text_rect)

                y_position -= 15  # 只减少一次，因为只有一行

            # 添加分隔空间
            if self.floatingWindow.time_texts:
                y_position -= 15

            # 绘制订单状态（在加密货币数据之前）
            if hasattr(self.floatingWindow, "order_display"):
                y_position = self.floatingWindow.order_display.draw(rect, self.floatingWindow.bg_style, y_position)

            # 绘制仓位状态（在加密货币数据之前）
            if hasattr(self.floatingWindow, "position_display"):
                y_position = self.floatingWindow.position_display.draw(rect, self.floatingWindow.bg_style, y_position)

            # 绘制加密货币数据和趋势信息
            for symbol, symbol_dto in self.floatingWindow.crypto_data.items():
                if y_position < 10:
                    break

                # 绘制基本价格信息
                text = symbol_dto.symbol_info.ui_text
                color_tuple = symbol_dto.symbol_info.color

                # 创建属性字符串
                font = NSFont.systemFontOfSize_(12)
                text_color = NSColor.colorWithRed_green_blue_alpha_(color_tuple[0], color_tuple[1], color_tuple[2], 1.0)

                attributes = {
                    NSFontAttributeName: font,
                    NSForegroundColorAttributeName: text_color,
                }

                attr_string = NSAttributedString.alloc().initWithString_attributes_(text, attributes)

                # 绘制价格文本
                text_rect = NSMakeRect(10, y_position, rect.size.width - 20, 20)
                attr_string.drawInRect_(text_rect)

                y_position -= 15

                # 绘制趋势数据
                trend_by_tf = symbol_dto.trend_by_tf
                extras_by_tf = symbol_dto.extras_by_tf

                if trend_by_tf:
                    # 固定三行：5m/1h/4h
                    tf_order = self.enabled_timeframes
                    per_line_gap = 20  # 减少行间距
                    base_gap = 3
                    total_lines = 0

                    for idx, tf in enumerate(tf_order):
                        trends = trend_by_tf.data.get(tf, [])
                        trend_y = y_position - (base_gap + idx * per_line_gap)
                        total_lines += 1

                        # 时间框架标签不同配色
                        label = f"    {tf}: "
                        label_start_x = 10

                        # 检查是否正在闪烁
                        is_blinking = self.floatingWindow.is_timeframe_blinking(symbol, tf)

                        if is_blinking:
                            # 闪烁时使用高亮颜色（白色/黄色）
                            label_color = NSColor.colorWithRed_green_blue_alpha_(1.0, 1.0, 0.0, 1.0)  # 黄色高亮
                            # 绘制背景高亮框
                            highlight_rect = NSMakeRect(label_start_x - 2, trend_y - 2, 50, 14)
                            NSColor.colorWithRed_green_blue_alpha_(1.0, 1.0, 0.0, 0.3).set()
                            NSBezierPath.fillRect_(highlight_rect)
                        else:
                            # 正常颜色
                            if tf == "5m":
                                label_color = NSColor.colorWithRed_green_blue_alpha_(0.4, 0.8, 1.0, 1.0)
                            elif tf == "1h":
                                label_color = NSColor.colorWithRed_green_blue_alpha_(0.6, 0.6, 1.0, 1.0)
                            else:
                                label_color = NSColor.colorWithRed_green_blue_alpha_(0.8, 0.6, 1.0, 1.0)

                        attrs = {
                            NSFontAttributeName: NSFont.systemFontOfSize_(10),
                            NSForegroundColorAttributeName: label_color,
                        }
                        label_text = NSString.alloc().initWithString_(label)
                        label_text.drawAtPoint_withAttributes_(NSPoint(label_start_x, trend_y), attrs)

                        # 箭头起始 x
                        label_width = label_text.sizeWithAttributes_({NSFontAttributeName: NSFont.systemFontOfSize_(10)}).width
                        x_position = label_start_x + label_width

                        # 无信号占位灰横
                        if not trends:
                            font = NSFont.boldSystemFontOfSize_(12)
                            attrs_dash = {
                                NSFontAttributeName: font,
                                NSForegroundColorAttributeName: NSColor.colorWithRed_green_blue_alpha_(0.6, 0.6, 0.6, 1.0),
                            }
                            dash = NSString.alloc().initWithString_("—")
                            dash.drawAtPoint_withAttributes_(NSPoint(x_position, trend_y - 3), attrs_dash)

                        # 绘制箭头
                        meta_confidence = None
                        meta_periods = None
                        trends_iter = trends if trends else []

                        for trend in trends_iter:
                            if isinstance(trend, dict) and "_meta" in trend:
                                try:
                                    meta_confidence = float(trend["_meta"].get("confidence", 0.0))
                                    if trend["_meta"].get("periods") is not None:
                                        meta_periods = int(trend["_meta"].get("periods"))
                                except Exception:
                                    meta_confidence = None
                                continue

                            direction = trend.get("direction") if isinstance(trend, dict) else None
                            strength = trend.get("strength", 0) if isinstance(trend, dict) else 0

                            if direction == "↑":
                                if strength >= 2:
                                    color = NSColor.colorWithRed_green_blue_alpha_(0, 0.7, 0, 1.0)
                                elif strength >= 1:
                                    color = NSColor.colorWithRed_green_blue_alpha_(0.2, 0.8, 0.2, 1.0)
                                else:
                                    color = NSColor.colorWithRed_green_blue_alpha_(0.5, 0.9, 0.5, 1.0)
                            elif direction == "↓":
                                if strength >= 2:
                                    color = NSColor.colorWithRed_green_blue_alpha_(0.8, 0, 0, 1.0)
                                elif strength >= 1:
                                    color = NSColor.colorWithRed_green_blue_alpha_(0.9, 0.2, 0.2, 1.0)
                                else:
                                    color = NSColor.colorWithRed_green_blue_alpha_(1.0, 0.5, 0.5, 1.0)
                            elif direction == "-":
                                color = NSColor.yellowColor()
                            else:
                                color = NSColor.whiteColor()

                            font = NSFont.boldSystemFontOfSize_(12)
                            attrs_arrow = {
                                NSFontAttributeName: font,
                                NSForegroundColorAttributeName: color,
                            }
                            arrow_text = NSString.alloc().initWithString_(direction or " ")
                            arrow_text.drawAtPoint_withAttributes_(NSPoint(x_position, trend_y - 3), attrs_arrow)
                            x_position += 15

                        # 行尾附加：(置信度/N) + 3x + R:
                        tail_parts = []
                        if meta_confidence is not None:
                            tail_parts.append(f" ({meta_confidence:.1f}{', N=' + str(meta_periods) if meta_periods else ''})")

                        if tf == "5m":
                            if extras_by_tf is None:
                                continue
                            tail_parts.append(f" {extras_by_tf.impulse}")
                            tail_parts.append(f" {extras_by_tf.breakout}")
                            tail_parts.append(f" {extras_by_tf.range}")

                        if tail_parts:
                            tail = " ".join(tail_parts)
                            conf_text = NSString.alloc().initWithString_(tail)
                            conf_attrs = {
                                NSFontAttributeName: NSFont.systemFontOfSize_(10),
                                NSForegroundColorAttributeName: NSColor.colorWithRed_green_blue_alpha_(0.9, 0.9, 0.9, 1.0),
                            }
                            conf_text.drawAtPoint_withAttributes_(NSPoint(x_position, trend_y - 2), conf_attrs)

                    # 下一个币种
                    extra_gap = max(0, total_lines - 1) * per_line_gap
                    y_position -= 30 + extra_gap
                else:
                    y_position -= 15

            # 绘制趋势标签（如果有的话）
            for label in self.trend_labels:
                if y_position < 10:
                    break

                font = NSFont.systemFontOfSize_(10)
                text_color = NSColor.colorWithRed_green_blue_alpha_(*style["text"], 0.8)

                attributes = {
                    NSFontAttributeName: font,
                    NSForegroundColorAttributeName: text_color,
                }

                attr_string = NSAttributedString.alloc().initWithString_attributes_(label, attributes)

                text_rect = NSMakeRect(10, y_position, rect.size.width - 20, 15)
                attr_string.drawInRect_(text_rect)

                y_position -= 20

        except Exception as e:
            log_error(f"绘制窗口内容失败: {e}", "EVENT_FLOATING_WINDOW")
