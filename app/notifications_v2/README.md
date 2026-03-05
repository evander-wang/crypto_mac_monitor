# 通知模块 V2 使用指南

## 概述

通知模块 V2 是一个现代化的、可扩展的通知系统，支持多种通知渠道和灵活的配置选项。

## 功能特性

- 🚀 **多渠道支持**: 桌面通知、Webhook、邮件、Telegram
- 🎯 **优先级管理**: 支持不同优先级的通知
- 📊 **统计功能**: 实时统计发送成功率和渠道状态
- 🔄 **异步处理**: 基于 asyncio 的高性能异步处理
- 🛠️ **依赖注入**: 使用 DI 容器进行模块解耦
- ⚙️ **灵活配置**: 支持 YAML 配置文件和环境变量

## 快速开始

### 1. 基本使用

```python
import asyncio
from core.di import DIContainer
from app.notifications_v2 import NotificationLevel
from app.notifications_v2.config.notification_config import (
    DEFAULT_NOTIFICATION_CONFIG,
    setup_notification_dependencies
)
from app.notifications_v2 import NotificationHandlerV2


async def main():
    # 配置初始化
    config = DEFAULT_NOTIFICATION_CONFIG
    config.desktop.enabled = True
    config.desktop.min_level = NotificationLevel.INFO

    # 依赖注入设置
    container = DIContainer()
    setup_notification_dependencies(container, config)

    # 获取通知处理器
    handler = container.get_service(NotificationHandlerV2)

    # 启动通知系统
    await handler.startup()

    try:
        # 发送通知
        await handler.send_info("测试消息", "测试模块")
        await handler.send_warning("警告消息", "测试模块")

        # 查看统计
        stats = handler.get_statistics()
        print(f"发送: {stats.total_sent}, 失败: {stats.total_failed}")

    finally:
        # 关闭系统
        await handler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
```

### 2. 独立运行示例

项目提供了两个现成的示例脚本：

```bash
# 快速测试
python test_notification_v2.py

# 完整功能演示
python run_notification_v2.py
```

## 支持的通知渠道

### 桌面通知 (Desktop)
- 支持 macOS 系统通知
- 自动检测 Plyer 库可用性
- 配置项：`enabled`, `min_level`

### Webhook 通知
- 支持 HTTP POST/GET 请求
- 可配置消息格式 (JSON/Form)
- 配置项：`url`, `method`, `message_format`, `headers`

### 邮件通知 (Email)
- 支持 SMTP 协议
- 支持多收件人
- 配置项：`smtp_server`, `smtp_port`, `username`, `password`

### Telegram 通知
- 支持 Bot API
- 支持多个聊天群组
- 配置项：`bot_token`, `chat_ids`

## 通知级别

- `DEBUG`: 调试信息
- `INFO`: 一般信息  
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

## 通知优先级

- `LOW`: 低优先级
- `NORMAL`: 普通优先级 (默认)
- `HIGH`: 高优先级
- `URGENT`: 紧急优先级

## 配置方式

### 1. 代码配置

```python
from app.notifications_v2.config.notification_config import NotificationConfig
from app.notifications_v2 import DesktopConfig

config = NotificationConfig(
    enabled=True,
    desktop=DesktopConfig(
        enabled=True,
        min_level=NotificationLevel.INFO
    )
)
```

### 2. YAML 配置文件

```yaml
# notification_v2_config.yaml
global:
  enabled: true
  min_level: "info"
  max_queue_size: 1000

channels:
  desktop:
    enabled: true
    min_level: "warning"
  
  webhook:
    enabled: false
    url: "https://your-webhook-url.com"
    method: "POST"
```

### 3. 环境变量

```bash
export NOTIFICATION_DESKTOP_ENABLED=true
export NOTIFICATION_WEBHOOK_URL=https://your-webhook.com
export NOTIFICATION_EMAIL_SMTP_SERVER=smtp.gmail.com
```

## API 参考

### NotificationHandlerV2

主要的通知处理器类，提供以下方法：

#### 基本方法
- `startup()`: 启动通知系统
- `shutdown()`: 关闭通知系统
- `get_statistics()`: 获取统计信息

#### 发送方法
- `send_info(title, message, data=None)`: 发送信息通知
- `send_warning(title, message, data=None)`: 发送警告通知
- `send_error(title, message, data=None)`: 发送错误通知
- `send_critical(title, message, data=None)`: 发送严重错误通知

#### 高级方法
- `send_notification_v2()`: 发送自定义通知
- `send_notification_message()`: 发送通知消息对象

### NotificationMessage

通知消息数据类：

```python
@dataclass
class NotificationMessage:
    title: str
    content: str
    level: NotificationLevel = NotificationLevel.INFO
    priority: NotificationPriority = NotificationPriority.NORMAL
    channels: Optional[List[str]] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)
```

## 故障排除

### 常见问题

1. **桌面通知不显示**
   - 检查系统通知权限
   - 确认 `min_level` 设置正确
   - 查看日志中的错误信息

2. **Webhook 通知失败**
   - 验证 URL 可访问性
   - 检查网络连接
   - 确认服务器响应格式

3. **邮件通知失败**
   - 验证 SMTP 服务器设置
   - 检查用户名密码
   - 确认端口和加密设置

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 性能优化

- 使用异步队列处理大量通知
- 配置合适的 `max_queue_size`
- 启用统计功能监控性能
- 根据需要调整重试策略

## 扩展开发

### 添加新的通知渠道

1. 继承 `BaseNotificationChannel`
2. 实现必要的方法
3. 在配置中注册新渠道
4. 更新依赖注入设置

### 自定义消息格式

通过 `data` 字段传递自定义数据：

```python
custom_data = {
    "source": "自定义模块",
    "type": "alert",
    "metadata": {"key": "value"}
}
await handler.send_info("标题", "内容", custom_data)
```

## 版本历史

- **v2.0**: 简洁的通知系统实现

## 许可证

本项目遵循项目根目录的许可证条款。