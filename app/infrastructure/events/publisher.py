"""EventBusPublisher - 事件发布者实现"""

from typing import Any, Callable

from pyee import EventEmitter

from app.domain.events import EventPublisher
from app.events.bridge import UIEventBridge, AlertEventBridge


class EventBusPublisher(EventPublisher):
    """
    事件发布者实现

    基础设施层实现 EventPublisher 接口。
    封装 pyee EventEmitter 和跨线程桥接机制。
    """

    def __init__(self, config):
        """
        初始化事件发布者

        Args:
            config: 配置提供者
        """
        # 创建跨线程桥接器
        self.ui_bridge = UIEventBridge()
        self.alert_bridge = AlertEventBridge()

        # 分析线程内总线
        self.analysis_bus = EventEmitter()

    def publish_ui(self, event: str, data: Any) -> None:
        """
        发布事件到 UI 线程

        Args:
            event: 事件名称
            data: 事件数据
        """
        self.ui_bridge.publish_to_ui(event, data)

    def publish_alert(self, event: str, data: Any) -> None:
        """
        发布事件到告警线程

        Args:
            event: 事件名称
            data: 事件数据
        """
        self.alert_bridge.publish_to_alerts(event, data)

    def subscribe(self, event: str, handler: Callable) -> None:
        """
        订阅事件

        Args:
            event: 事件名称
            handler: 事件处理函数
        """
        self.analysis_bus.on(event, handler)
