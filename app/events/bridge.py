"""
事件桥接层实现
提供跨线程事件通信的桥接机制
"""

from typing import Any, Callable, Dict, Optional
import asyncio
import queue
import threading

from pyee import EventEmitter
from pyee.asyncio import AsyncIOEventEmitter

from app.consts.consts import LOGGER_UI_EVENT_PUMP_PREFIX
from app.utils import log_debug, log_error, log_info, log_warn


class UIEventBridge:
    """UI线程事件桥接器

    负责将其他线程的事件安全地转发到UI主线程
    使用队列缓冲 + 定时泵取的方式实现
    """

    def __init__(self, debounce_ms: int = 100, max_queue_size: int = 1000):
        self.ui_queue = queue.Queue(maxsize=max_queue_size)
        self.debounce_ms = debounce_ms
        self.running = False
        self._pump_timer = None

        # UI线程的事件发射器
        self.ui_emitter = EventEmitter()

        # 去抖缓存：topic -> latest_event
        self._debounce_cache: Dict[str, Any] = {}

    def start_pump(self, timer_func: Callable[[float, Callable], Any]):
        """启动事件泵

        Args:
            timer_func: 定时器函数，如 rumps.Timer
        """
        if self.running:
            return

        self.running = True
        self._pump_timer = timer_func(self.debounce_ms / 1000.0, self._pump_events)
        self._pump_timer.name = "UIEventPumpTimer"
        self._pump_timer.daemon = True
        self._pump_timer.start()
        log_info(f"UI事件泵已启动，去抖间隔: {self.debounce_ms}ms", LOGGER_UI_EVENT_PUMP_PREFIX)

    def stop_pump(self):
        """停止事件泵"""
        self.running = False
        if self._pump_timer:
            self._pump_timer.stop()
            self._pump_timer = None
        log_info("UI事件泵已停止", LOGGER_UI_EVENT_PUMP_PREFIX)

    def publish_to_ui(self, topic: str, data: Any):
        """从其他线程发布事件到UI线程

        Args:
            topic: 事件主题
            data: 事件数据
        """
        try:
            # 非阻塞写入队列
            log_debug(f"告警事件桥接器发布事件 to ui {topic}", LOGGER_UI_EVENT_PUMP_PREFIX)
            self.ui_queue.put_nowait((topic, data))
        except queue.Full:
            log_warn(f"UI事件队列已满，丢弃事件: {topic}", LOGGER_UI_EVENT_PUMP_PREFIX)

    def _pump_events(self, timer):
        """事件泵：从队列中取出事件并发射到UI线程"""
        if not self.running:
            return

        # 批量处理队列中的事件
        events_processed = 0
        while events_processed < 50:  # 限制单次处理数量
            try:
                topic, data = self.ui_queue.get_nowait()

                # 去抖处理：相同topic的事件只保留最新的
                self._debounce_cache[topic] = data
                events_processed += 1

            except queue.Empty:
                break

        # 发射去抖后的事件
        for topic, data in self._debounce_cache.items():
            try:
                self.ui_emitter.emit(topic, data)
            except Exception as e:
                log_error(f"UI事件发射失败 {topic}: {e}", LOGGER_UI_EVENT_PUMP_PREFIX)

        # 清空去抖缓存
        self._debounce_cache.clear()

        if events_processed > 0:
            log_debug(f"UI事件泵处理了 {events_processed} 个事件", LOGGER_UI_EVENT_PUMP_PREFIX)


class AlertEventBridge:
    """告警线程事件桥接器

    负责将其他线程的事件安全地转发到告警线程的asyncio循环
    """

    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.loop = loop
        self.alert_emitter = AsyncIOEventEmitter()

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """设置目标asyncio循环"""
        self.loop = loop
        log_info("告警事件桥接器已绑定到asyncio循环", LOGGER_UI_EVENT_PUMP_PREFIX)

    def publish_to_alerts(self, topic: str, data: Any):
        """从其他线程发布事件到告警线程

        Args:
            topic: 事件主题
            data: 事件数据
        """
        if not self.loop:
            log_warn(f"告警事件桥接器未绑定循环，丢弃事件: {topic}", LOGGER_UI_EVENT_PUMP_PREFIX)
            return

        try:
            # 使用call_soon_threadsafe安全地调度到目标循环
            self.loop.call_soon_threadsafe(self._emit_in_loop, topic, data)
        except Exception as e:
            log_error(f"告警事件跨线程调度失败 {topic}: {e}", LOGGER_UI_EVENT_PUMP_PREFIX)

    def _emit_in_loop(self, topic: str, data: Any):
        """在目标循环中发射事件"""
        try:
            log_info(f"告警事件桥接器发射事件 to alart {topic}", LOGGER_UI_EVENT_PUMP_PREFIX)
            self.alert_emitter.emit(topic, data)
        except Exception as e:
            log_error(f"告警事件发射失败 {topic}: {e}", LOGGER_UI_EVENT_PUMP_PREFIX)


