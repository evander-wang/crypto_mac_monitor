"""
Desktop Notification Channel

桌面通知渠道实现，支持系统原生通知和第三方库。
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import platform
import subprocess
import time

from app.notifications_v2.channels.notification_channel_interface import INotificationChannel
from app.notifications_v2.notification_level import NotificationLevel
from app.utils import log_error, log_warn
from app.utils.logger import log_success


@dataclass
class DesktopConfig:
    """桌面通知配置"""

    enabled: bool = True
    use_system_notification: bool = True  # 优先使用系统通知
    notification_timeout: int = 5  # 通知显示时间（秒）
    app_name: str = "BTC Trading Bot"
    app_icon: Optional[str] = None

    # 声音设置
    enable_sound: bool = True
    sound_file: Optional[str] = None

    # 级别过滤
    min_level: NotificationLevel = NotificationLevel.INFO

    # 频率限制
    rate_limit_requests: int = 10
    rate_limit_window: int = 60  # 秒


class DesktopChannel(INotificationChannel):
    """
    桌面通知渠道

    支持系统原生通知和第三方库的桌面通知。
    """

    def __init__(self, **config: Any):
        """
        Initializes the DesktopChannel.

        Args:
            **config: Configuration parameters for the channel.
        """
        self.config = DesktopConfig(**config)
        self.channel_name = "desktop"
        self._system = platform.system()
        self._request_times: list[float] = []  # 频率限制时间戳记录（滑动窗口）

    def send(
        self,
        message: str,
        title: str = "Notification",
        level: NotificationLevel = NotificationLevel.INFO,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if not self.config.enabled:
            return False

        # 频率限制检查（滑动窗口，仅统计成功记录）
        if not self._check_rate_limit():
            log_warn("Desktop 发送频率超过限制", "DESKTOP_CHANNEL")
            return False

        try:
            if self.config.use_system_notification:
                self._send_system_notification(title, message)
                log_success(f"System notification sent: {title} - {message}", "DESKTOP_CHANNEL")
                self._record_request()
            else:
                log_warn("System notification is disabled.", "DESKTOP_CHANNEL")
                return False
            return True
        except Exception as e:
            log_error(f"Failed to send desktop notification: {e}", "DESKTOP_CHANNEL")
            return False

    def _send_system_notification(self, title: str, content: str):
        """发送系统通知"""
        try:
            if self._system == "Darwin":  # macOS
                script = f'''display notification "{content}" with title "{self.config.app_name}" subtitle "{title}"'''
                subprocess.run(["osascript", "-e", script], check=True)
            elif self._system == "Linux":
                subprocess.run(["notify-send", f"{title}", content], check=True)
            elif self._system == "Windows":
                # This is a simplified example. Windows notifications are more complex.
                log_warn(
                    "Windows system notifications not fully implemented in this version.",
                    "DESKTOP_CHANNEL",
                )
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            log_error(f"Failed to send system notification: {e}", "DESKTOP_CHANNEL")

    def is_enabled(self) -> bool:
        """检查通道是否启用"""
        return self.config.enabled

    def get_channel_name(self) -> str:
        """获取通道名称"""
        return self.channel_name

    def test_connection(self) -> bool:
        """测试通道连接"""
        try:
            # 发送一个测试通知
            if self.config.use_system_notification:
                if self._system == "Darwin":  # macOS
                    subprocess.run(
                        [
                            "osascript",
                            "-e",
                            'display notification "Test" with title "Test"',
                        ],
                        check=True,
                        capture_output=True,
                    )
                elif self._system == "Linux":
                    subprocess.run(["notify-send", "Test", "Test"], check=True, capture_output=True)
                return True
            return False
        except Exception:
            return False

    def update_config(self, config: Dict[str, Any]) -> None:
        """更新通道配置"""
        for key, value in config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    # 频率限制相关方法
    def _check_rate_limit(self) -> bool:
        """检查频率限制（滑动窗口）"""
        try:
            current_time = time.time()
            window_start = current_time - int(self.config.rate_limit_window)
            # 清理窗口外记录
            self._request_times = [t for t in self._request_times if t > window_start]
            # 判断是否超过限制
            return len(self._request_times) < int(self.config.rate_limit_requests)
        except Exception:
            # 容错：若异常则不阻塞发送
            return True

    def _record_request(self) -> None:
        """记录一次成功发送的时间戳"""
        try:
            self._request_times.append(time.time())
        except Exception:
            pass
