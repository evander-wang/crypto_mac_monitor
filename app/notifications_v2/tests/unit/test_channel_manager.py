"""
ChannelManager 的单元测试（适配新版 API）
"""

from app.notifications_v2.channels.channel_manager import ChannelManager
from app.notifications_v2.channels.desktop_channel import DesktopChannel, DesktopConfig
from app.notifications_v2.channels.webhook_channel import WebhookChannel, WebhookConfig
from app.notifications_v2.config.notification_config import NotificationConfig


class TestChannelManager:
    """新版 ChannelManager 的测试"""

    def test_init_registers_channels(self):
        """根据配置正确注册渠道"""
        config = NotificationConfig(
            desktop=DesktopConfig(enabled=True),
            webhook=WebhookConfig(
                enabled=True,
                url="https://example.com/webhook",
                method="POST",
                message_format="JSON",
            ),
        )
        manager = ChannelManager(config)

        assert "desktop" in manager.channels
        assert "webhook" in manager.channels
        assert isinstance(manager.channels["desktop"], DesktopChannel)
        assert isinstance(manager.channels["webhook"], WebhookChannel)

    def test_get_channel_found_and_not_found(self):
        """获取渠道存在与不存在的情况"""
        config = NotificationConfig(desktop=DesktopConfig(enabled=True))
        manager = ChannelManager(config)

        assert isinstance(manager.get_channel("desktop"), DesktopChannel)
        assert manager.get_channel("unknown") is None

    def test_send_specific_channel(self, monkeypatch):
        """向特定渠道发送消息"""
        config = NotificationConfig(desktop=DesktopConfig(enabled=True))
        manager = ChannelManager(config)
        desktop = manager.get_channel("desktop")

        called = {"times": 0, "last": None}

        def fake_send(message: str, title: str = "Notification"):
            called["times"] += 1
            called["last"] = (message, title)

        monkeypatch.setattr(desktop, "send", fake_send)

        manager.send("desktop", "Hello", "Title")

        assert called["times"] == 1
        assert called["last"] == ("Hello", "Title")

    def test_broadcast_to_all(self, monkeypatch):
        """广播调用所有已注册渠道"""
        config = NotificationConfig(
            desktop=DesktopConfig(enabled=True),
            webhook=WebhookConfig(
                enabled=True,
                url="https://example.com/webhook",
                method="POST",
                message_format="JSON",
            ),
        )
        manager = ChannelManager(config)

        desktop = manager.get_channel("desktop")
        webhook = manager.get_channel("webhook")

        hits = {"desktop": 0, "webhook": 0}

        def fake_send_desktop(message: str, title: str = "Notification"):
            hits["desktop"] += 1

        def fake_send_webhook(message: str, title: str = "Notification"):
            hits["webhook"] += 1

        monkeypatch.setattr(desktop, "send", fake_send_desktop)
        monkeypatch.setattr(webhook, "send", fake_send_webhook)

        manager.broadcast("Msg", "T")

        assert hits["desktop"] == 1
        assert hits["webhook"] == 1
