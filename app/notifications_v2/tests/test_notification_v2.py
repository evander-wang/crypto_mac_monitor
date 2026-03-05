#!/usr/bin/env python3
"""
Notifications V2 快速测试脚本

快速测试通知模块的基本功能
"""

from pathlib import Path
import os
import sys

from dependency_injector import containers, providers

from app.notifications_v2.channels.channel_manager import ChannelManager
from app.notifications_v2.config.notification_config import NotificationConfig
from app.notifications_v2.notification_manager import NotificationManager
from app.utils import log_error, log_info


# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# 设置一个默认的日志级别以避免潜在的错误
os.environ.setdefault("MACBAR_LOG_LEVEL", "INFO")


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    # Notifications v2
    notification_config = providers.Singleton(NotificationConfig.from_dict, config.notification)

    channel_manager = providers.Singleton(ChannelManager, config=notification_config)

    notification_manager = providers.Singleton(NotificationManager, channel_manager=channel_manager)


def quick_test():
    """快速测试通知系统"""
    log_info("🚀 快速测试 Notifications V2...", "TEST")

    try:
        # 1. 加载配置
        config_path = Path(__file__).parent.parent / "config" / "notifications_v2_config.yaml"
        log_info(f"加载配置文件: {config_path}")
        notification_config = NotificationConfig.from_file(str(config_path))

        # 2. 初始化DI容器
        container = Container()

        # 将加载的配置注入到容器中
        # to_dict() 方法需要确保能正确序列化所有嵌套的 dataclass
        config_dict = notification_config.to_dict()
        container.config.from_dict(config_dict)

        # 显式地覆盖 NotificationConfig 提供者
        container.notification_config.override(notification_config)

        log_info(
            f"✅ 配置加载完成，启用的渠道: {notification_config.get_enabled_channels()}",
            "TEST",
        )

        # 3. 从容器中获取 NotificationManager
        notification_manager = container.notification_manager()

        # 4. 发送测试通知
        log_info("📢 发送测试通知...", "TEST")

        notification_manager.send(
            "【mac_bac】这是一个来自 Notifications V2 的测试通知",
            title="测试通知 (INFO)",
        )
        log_info("信息通知: ✅ 成功", "TEST")

        notification_manager.send(
            "【mac_bac】这是一个警告级别的测试通知",
            title="警告测试 (WARNING)",
        )
        log_info("警告通知: ✅ 成功", "TEST")

        log_info("\n✅ 测试完成", "TEST")

    except Exception as e:
        log_error(f"错误: {e}", "TEST")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    quick_test()
