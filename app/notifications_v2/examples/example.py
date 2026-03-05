"""
Notifications V2 Usage Examples

通知系统V2使用示例，展示如何使用新的通知系统。
"""

from pathlib import Path
import asyncio
import os
import sys


# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from dependency_injector import containers, providers

from app.notifications_v2.channels.channel_manager import ChannelManager
from app.notifications_v2.channels.webhook_channel import AuthType, MessageFormat
from app.notifications_v2.config import (
    DesktopConfig,
    WebhookConfig,
)
from app.notifications_v2.config.notification_config import NotificationConfig
from app.notifications_v2.notification_manager import NotificationManager


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    # Notifications v2
    notification_config = providers.Singleton(NotificationConfig.from_dict, config.notification)

    channel_manager = providers.Singleton(ChannelManager, config=notification_config)

    notification_manager = providers.Singleton(NotificationManager, channel_manager=channel_manager)


async def basic_usage_example():
    """基本使用示例"""
    print("=== 基本使用示例 ===")

    # 1. 创建配置
    config = NotificationConfig(
        webhook=(
            WebhookConfig(
                enabled=True,
                url=os.getenv("WEBHOOK_URL", "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"),
                message_format=MessageFormat.DINGTALK,
            )
        ),
        desktop=DesktopConfig(
            enabled=True,
        ),
    )

    # 2. 设置依赖注入
    container = Container()
    container.config.from_dict({"notification": config.to_dict()})

    # 获取通知处理器
    handler = container.notification_manager()

    try:
        # 5. 发送各种级别的通知
        handler.send(
            title="系统启动",
            message="【mac_bar】BTC交易机器人已成功启动",
        )

        handler.send(
            title="价格警告",
            message="【mac_bar】BTC价格突破关键阻力位 $50,000",
        )

        handler.send(
            title="交易执行",
            message="【mac_bar】买入订单已成功执行",
        )

        # 6. 使用便捷方法
        handler.send(title="【mac_bar】信息通知", message="【mac_bar】这是一条信息通知")
        handler.send(title="【mac_bar】警告通知", message="【mac_bar】这是一条警告通知")
        handler.send(title="【mac_bar】错误通知", message="【mac_bar】这是一条错误通知")

        print("基本通知发送完成")

    finally:
        # 7. 关闭系统
        pass


async def advanced_configuration_example():
    """高级配置示例"""
    print("\n=== 高级配置示例 ===")

    # 创建完整配置
    config = NotificationConfig(
        webhook=(
            WebhookConfig(
                enabled=bool(os.getenv("WEBHOOK_URL")),
                url=os.getenv("WEBHOOK_URL", ""),
                method="POST",
                message_format=MessageFormat.DINGTALK,  # 使用Slack格式
                auth_type=AuthType.NONE,
                auth_token=os.getenv("WEBHOOK_TOKEN", ""),
                rate_limit_requests=20,
                rate_limit_window=60,
            )
            if os.getenv("WEBHOOK_URL")
            else None
        ),
        # 桌面通知配置
        desktop=DesktopConfig(
            enabled=True,
        ),
    )

    # 设置系统
    container = Container()
    container.config.from_dict({"notification": config.to_dict()})
    handler = container.notification_manager()

    try:
        # 发送富文本通知
        handler.send(
            title="交易信号分析",
            message="""
技术指标分析结果：

📈 RSI: 65.2 (中性偏多)
📊 MACD: 金叉信号
🎯 支撑位: $48,500
🚀 阻力位: $51,200

建议：谨慎做多，注意风险控制
            """.strip(),
        )

    finally:
        pass


async def event_handling_example():
    """事件处理示例"""
    print("\n=== 事件处理示例 ===")

    config = NotificationConfig(
        desktop=DesktopConfig(enabled=True),
    )

    container = Container()
    container.config.from_dict({"notification": config.to_dict()})
    handler = container.notification_manager()

    try:
        # 发送通知，观察事件
        handler.send(
            title="事件测试",
            message="这是一条用于测试事件系统的通知",
        )

        # 等待事件处理
        await asyncio.sleep(1)

    finally:
        pass


async def error_handling_example():
    """错误处理示例"""
    print("\n=== 错误处理示例 ===")

    # 创建有问题的配置
    config = NotificationConfig(
        webhook=WebhookConfig(
            enabled=True,
            url="http://invalid-url-that-does-not-exist.com/webhook",
        )
    )

    container = Container()
    container.config.from_dict({"notification": config.to_dict()})
    handler = container.notification_manager()

    try:
        # 尝试发送到无效的webhook
        handler.send(
            title="错误测试",
            message="这条通知应该会失败",
        )

    finally:
        pass


async def configuration_management_example():
    """配置管理示例"""
    print("\n=== 配置管理示例 ===")

    # 1. 从YAML文件加载配置
    config_file = Path(__file__).parent.parent / "config" / "notifications_v2_config.yaml"
    if config_file.exists():
        config = NotificationConfig.from_file(config_file)
        print("从YAML文件加载配置")
    else:
        # 2. 创建默认配置
        config = NotificationConfig(desktop=DesktopConfig(enabled=True))
        print("使用默认配置")

    # 4. 保存配置到文件
    output_file = Path("config/notifications_v2_example_output.yaml")
    config.save_to_file(output_file)
    print(f"配置已保存到 {output_file}")

    # 5. 显示启用的渠道
    enabled_channels = config.get_enabled_channels()
    print(f"启用的渠道: {enabled_channels}")


async def main():
    """主函数"""
    print("通知系统V2使用示例")
    print("=" * 50)

    try:
        # 运行各种示例
        await basic_usage_example()
        await advanced_configuration_example()
        await event_handling_example()
        await error_handling_example()
        await configuration_management_example()

        print("\n所有示例运行完成！")

    except Exception as e:
        print(f"示例运行出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # 设置环境变量示例（可选）
    # os.environ['WEBHOOK_URL'] = 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
    # os.environ['TELEGRAM_BOT_TOKEN'] = 'YOUR_BOT_TOKEN'
    # os.environ['TELEGRAM_CHAT_IDS'] = 'YOUR_CHAT_ID'

    asyncio.run(main())
