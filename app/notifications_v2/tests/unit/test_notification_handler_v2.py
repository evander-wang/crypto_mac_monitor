"""
NotificationManager 的单元测试（替换旧 NotificationHandlerV2）
"""

from unittest.mock import Mock

from app.notifications_v2.notification_manager import NotificationManager


class TestNotificationManager:
    """测试 NotificationManager 的基本行为"""

    def test_send_calls_broadcast(self):
        """send 应调用 channel_manager.broadcast"""
        mock_channel_manager = Mock()
        manager = NotificationManager(channel_manager=mock_channel_manager)

        manager.send("Hello", title="World")

        mock_channel_manager.broadcast.assert_called_once_with("Hello", "World")

    def test_send_handles_exception(self, caplog):
        """broadcast 抛异常时不应冒泡"""
        mock_channel_manager = Mock()
        mock_channel_manager.broadcast.side_effect = Exception("boom")
        manager = NotificationManager(channel_manager=mock_channel_manager)

        # 不应抛出异常
        manager.send("Hi", title="T")

        # 可选：检查日志中有错误（不强制）
        # assert any("Failed to broadcast notification" in rec.message for rec in caplog.records)
