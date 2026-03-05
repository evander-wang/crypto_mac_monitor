"""
Notification Manager V2 - Refactored for Dependency Injection
"""

from app.consts.consts import LOGGER_NOTIFICATION_MANAGER_PREFIX
from app.utils import log_debug, log_error, log_info

from .channels.channel_manager import ChannelManager


class NotificationManager:
    """
    Manages the routing of notifications to different channels.
    This version is simplified to work with the dependency injection container.
    """

    def __init__(self, channel_manager: ChannelManager):
        """
        Initializes the NotificationManager.

        Args:
            channel_manager: The manager for notification channels, injected by the container.
        """
        self.channel_manager = channel_manager
        log_info("NotificationManager V2 (DI) initialized.", LOGGER_NOTIFICATION_MANAGER_PREFIX)

    def send(self, message: str, title: str = "Notification"):
        """
        Sends a notification to all enabled channels.

        Args:
            message: The message content to send.
            title: The title of the notification.
        """
        try:
            # Channels currently only accept 'message'; 'title' retained for API compatibility
            self.channel_manager.broadcast(message)
            log_debug("Notification broadcast to all enabled channels.", LOGGER_NOTIFICATION_MANAGER_PREFIX)
        except Exception as e:
            log_error(f"Failed to broadcast notification: {e}", LOGGER_NOTIFICATION_MANAGER_PREFIX)