class AnalysisEventBridge:
    """分析线程事件桥接器

    负责将其他线程的事件安全地转发到分析线程
    使用队列缓冲 + 线程安全的方式实现
    """

    def __init__(self, max_queue_size: int = 1000):
        self.analysis_queue = queue.Queue(maxsize=max_queue_size)
        self.running = False
        self.analysis_thread = None

        # 分析线程的事件发射器
        self.analysis_emitter = EventEmitter()

    def start_analysis_thread(self):
        """启动分析线程"""
        if self.running:
            return

        self.running = True
        self.analysis_thread = threading.Thread(target=self._analysis_thread_worker, name="AnalysisEventThread", daemon=True)
        self.analysis_thread.start()
        log_info("分析事件线程已启动", LOGGER_UI_EVENT_PUMP_PREFIX)

    def stop_analysis_thread(self):
        """停止分析线程"""
        self.running = False
        if self.analysis_thread and self.analysis_thread.is_alive():
            # 发送停止信号
            try:
                self.analysis_queue.put_nowait(("__STOP__", None))
            except queue.Full:
                pass
            self.analysis_thread.join(timeout=2.0)
        log_info("分析事件线程已停止", LOGGER_UI_EVENT_PUMP_PREFIX)

    def publish_to_analysis(self, topic: str, data: Any):
        """从其他线程发布事件到分析线程

        Args:
            topic: 事件主题
            data: 事件数据
        """
        try:
            # 非阻塞写入队列
            log_debug(f"发布事件到分析线程: {topic}", LOGGER_UI_EVENT_PUMP_PREFIX)
            self.analysis_queue.put_nowait((topic, data))
        except queue.Full:
            log_warn(f"分析事件队列已满，丢弃事件: {topic}", LOGGER_UI_EVENT_PUMP_PREFIX)

    def _analysis_thread_worker(self):
        """分析线程工作函数：从队列中取出事件并发射"""
        log_info("分析事件线程工作器已启动", LOGGER_UI_EVENT_PUMP_PREFIX)

        while self.running:
            try:
                # 阻塞等待事件，超时1秒检查运行状态
                topic, data = self.analysis_queue.get(timeout=1.0)

                # 检查停止信号
                if topic == "__STOP__":
                    break

                # 发射事件到分析线程的事件总线
                try:
                    self.analysis_emitter.emit(topic, data)
                    log_debug(f"分析线程发射事件: {topic}", LOGGER_UI_EVENT_PUMP_PREFIX)
                except Exception as e:
                    log_error(f"分析事件发射失败 {topic}: {e}", LOGGER_UI_EVENT_PUMP_PREFIX)

            except queue.Empty:
                # 超时，继续循环检查运行状态
                continue
            except Exception as e:
                log_error(f"分析线程工作器异常: {e}", LOGGER_UI_EVENT_PUMP_PREFIX)

        log_info("分析事件线程工作器已退出", LOGGER_UI_EVENT_PUMP_PREFIX)


