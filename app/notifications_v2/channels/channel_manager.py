from dataclasses import dataclass
from typing import Dict, Optional
import dataclasses

from app.notifications_v2.channels.desktop_channel import DesktopChannel
from app.notifications_v2.channels.email_channel import EmailChannel
from app.notifications_v2.channels.notification_channel_interface import INotificationChannel
from app.notifications_v2.channels.webhook_channel import WebhookChannel
from app.notifications_v2.config.notification_config import NotificationConfig
from app.utils import log_warn


@dataclass
class ChannelStatistics:
    total_sent: int = 0
    total_failed: int = 0


class ChannelManager:
    def __init__(self, config: NotificationConfig):
        self.config = config
        self.channels: Dict[str, INotificationChannel] = {}
        self.statistics = ChannelStatistics()
        self._register_channels()

    def _register_channels(self):
        if self.config.desktop and self.config.desktop.enabled:
            self.channels["desktop"] = DesktopChannel(**dataclasses.asdict(self.config.desktop))
        if self.config.webhook and self.config.webhook.enabled:
            self.channels["webhook"] = WebhookChannel(**dataclasses.asdict(self.config.webhook))
        if getattr(self.config, "email", None) and self.config.email.enabled:
            self.channels["email"] = EmailChannel(**dataclasses.asdict(self.config.email))

    def get_channel(self, name: str) -> Optional[INotificationChannel]:
        return self.channels.get(name)

    def send(self, channel_name: str, message: str) -> bool:
        channel = self.get_channel(channel_name)
        if not channel:
            log_warn(f"渠道 '{channel_name}' 未注册或未启用", "CHANNEL_MANAGER")
            self.statistics.total_failed += 1
            return False
        success = channel.send(message)
        if success:
            self.statistics.total_sent += 1
        else:
            self.statistics.total_failed += 1
        return success

    def broadcast(self, message: str) -> Dict[str, bool]:
        if not self.channels:
            log_warn("没有可用的通知渠道进行广播", "CHANNEL_MANAGER")
            return {}
        results = {}
        for name, channel in self.channels.items():
            results[name] = channel.send(message)
            if results[name]:
                self.statistics.total_sent += 1
            else:
                self.statistics.total_failed += 1
        return results
