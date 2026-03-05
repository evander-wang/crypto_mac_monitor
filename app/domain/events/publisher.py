"""EventPublisher 接口 - 事件发布者抽象"""

from abc import ABC, abstractmethod
from typing import Callable, Any


class EventPublisher(ABC):
    """
    事件发布者抽象接口

    领域层定义，由基础设施层实现。
    封装事件发布和订阅逻辑。
    """

    @abstractmethod
    def publish_ui(self, event: str, data: Any) -> None:
        """
        发布事件到 UI 线程

        Args:
            event: 事件名称
            data: 事件数据
        """
        pass

    @abstractmethod
    def publish_alert(self, event: str, data: Any) -> None:
        """
        发布事件到告警线程

        Args:
            event: 事件名称
            data: 事件数据
        """
        pass

    @abstractmethod
    def subscribe(self, event: str, handler: Callable) -> None:
        """
        订阅事件

        Args:
            event: 事件名称
            handler: 事件处理函数
        """
        pass