class EventBridgeManager:
    """事件桥接管理器

    统一管理UI、告警和分析线程的事件桥接器
    """

    def __init__(self):
        self.ui_bridge = UIEventBridge()
        self.alert_bridge = AlertEventBridge()
        self.analysis_bridge = AnalysisEventBridge()
        self._initialized = False
        # 每线程事件总线：thread_id -> EventEmitter
        self._thread_emitters: Dict[int, EventEmitter] = {}
        self._thread_emitters_lock = threading.Lock()

    def initialize(
        self,
        ui_timer_func: Callable[[float, Callable], Any],
        alert_loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        """初始化桥接器

        Args:
            ui_timer_func: UI定时器函数
            alert_loop: 告警线程的asyncio循环
        """
        if self._initialized:
            return

        # 启动UI事件泵
        self.ui_bridge.start_pump(ui_timer_func)

        # 绑定告警循环
        if alert_loop:
            self.alert_bridge.set_loop(alert_loop)

        # 启动分析线程
        self.analysis_bridge.start_analysis_thread()

        self._initialized = True
        log_info("事件桥接管理器初始化完成", LOGGER_UI_EVENT_PUMP_PREFIX)

    def shutdown(self):
        """关闭桥接器"""
        self.ui_bridge.stop_pump()
        self.analysis_bridge.stop_analysis_thread()
        # 清理每线程事件总线
        with self._thread_emitters_lock:
            self._thread_emitters.clear()
        self._initialized = False
        log_info("事件桥接管理器已关闭", LOGGER_UI_EVENT_PUMP_PREFIX)

    def get_ui_emitter(self) -> EventEmitter:
        """获取UI线程事件发射器"""
        return self.ui_bridge.ui_emitter

    def get_alert_emitter(self) -> AsyncIOEventEmitter:
        """获取告警线程事件发射器"""
        return self.alert_bridge.alert_emitter

    def get_analysis_emitter(self) -> EventEmitter:
        """获取分析线程事件发射器"""
        return self.analysis_bridge.analysis_emitter

    def publish_to_ui(self, topic: str, data: Any):
        """发布事件到UI线程"""
        self.ui_bridge.publish_to_ui(topic, data)

    def publish_to_alerts(self, topic: str, data: Any):
        """发布事件到告警线程"""
        self.alert_bridge.publish_to_alerts(topic, data)

    def publish_to_analysis(self, topic: str, data: Any):
        """发布事件到分析线程"""
        self.analysis_bridge.publish_to_analysis(topic, data)

    def get_cur_thread_emitter(self) -> EventEmitter:
        """获取当前线程的事件发射器

        若当前线程尚未创建事件总线，则进行惰性创建并缓存。

        Returns:
            EventEmitter: 当前线程的事件发射器
        """
        thread_id = threading.get_ident()
        with self._thread_emitters_lock:
            emitter = self._thread_emitters.get(thread_id)
            if emitter is None:
                emitter = EventEmitter()
                self._thread_emitters[thread_id] = emitter
                log_info(f"创建当前线程事件总线: {thread_id}", LOGGER_UI_EVENT_PUMP_PREFIX)
            return emitter

    def publish_cur_thread(self, topic: str, data: Any) -> None:
        """在当前线程事件总线上发布事件

        Args:
            topic: 事件主题
            data: 事件数据
        """
        try:
            emitter = self.get_cur_thread_emitter()
            emitter.emit(topic, data)
            log_debug(f"当前线程事件总线发射事件: {topic}", LOGGER_UI_EVENT_PUMP_PREFIX)
        except Exception as e:
            log_error(f"当前线程事件总线发射失败 {topic}: {e}", LOGGER_UI_EVENT_PUMP_PREFIX)


# 全局桥接管理器实例
_bridge_manager: Optional[EventBridgeManager] = None


def get_bridge_manager() -> EventBridgeManager:
    """获取全局桥接管理器实例"""
    global _bridge_manager
    if _bridge_manager is None:
        _bridge_manager = EventBridgeManager()
    return _bridge_manager


def initialize_event_bridges(
    ui_timer_func: Callable[[float, Callable], Any],
    alert_loop: Optional[asyncio.AbstractEventLoop] = None,
):
    """初始化全局事件桥接器"""
    bridge_manager = get_bridge_manager()
    bridge_manager.initialize(ui_timer_func, alert_loop)


def shutdown_event_bridges():
    """关闭全局事件桥接器"""
    global _bridge_manager
    if _bridge_manager:
        _bridge_manager.shutdown()
        _bridge_manager = None


def get_cur_thread_emitter() -> EventEmitter:
    """获取当前线程的事件发射器（全局封装）"""
    return get_bridge_manager().get_cur_thread_emitter()


def publish_cur_thread(topic: str, data: Any) -> None:
    """在当前线程事件总线上发布事件（全局封装）"""
    get_bridge_manager().publish_cur_thread(topic, data)
