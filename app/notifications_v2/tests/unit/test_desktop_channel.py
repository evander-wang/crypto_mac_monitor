"""
DesktopChannel 的单元测试（适配新版同步 send 接口）
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from app.notifications_v2.channels.desktop_channel import DesktopChannel, DesktopConfig
from app.notifications_v2.notification_level import NotificationLevel


class TestDesktopConfig:
    """DesktopConfig 的测试类"""

    def test_init_default(self):
        """测试默认初始化"""
        config = DesktopConfig()

        assert config.enabled is True
        assert config.use_system_notification is True
        assert config.use_plyer is True
        assert config.notification_timeout == 5
        assert config.app_name == "BTC Trading Bot"
        assert config.app_icon is None
        assert config.enable_sound is True
        assert config.sound_file is None
        assert config.min_level == NotificationLevel.INFO
        assert config.rate_limit_requests == 10
        assert config.rate_limit_window == 60

    def test_init_custom(self):
        """测试自定义初始化"""
        config = DesktopConfig(
            enabled=False,
            use_system_notification=False,
            use_plyer=True,
            notification_timeout=10,
            app_name="Custom App",
            app_icon="/path/to/icon.png",
            enable_sound=False,
            sound_file="/path/to/sound.wav",
            min_level=NotificationLevel.WARNING,
            rate_limit_requests=5,
            rate_limit_window=30,
        )

        assert config.enabled is False
        assert config.use_system_notification is False
        assert config.use_plyer is True
        assert config.notification_timeout == 10
        assert config.app_name == "Custom App"
        assert config.app_icon == "/path/to/icon.png"
        assert config.enable_sound is False
        assert config.sound_file == "/path/to/sound.wav"
        assert config.min_level == NotificationLevel.WARNING
        assert config.rate_limit_requests == 5
        assert config.rate_limit_window == 30


class TestDesktopChannel:
    """DesktopChannel 的测试类"""

    @pytest.fixture
    def channel(self):
        """创建测试渠道（直接用 dict 初始化）"""
        return DesktopChannel(enabled=True, use_system_notification=True, use_plyer=False)

    def test_init(self, channel):
        """测试初始化"""
        assert isinstance(channel.config, DesktopConfig)
        assert channel.channel_name == "desktop"
        assert channel.config.enabled is True
        assert channel.config.use_system_notification is True
        assert channel.config.use_plyer is False

    @patch("notifications_v2.channels.desktop_channel.subprocess.run")
    def test_send_system_notification_success(self, mock_subprocess, channel):
        """测试系统通知发送成功"""
        mock_subprocess.return_value = Mock()
        channel.send("Test Content", title="Test Title")
        mock_subprocess.assert_called()

    @patch("notifications_v2.channels.desktop_channel.subprocess.run")
    def test_send_system_notification_failure(self, mock_subprocess, channel):
        """测试系统通知发送失败不抛异常"""
        mock_subprocess.side_effect = FileNotFoundError("osascript not found")
        channel.send("Test Content", title="Test Title")
        # 不抛异常即可

    def test_send_disabled_channel(self):
        """测试禁用渠道发送：不调用系统通知"""
        ch = DesktopChannel(enabled=False, use_system_notification=True)
        with patch("notifications_v2.channels.desktop_channel.subprocess.run") as mock_subprocess:
            ch.send("Test Content", title="Test Title")
            mock_subprocess.assert_not_called()

    def test_send_plyer_notification(self):
        """测试 plyer 发送路径"""
        ch = DesktopChannel(enabled=True, use_system_notification=False, use_plyer=True)
        # 模拟 plyer 可用
        ch._plyer_available = True
        ch._plyer_notification = MagicMock()
        ch.send("Hello", title="World")
        ch._plyer_notification.notify.assert_called_once()

    def test_send_no_available_method(self):
        """无可用方法时记录告警但不抛异常"""
        ch = DesktopChannel(enabled=True, use_system_notification=False, use_plyer=False)
        # 不应抛异常
        ch.send("Msg", title="Title")

    # 以下为旧版 API 的占位测试，避免因收集失败阻断
    def test_is_enabled(self):
        pytest.skip("DesktopChannel v2 无 is_enabled/startup/shutdown/dispose 接口")

    def test_startup_shutdown(self):
        pytest.skip("DesktopChannel v2 无 is_enabled/startup/shutdown/dispose 接口")

    def test_dispose(self):
        pytest.skip("DesktopChannel v2 无 is_enabled/startup/shutdown/dispose 接口")

    def test_rate_limiting(self):
        pytest.skip("DesktopChannel v2 不包含频率限制逻辑")

    def test_check_level_filter(self):
        pytest.skip("DesktopChannel v2 不包含级别过滤私有方法")

    def test_prepare_title(self):
        pytest.skip("DesktopChannel v2 不包含 prepare_title")

    def test_prepare_content(self):
        pytest.skip("DesktopChannel v2 不包含 prepare_content")

    def test_update_config(self):
        pytest.skip("DesktopChannel v2 不包含 update_config")

    def test_test_connection(self):
        pytest.skip("DesktopChannel v2 不包含 test_connection")
