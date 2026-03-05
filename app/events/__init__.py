"""
事件系统模块
提供基于pyee的事件总线和跨线程桥接功能
"""

from typing import Any, Dict, Optional
import threading

from pyee import EventEmitter
from pyee.asyncio import AsyncIOEventEmitter

from app.consts.consts import LOGGER_EVENT_BUS_PREFIX
from app.utils import log_info

from .bridge import (
    EventBridgeManager,
    get_bridge_manager,
    initialize_event_bridges,
    shutdown_event_bridges,
)


class EventBusFactory:
    """事件总线工厂

    为每个线程提供独立的事件总线实例
    实现"每线程一个总线"的设计模式
    """

    def __init__(self):
        self._thread_buses: Dict[int, EventEmitter] = {}
        self._lock = threading.Lock()

    def get_bus_for_current_thread(self) -> EventEmitter:
        """获取当前线程的事件总线"""
        thread_id = threading.get_ident()

        with self._lock:
            if thread_id not in self._thread_buses:
                bus = EventEmitter()
                self._thread_buses[thread_id] = bus
                log_info(f"为线程 {thread_id} 创建新的事件总线", LOGGER_EVENT_BUS_PREFIX)

            return self._thread_buses[thread_id]

    def get_bus_for_thread(self, thread_id: int) -> Optional[EventEmitter]:
        """获取指定线程的事件总线"""
        with self._lock:
            return self._thread_buses.get(thread_id)

    def cleanup_thread_bus(self, thread_id: Optional[int] = None):
        """清理线程事件总线"""
        if thread_id is None:
            thread_id = threading.get_ident()

        with self._lock:
            if thread_id in self._thread_buses:
                bus = self._thread_buses.pop(thread_id)
                bus.remove_all_listeners()
                log_info(f"清理线程 {thread_id} 的事件总线", LOGGER_EVENT_BUS_PREFIX)

    def get_all_buses(self) -> Dict[int, EventEmitter]:
        """获取所有线程的事件总线（调试用）"""
        with self._lock:
            return self._thread_buses.copy()


# 全局事件总线工厂实例
_bus_factory: Optional[EventBusFactory] = None


def get_event_bus() -> EventEmitter:
    """获取当前线程的事件总线

    这是最常用的API，为当前线程返回一个EventEmitter实例
    """
    global _bus_factory
    if _bus_factory is None:
        _bus_factory = EventBusFactory()
    return _bus_factory.get_bus_for_current_thread()


def get_ui_event_bus() -> EventEmitter:
    """获取UI线程的事件总线

    返回通过桥接器连接的UI事件发射器
    """
    bridge_manager = get_bridge_manager()
    return bridge_manager.get_ui_emitter()


def get_alert_event_bus() -> AsyncIOEventEmitter:
    """获取告警线程的事件总线

    返回通过桥接器连接的告警事件发射器
    """
    bridge_manager = get_bridge_manager()
    return bridge_manager.get_alert_emitter()


def publish_to_ui(topic: str, data: Any = None):
    """发布事件到UI线程

    Args:
        topic: 事件主题
        data: 事件数据
    """
    bridge_manager = get_bridge_manager()
    bridge_manager.publish_to_ui(topic, data)


def publish_to_alerts(topic: str, data: Any = None):
    """发布事件到告警线程

    Args:
        topic: 事件主题
        data: 事件数据
    """
    bridge_manager = get_bridge_manager()
    bridge_manager.publish_to_alerts(topic, data)


def get_analysis_event_bus() -> EventEmitter:
    """获取分析线程的事件总线"""
    bridge_manager = get_bridge_manager()
    return bridge_manager.get_analysis_emitter()


def publish_to_analysis(topic: str, data: Any = None):
    """发布事件到分析线程

    Args:
        topic: 事件主题
        data: 事件数据
    """
    bridge_manager = get_bridge_manager()
    bridge_manager.publish_to_analysis(topic, data)


def cleanup_current_thread():
    """清理当前线程的事件总线"""
    global _bus_factory
    if _bus_factory:
        _bus_factory.cleanup_thread_bus()


def cleanup_all_buses():
    """清理所有线程的事件总线"""
    global _bus_factory
    if _bus_factory:
        for thread_id in list(_bus_factory.get_all_buses().keys()):
            _bus_factory.cleanup_thread_bus(thread_id)


# 导出主要API
__all__ = [
    # 事件总线工厂和获取函数
    "EventBusFactory",
    "get_event_bus",
    "get_ui_event_bus",
    "get_alert_event_bus",
    "get_analysis_event_bus",
    # 跨线程事件发布函数
    "publish_to_ui",
    "publish_to_alerts",
    "publish_to_analysis",
    # 清理函数
    "cleanup_current_thread",
    "cleanup_all_threads",
    # 桥接管理器
    "get_bridge_manager",
]
