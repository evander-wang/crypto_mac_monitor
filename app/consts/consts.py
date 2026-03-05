# 做一个map btc->大饼
ONE = "一"
TWO = "二"

CRYPTO_MAP = {
    "BTC": ONE,
    "ETH": TWO,
    "BTC-USDT": ONE,
    "ETH-USDT": TWO,
    "BTC-USDT-SWAP": ONE,
    "ETH-USDT-SWAP": TWO,
    "PositionSide.LONG": "多",  # 持仓方向
    "PositionSide.SHORT": "空",  # 持仓方向
    "OrderType.LIMIT": "限价",  # 订单类型
    "OrderType.MARKET": "市价",  # 订单类型
    "OrderType.STOP": "止损",  # 订单类型
    "OrderType.STOP_LIMIT": "止损限价",  # 订单类型
    "OrderType.TAKE_PROFIT": "止盈",  # 订单类型
    "OrderType.TAKE_PROFIT_LIMIT": "止盈限价",  # 订单类型
    "OrderType.LIMIT_MAKER": "限价挂单",  # 订单类型
    "OrderStatus.OPEN": "已提交",  # 订单状态
    "OrderStatus.PARTIALLY_FILLED": "部分成交",  # 订单状态
    "OrderStatus.FILLED": "已成交",  # 订单状态
    "OrderStatus.CANCELED": "已取消",  # 订单状态
    "OrderStatus.REJECTED": "已拒绝",  # 订单状态
    "OrderStatus.EXPIRED": "已过期",  # 订单状态
    "OrderStatus.PENDING_CANCEL": "待取消",  # 订单状态
    "OrderStatus.PENDING_NEW": "待提交",  # 订单状态
}

# ==================== 事件主题常量 ====================
# 数据更新事件
EVENT_PRICE_UPDATE = "price.update"  # 价格更新事件
EVENT_TREND_UPDATE = "trend.update"  # 趋势更新事件
EVENT_KLINE_UPDATE = "kline.update"  # K线更新事件
EVENT_DATA_READY = "data.ready"  # 数据就绪事件
EVENT_DATA_ERROR = "data.error"  # 数据错误事件

# UI 事件
EVENT_WORLD_CLOCK_UPDATE = "ui.world_clock.update"  # 世界时钟文本更新事件
EVENT_UI_ENABLE_WINDOW = "ui.window.enable"  # 启用/刷新悬浮窗事件
EVENT_ORDER_UPDATE = "ui.order.update"  # 订单状态更新事件
EVENT_POSITION_UPDATE = "ui.position.update"  # 仓位状态更新事件

# 告警事件
EVENT_ALERT_TRIGGERED = "alert.triggered"  # 告警触发事件

# 通知事件
EVENT_NOTIFICATION_SENT = "notification.sent"  # 通知发送事件
EVENT_NOTIFICATION_FAILED = "notification.failed"  # 通知发送失败事件


# ==================== 告警级别常量 ====================
ALERT_LEVEL_INFO = "info"
ALERT_LEVEL_WARNING = "warning"
ALERT_LEVEL_CRITICAL = "critical"

# ==================== 组件名称常量 ====================
COMPONENTS_EVENT_BUS = "event_bus"  # 事件总线
COMPONENTS_CONFIG = "config"  # 配置管理器
COMPONENTS_ANALYSIS_CACHE = "analysis_cache"  # 分析缓存
COMPONENTS_CACHE_LOCK = "cache_lock"  # 缓存锁
COMPONENTS_DATA_MANAGER = "data_manager"  # 数据管理器
COMPONENTS_NOTIFICATION_MANAGER = "notification_manager"  # 通知管理器
COMPONENTS_ALERT_MANAGER = "alert_manager"  # 告警管理器
COMPONENTS_TREND_ANALYZER = "trend_analyzer"  # 趋势分析器
COMPONENTS_REALTIME_HELPER = "realtime_helper"  # 实时辅助工具
COMPONENTS_FLOATING_WINDOW = "floating_window"  # 浮动窗口
COMPONENTS_ANALYSIS_RUNNER = "analysis_runner"  # 分析运行器
COMPONENTS_THREAD_MEMORY_DATA_CACHE_MANAGER = "thread_memory_data_cache_manager"  # 线程内存数据缓存管理器
COMPONENTS_STATUS_MENU = "status_menu"  # 状态栏菜单管理器
COMPONENTS_WORLD_CLOCK_SERVICE = "world_clock_service"  # 世界时钟服务
COMPONENTS_APP_SERVICES = "app_services"  # 应用生命周期服务
COMPONENTS_ORDER_MANAGER = "order_manager"  # 订单管理器
COMPONENTS_POSITION_MANAGER = "position_manager"  # 仓位管理器
COMPONENTS_LIMIT_ORDER_SERVICE = "limit_order_service"  # 限价卖出服务


# ==================logger section======================
LOGGER_UI_EVENT_PUMP_PREFIX = "LOG_UI_BRIDGE"  # UI事件泵日志前缀
LOGGER_EVENT_BUS_PREFIX = "LOG_EVENT_BUS"  # 事件总线日志前缀
LOGGER_CONFIG_MANAGER_PREFIX = "LOG_CONFIG_MANAGER"  # 配置管理器日志前缀
LOGGER_NOTIFICATION_MANAGER_PREFIX = "LOG_NOTIFICATION_MANAGER"  # 通知管理器日志前缀
LOGGER_SCHEDULER_PREFIX = "LOG_SCHEDULER"  # 调度器日志前缀

# ==================== 指标告警阈值与设置 ====================
# 5m 三倍冲击告警百分比阈值（例如 >= 2.0% 触发）
ALERT_IMPULSE_PCT_THRESHOLD = 1.5
# 5m 连续突破最少连续根数（例如 >= 3 根）
ALERT_BREAKOUT_CONSECUTIVE_MIN = 3
# 5m 连续突破累计变化百分比阈值（例如 >= 1.0%）
ALERT_BREAKOUT_CHANGE_PCT_MIN = 1.0
# 1m 实时区间波动百分比阈值（例如 >= 3.0%）
ALERT_REALTIME_RANGE_PCT_MIN = 2.0
# 告警发送冷却时间（秒），避免重复轰炸
ALERT_COOLDOWN_SEC = 60
# 告警标题前缀
ALERT_NOTIFICATION_TITLE_PREFIX = "指标告警"

SYS_TYPE_MAC_OS = "macos"
