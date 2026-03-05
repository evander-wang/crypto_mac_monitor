"""
NotificationConfig 测试（仅保留 desktop/webhook 渠道）
"""

import os
import tempfile

import pytest

from app.notifications_v2.channels.desktop_channel import DesktopConfig
from app.notifications_v2.channels.webhook_channel import WebhookConfig
from app.notifications_v2.config.notification_config import (
    NotificationConfig,
)
from app.notifications_v2.notification_level import NotificationLevel


class TestNotificationConfig:
    """NotificationConfig 测试类"""

    @pytest.fixture
    def sample_config_dict(self):
        """示例配置字典（仅 desktop/webhook）"""
        return {
            "enabled": True,
            "min_level": "info",
            "max_queue_size": 500,
            "queue_timeout": 15.0,
            "desktop": {
                "enabled": True,
                "use_system_notification": True,
                "use_plyer": False,
                "notification_timeout": 5,
                "app_name": "Test App",
                "app_icon": None,
                "enable_sound": True,
                "sound_file": None,
                "min_level": "warning",
                "rate_limit_requests": 10,
                "rate_limit_window": 60,
            },
            "webhook": {
                "enabled": False,
                "url": "https://example.com/webhook",
                "method": "POST",
                "message_format": "json",
            },
            "enable_statistics": True,
            "enable_health_check": True,
            "health_check_interval": 300.0,
            "enable_events": True,
            "auto_retry": True,
            "max_retry_attempts": 3,
            "retry_delay": 5.0,
        }

    def test_init_default(self):
        """测试默认初始化"""
        config = NotificationConfig()

        assert config.enabled is True
        assert config.min_level == NotificationLevel.INFO
        assert config.max_queue_size == 1000
        assert config.queue_timeout == 30.0
        assert config.webhook is None
        assert config.desktop is None

    def test_from_dict(self, sample_config_dict):
        """测试从字典创建配置"""
        config = NotificationConfig.from_dict(sample_config_dict)

        assert config.enabled is True
        assert config.min_level == NotificationLevel.INFO
        assert config.max_queue_size == 500
        assert config.queue_timeout == 15.0

        assert isinstance(config.desktop, DesktopConfig)
        assert config.desktop.enabled is True
        assert config.desktop.app_name == "Test App"

        assert isinstance(config.webhook, WebhookConfig)
        assert config.webhook.enabled is False
        assert config.webhook.url == "https://example.com/webhook"

    def test_from_dict_partial(self):
        """测试从部分字典创建配置"""
        partial_dict = {
            "enabled": False,
            "max_queue_size": 200,
            "desktop": {"app_name": "Partial App"},
        }

        config = NotificationConfig.from_dict(partial_dict)

        assert config.enabled is False
        assert config.max_queue_size == 200
        assert isinstance(config.desktop, DesktopConfig)
        assert config.desktop.app_name == "Partial App"
        # 其他值应该使用默认值
        assert config.min_level == NotificationLevel.INFO
        assert config.desktop.enabled is True

    def test_to_dict(self, sample_config_dict):
        """测试转换为字典"""
        config = NotificationConfig.from_dict(sample_config_dict)
        result_dict = config.to_dict()

        assert "enabled" in result_dict
        assert "min_level" in result_dict
        assert "desktop" in result_dict
        assert "webhook" in result_dict

        assert result_dict["enabled"] is True
        assert result_dict["min_level"] == "info"
        assert result_dict["max_queue_size"] == 500
        assert result_dict["desktop"]["app_name"] == "Test App"
        assert result_dict["webhook"]["url"] == "https://example.com/webhook"

    def test_from_file(self, sample_config_dict):
        """测试从文件加载配置"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            import yaml

            yaml.dump(sample_config_dict, f)
            temp_file = f.name

        try:
            config = NotificationConfig.from_file(temp_file)
            assert config.enabled is True
            assert config.max_queue_size == 500
            assert config.desktop.app_name == "Test App"
        finally:
            os.unlink(temp_file)

    def test_from_file_not_found(self):
        """测试文件不存在的情况"""
        with pytest.raises(FileNotFoundError):
            NotificationConfig.from_file("non_existent_file.yaml")

    def test_save_to_file(self, sample_config_dict):
        """测试保存配置到文件"""
        config = NotificationConfig.from_dict(sample_config_dict)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            temp_file = f.name

        try:
            config.save_to_file(temp_file)

            # 验证文件存在且可以读取
            loaded_config = NotificationConfig.from_file(temp_file)
            assert loaded_config.enabled == config.enabled
            assert loaded_config.max_queue_size == config.max_queue_size
            assert loaded_config.desktop.app_name == config.desktop.app_name
        finally:
            os.unlink(temp_file)

    def test_get_enabled_channels(self, sample_config_dict):
        """测试获取启用的渠道"""
        # 测试没有启用渠道的情况
        config = NotificationConfig()
        enabled_channels = config.get_enabled_channels()
        assert enabled_channels == []

        # 测试有启用渠道的情况
        sample_config_dict["desktop"]["enabled"] = True
        sample_config_dict["webhook"]["enabled"] = True
        config = NotificationConfig.from_dict(sample_config_dict)
        enabled_channels = config.get_enabled_channels()
        assert "desktop" in enabled_channels
        assert "webhook" in enabled_channels
        assert len(enabled_channels) == 2

    def test_validate_config(self, sample_config_dict):
        """测试配置验证"""
        config = NotificationConfig.from_dict(sample_config_dict)

        # 正常配置应该验证通过
        assert config.validate() is True

        # 测试无效的队列大小
        config.max_queue_size = 0
        assert config.validate() is False

        # 测试无效的队列超时
        config.max_queue_size = 1000
        config.queue_timeout = 0
        assert config.validate() is False

        # 测试无效的健康检查间隔
        config.queue_timeout = 30.0
        config.health_check_interval = 0
        assert config.validate() is False

    def test_validate_webhook_config(self):
        """测试 Webhook 配置验证"""
        config = NotificationConfig(webhook=WebhookConfig(enabled=True, url="", method="POST", message_format="JSON"))

        # 没有URL应该验证失败
        assert config.validate() is False

        # 有URL应该验证通过
        config.webhook.url = "https://example.com/webhook"
        assert config.validate() is True

    def test_to_yaml(self, sample_config_dict):
        """测试配置转 YAML"""
        config = NotificationConfig.from_dict(sample_config_dict)
        yaml_str = config.to_yaml()
        assert isinstance(yaml_str, str)
        assert "desktop" in yaml_str
        assert "webhook" in yaml_str

    def test_from_yaml(self, sample_config_dict):
        """测试从 YAML 读取配置"""
        import yaml

        yaml_str = yaml.safe_dump(sample_config_dict, default_flow_style=False, allow_unicode=True)
        new_config = NotificationConfig.from_yaml(yaml_str)
        assert isinstance(new_config.desktop, DesktopConfig)
        assert isinstance(new_config.webhook, WebhookConfig)
        assert new_config.desktop.app_name == sample_config_dict["desktop"]["app_name"]
