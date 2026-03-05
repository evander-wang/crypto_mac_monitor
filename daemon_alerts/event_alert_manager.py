"""
事件驱动的告警管理器

基于原有AlertManager，集成事件订阅模式
自动响应价格和趋势事件，实现实时告警处理
"""

import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from app.consts.consts import (
    EVENT_PRICE_UPDATE,
    EVENT_TREND_UPDATE,
    EVENT_ALERT_TRIGGERED,
    ALERT_LEVEL_INFO,
    ALERT_LEVEL_WARNING,
    ALERT_LEVEL_CRITICAL,
)
from app.models import AlertDTO
from app.events import get_alert_event_bus
from app.utils import log_info, log_warn, log_error, log_success
from app.notifications_v2 import NotificationManager


@dataclass
class EventAlertCondition:
    """事件告警条件"""

    id: str
    name: str
    symbol: str
    condition_type: str  # price_above, price_below, trend_change, volume_spike
    threshold: float
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    cooldown_seconds: int = 300  # 5分钟冷却时间

    def check_condition(self, data: Dict[str, Any]) -> bool:
        """检查告警条件是否满足"""
        try:
            # 检查冷却时间
            if self.last_triggered:
                elapsed = (datetime.now() - self.last_triggered).total_seconds()
                if elapsed < self.cooldown_seconds:
                    return False

            if self.condition_type == "price_above":
                price = data.get("price", 0)
                return price > self.threshold
            elif self.condition_type == "price_below":
                price = data.get("price", 0)
                return price < self.threshold
            elif self.condition_type == "change_percent_above":
                change_percent = data.get("change_percent", 0)
                return abs(change_percent) > self.threshold
            elif self.condition_type == "trend_change":
                trend_info = data.get("trend_info", {})
                trend_direction = trend_info.get("direction", "neutral")
                return trend_direction != "neutral"

            return False
        except Exception as e:
            log_error(f"检查告警条件失败 {self.id}: {e}", "EVENT_ALERT_MANAGER")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class EventDrivenAlertManager:
    """事件驱动的告警管理器：基于事件订阅模式的实时告警处理"""

    def __init__(self, notification_manager: NotificationManager):
        """
        初始化事件驱动告警管理器

        Args:
            notification_manager: 通知管理器实例
        """
        self.notification_manager: NotificationManager = notification_manager
        self.conditions: Dict[str, EventAlertCondition] = {}
        self.alert_history: List[AlertDTO] = []
        self.is_running = False
        self._lock = threading.Lock()

        # 事件总线
        self.event_bus = get_alert_event_bus()

        # 统计信息
        self.stats = {
            "total_alerts": 0,
            "alerts_by_level": {
                ALERT_LEVEL_INFO: 0,
                ALERT_LEVEL_WARNING: 0,
                ALERT_LEVEL_CRITICAL: 0,
            },
            "alerts_by_symbol": {},
            "last_alert_time": None,
        }

        # 订阅事件
        self._subscribe_to_events()

        log_success("事件驱动告警管理器初始化完成", "EVENT_ALERT_MANAGER")

    def _subscribe_to_events(self):
        """订阅事件"""
        self.event_bus.on(EVENT_PRICE_UPDATE, self._on_price_update)
        self.event_bus.on(EVENT_TREND_UPDATE, self._on_trend_update)

    def _on_price_update(self, price_data: Dict[str, Any]):
        """处理价格更新事件"""
        try:
            symbol = price_data.get("symbol")
            if not symbol:
                return

            # 检查该符号的所有告警条件
            for condition_id, condition in self.conditions.items():
                if condition.symbol == symbol and condition.enabled:
                    if condition.check_condition(price_data):
                        self._trigger_alert(condition, price_data, "price_update")

        except Exception as e:
            log_error(f"处理价格更新事件失败: {e}", "EVENT_ALERT_MANAGER")

    def _on_trend_update(self, trend_data: Dict[str, Any]):
        """处理趋势更新事件"""
        try:
            symbol = trend_data.get("symbol")
            if not symbol:
                return

            # 检查该符号的趋势相关告警条件
            for condition_id, condition in self.conditions.items():
                if condition.symbol == symbol and condition.enabled and condition.condition_type == "trend_change":
                    if condition.check_condition(trend_data):
                        self._trigger_alert(condition, trend_data, "trend_update")

        except Exception as e:
            log_error(f"处理趋势更新事件失败: {e}", "EVENT_ALERT_MANAGER")

    def _trigger_alert(self, condition: EventAlertCondition, data: Dict[str, Any], trigger_type: str):
        """触发告警"""
        try:
            with self._lock:
                # 更新条件的最后触发时间
                condition.last_triggered = datetime.now()

                # 确定告警级别
                alert_level = self._determine_alert_level(condition, data)

                # 创建告警DTO
                alert = AlertDTO(
                    alert_id=f"alert_{int(time.time() * 1000)}",
                    title=f"{condition.name} - {condition.symbol}",
                    symbol=condition.symbol,
                    level=alert_level,
                    condition_type=condition.condition_type,
                    message=self._format_alert_message(condition, data, trigger_type),
                    timestamp=datetime.now(),
                )

                # 添加到历史记录
                self.alert_history.append(alert)

                # 更新统计信息
                self._update_stats(alert)

                # 发送通知
                self._send_notification(alert)

                # 发布告警事件
                self.event_bus.emit(EVENT_ALERT_TRIGGERED, alert.to_dict())

                log_info(f"告警触发: {alert.alert_id}", "EVENT_ALERT_MANAGER")

        except Exception as e:
            log_error(f"触发告警失败: {e}", "EVENT_ALERT_MANAGER")

    def _determine_alert_level(self, condition: EventAlertCondition, data: Dict[str, Any]) -> str:
        """确定告警级别"""
        try:
            if condition.condition_type in ["price_above", "price_below"]:
                price = data.get("price", 0)
                if price > 100000:  # 示例：高价格为关键告警
                    return ALERT_LEVEL_CRITICAL
                elif price > 50000:
                    return ALERT_LEVEL_WARNING
                else:
                    return ALERT_LEVEL_INFO
            elif condition.condition_type == "change_percent_above":
                change_percent = abs(data.get("change_percent", 0))
                if change_percent > 10:
                    return ALERT_LEVEL_CRITICAL
                elif change_percent > 5:
                    return ALERT_LEVEL_WARNING
                else:
                    return ALERT_LEVEL_INFO
            elif condition.condition_type == "trend_change":
                return ALERT_LEVEL_WARNING

            return ALERT_LEVEL_INFO
        except Exception:
            return ALERT_LEVEL_INFO

    def _format_alert_message(self, condition: EventAlertCondition, data: Dict[str, Any], trigger_type: str) -> str:
        """格式化告警消息"""
        try:
            if condition.condition_type in ["price_above", "price_below"]:
                price = data.get("price", 0)
                change_percent = data.get("change_percent", 0)
                return f"价格 ${price:.2f} ({change_percent:+.2f}%) 触发条件: {condition.condition_type} {condition.threshold}"
            elif condition.condition_type == "change_percent_above":
                change_percent = data.get("change_percent", 0)
                return f"涨跌幅 {change_percent:+.2f}% 超过阈值 {condition.threshold}%"
            elif condition.condition_type == "trend_change":
                trend_info = data.get("trend_info", {})
                direction = trend_info.get("direction", "unknown")
                return f"趋势变化: {direction}"

            return f"告警条件 {condition.name} 已触发"
        except Exception:
            return f"告警条件 {condition.name} 已触发"

    def _send_notification(self, alert: AlertDTO):
        """发送通知"""
        try:
            if self.notification_manager:
                # 使用通知管理器发送
                self.notification_manager.send(message=alert.message, title=alert.title)
            else:
                log_warn("通知管理器未配置，跳过通知发送", "EVENT_ALERT_MANAGER")
        except Exception as e:
            log_error(f"发送通知失败: {e}", "EVENT_ALERT_MANAGER")

    def _update_stats(self, alert: AlertDTO):
        """更新统计信息"""
        try:
            self.stats["total_alerts"] += 1
            self.stats["alerts_by_level"][alert.level] += 1

            if alert.symbol not in self.stats["alerts_by_symbol"]:
                self.stats["alerts_by_symbol"][alert.symbol] = 0
            self.stats["alerts_by_symbol"][alert.symbol] += 1

            self.stats["last_alert_time"] = alert.timestamp
        except Exception as e:
            log_error(f"更新统计信息失败: {e}", "EVENT_ALERT_MANAGER")

    # ==================== 公共接口 ====================

    def add_condition(self, condition: EventAlertCondition) -> bool:
        """添加告警条件"""
        try:
            with self._lock:
                self.conditions[condition.id] = condition
                log_info(f"添加告警条件: {condition.name}", "EVENT_ALERT_MANAGER")
                return True
        except Exception as e:
            log_error(f"添加告警条件失败: {e}", "EVENT_ALERT_MANAGER")
            return False

    def remove_condition(self, condition_id: str) -> bool:
        """移除告警条件"""
        try:
            with self._lock:
                if condition_id in self.conditions:
                    del self.conditions[condition_id]
                    log_info(f"移除告警条件: {condition_id}", "EVENT_ALERT_MANAGER")
                    return True
                return False
        except Exception as e:
            log_error(f"移除告警条件失败: {e}", "EVENT_ALERT_MANAGER")
            return False

    def enable_condition(self, condition_id: str) -> bool:
        """启用告警条件"""
        try:
            with self._lock:
                if condition_id in self.conditions:
                    self.conditions[condition_id].enabled = True
                    log_info(f"启用告警条件: {condition_id}", "EVENT_ALERT_MANAGER")
                    return True
                return False
        except Exception as e:
            log_error(f"启用告警条件失败: {e}", "EVENT_ALERT_MANAGER")
            return False

    def disable_condition(self, condition_id: str) -> bool:
        """禁用告警条件"""
        try:
            with self._lock:
                if condition_id in self.conditions:
                    self.conditions[condition_id].enabled = False
                    log_info(f"禁用告警条件: {condition_id}", "EVENT_ALERT_MANAGER")
                    return True
                return False
        except Exception as e:
            log_error(f"禁用告警条件失败: {e}", "EVENT_ALERT_MANAGER")
            return False

    def get_conditions(self) -> List[Dict[str, Any]]:
        """获取所有告警条件"""
        try:
            with self._lock:
                return [condition.to_dict() for condition in self.conditions.values()]
        except Exception as e:
            log_error(f"获取告警条件失败: {e}", "EVENT_ALERT_MANAGER")
            return []

    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取告警历史"""
        try:
            with self._lock:
                recent_alerts = self.alert_history[-limit:] if limit > 0 else self.alert_history
                return [alert.to_dict() for alert in recent_alerts]
        except Exception as e:
            log_error(f"获取告警历史失败: {e}", "EVENT_ALERT_MANAGER")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            with self._lock:
                return self.stats.copy()
        except Exception as e:
            log_error(f"获取统计信息失败: {e}", "EVENT_ALERT_MANAGER")
            return {}

    def clear_history(self):
        """清空告警历史"""
        try:
            with self._lock:
                self.alert_history.clear()
                log_info("告警历史已清空", "EVENT_ALERT_MANAGER")
        except Exception as e:
            log_error(f"清空告警历史失败: {e}", "EVENT_ALERT_MANAGER")

    def start(self):
        """启动告警管理器"""
        try:
            self.is_running = True
            log_success("事件驱动告警管理器已启动", "EVENT_ALERT_MANAGER")
        except Exception as e:
            log_error(f"启动告警管理器失败: {e}", "EVENT_ALERT_MANAGER")

    def stop(self):
        """停止告警管理器"""
        try:
            self.is_running = False
            log_info("事件驱动告警管理器已停止", "EVENT_ALERT_MANAGER")
        except Exception as e:
            log_error(f"停止告警管理器失败: {e}", "EVENT_ALERT_MANAGER")

    def cleanup(self):
        """清理资源"""
        try:
            # 停止管理器
            self.stop()

            # 取消事件订阅
            self.event_bus.remove_listener(EVENT_PRICE_UPDATE, self._on_price_update)
            self.event_bus.remove_listener(EVENT_TREND_UPDATE, self._on_trend_update)

            log_info("事件驱动告警管理器已清理", "EVENT_ALERT_MANAGER")
        except Exception as e:
            log_error(f"清理告警管理器失败: {e}", "EVENT_ALERT_MANAGER")
