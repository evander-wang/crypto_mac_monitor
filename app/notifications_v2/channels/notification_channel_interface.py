"""
通知通道接口定义

定义了通知通道的标准接口，用于统一不同类型的通知渠道。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.notifications_v2.notification_level import NotificationLevel


class INotificationChannel(ABC):
    """通知通道接口"""

    @abstractmethod
    def send(
        self,
        message: str,
        title: str = "Notification",
        level: NotificationLevel = NotificationLevel.INFO,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        发送通知

        Args:
            message: 通知消息内容
            title: 通知标题
            level: 通知级别
            data: 额外数据

        Returns:
            发送是否成功
        """
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """
        检查通道是否启用

        Returns:
            通道是否启用
        """
        pass

    @abstractmethod
    def get_channel_name(self) -> str:
        """
        获取通道名称

        Returns:
            通道名称
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        测试通道连接

        Returns:
            连接是否正常
        """
        pass

    def update_config(self, config: Dict[str, Any]) -> None:
        """
        更新通道配置（可选实现）

        Args:
            config: 新的配置
        """
        pass
