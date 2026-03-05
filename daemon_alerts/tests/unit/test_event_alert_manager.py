"""
EventDrivenAlertManager 单元测试.

测试事件驱动告警管理器的核心功能,包括:
- 初始化
- 告警条件管理
- 价格告警处理
- 趋势告警处理
- 告警历史和统计
- 生命周期管理
"""

import pytest
import time
from unittest.mock import Mock, patch, call
from datetime import datetime, timedelta
from daemon_alerts.event_alert_manager import EventAlertCondition, EventDrivenAlertManager
from app.consts.consts import (
    EVENT_PRICE_UPDATE,
    EVENT_TREND_UPDATE,
    ALERT_LEVEL_INFO,
    ALERT_LEVEL_WARNING,
    ALERT_LEVEL_CRITICAL,
)


class TestEventAlertCondition:
    """测试 EventAlertCondition 类."""

    def test_check_condition_price_above_true(self, sample_price_condition):
        """测试价格高于条件满足."""
        data = {"price": 51000.0}
        result = sample_price_condition.check_condition(data)

        assert result is True

    def test_check_condition_price_above_false(self, sample_price_condition):
        """测试价格高于条件不满足."""
        data = {"price": 49000.0}
        result = sample_price_condition.check_condition(data)

        assert result is False

    def test_check_condition_price_below_true(self):
        """测试价格低于条件满足."""
        condition = EventAlertCondition(
            id="price_below_50000",
            name="BTC 价格低于 50000",
            symbol="BTC-USDT-SWAP",
            condition_type="price_below",
            threshold=50000.0,
        )

        data = {"price": 49000.0}
        result = condition.check_condition(data)

        assert result is True

    def test_check_condition_cooldown(self, sample_price_condition):
        """测试冷却时间."""
        # 设置最近触发时间
        sample_price_condition.last_triggered = datetime.now()
        sample_price_condition.cooldown_seconds = 300

        data = {"price": 51000.0}
        result = sample_price_condition.check_condition(data)

        # 应该因为冷却时间而返回 False
        assert result is False

    def test_check_condition_cooldown_expired(self, sample_price_condition):
        """测试冷却时间过期."""
        # 设置很久以前的触发时间
        sample_price_condition.last_triggered = datetime.now() - timedelta(seconds=400)
        sample_price_condition.cooldown_seconds = 300

        data = {"price": 51000.0}
        result = sample_price_condition.check_condition(data)

        # 冷却时间已过,应该检查条件
        assert result is True

    def test_check_condition_change_percent(self):
        """测试涨跌幅条件."""
        condition = EventAlertCondition(
            id="change_percent_5",
            name="涨跌幅超过 5%",
            symbol="BTC-USDT-SWAP",
            condition_type="change_percent_above",
            threshold=5.0,
        )

        # 超过阈值
        data = {"change_percent": 6.0}
        assert condition.check_condition(data) is True

        # 低于阈值
        data = {"change_percent": 3.0}
        assert condition.check_condition(data) is False

    def test_check_condition_trend_change(self, sample_trend_condition):
        """测试趋势变化条件."""
        # 趋势不是 neutral
        data = {"trend_info": {"direction": "up"}}
        result = sample_trend_condition.check_condition(data)

        assert result is True

    def test_check_condition_trend_neutral(self, sample_trend_condition):
        """测试趋势为 neutral 时不触发."""
        data = {"trend_info": {"direction": "neutral"}}
        result = sample_trend_condition.check_condition(data)

        assert result is False

    def test_to_dict(self, sample_price_condition):
        """测试转换为字典."""
        result = sample_price_condition.to_dict()

        assert result["id"] == "price_above_50000"
        assert result["name"] == "BTC 价格超过 50000"
        assert result["symbol"] == "BTC-USDT-SWAP"
        assert result["threshold"] == 50000.0


class TestEventDrivenAlertManagerInit:
    """测试 EventDrivenAlertManager 初始化."""

    def test_init(self, alert_manager):
        """测试初始化."""
        assert alert_manager.notification_manager is not None
        assert alert_manager.conditions == {}
        assert alert_manager.alert_history == []
        assert alert_manager.is_running is False
        assert alert_manager.event_bus is not None

    def test_init_with_stats(self, alert_manager):
        """测试统计信息初始化."""
        stats = alert_manager.get_stats()

        assert "total_alerts" in stats
        assert stats["total_alerts"] == 0
        assert "alerts_by_level" in stats
        assert stats["alerts_by_level"][ALERT_LEVEL_INFO] == 0


class TestEventDrivenAlertManagerConditionManagement:
    """测试告警条件管理."""

    def test_add_condition(self, alert_manager, sample_price_condition):
        """测试添加告警条件."""
        result = alert_manager.add_condition(sample_price_condition)

        assert result is True
        assert "price_above_50000" in alert_manager.conditions

    def test_add_duplicate_condition(self, alert_manager, sample_price_condition):
        """测试添加重复条件."""
        alert_manager.add_condition(sample_price_condition)

        # 再次添加相同ID的条件
        result = alert_manager.add_condition(sample_price_condition)

        # 应该覆盖原有条件
        assert result is True
        assert "price_above_50000" in alert_manager.conditions

    def test_remove_condition(self, alert_manager, sample_price_condition):
        """测试移除告警条件."""
        alert_manager.add_condition(sample_price_condition)

        result = alert_manager.remove_condition("price_above_50000")

        assert result is True
        assert "price_above_50000" not in alert_manager.conditions

    def test_remove_nonexistent_condition(self, alert_manager):
        """测试移除不存在的条件."""
        result = alert_manager.remove_condition("nonexistent")

        assert result is False

    def test_enable_condition(self, alert_manager, sample_price_condition):
        """测试启用告警条件."""
        sample_price_condition.enabled = False
        alert_manager.add_condition(sample_price_condition)

        result = alert_manager.enable_condition("price_above_50000")

        assert result is True
        assert alert_manager.conditions["price_above_50000"].enabled is True

    def test_disable_condition(self, alert_manager, sample_price_condition):
        """测试禁用告警条件."""
        alert_manager.add_condition(sample_price_condition)

        result = alert_manager.disable_condition("price_above_50000")

        assert result is True
        assert alert_manager.conditions["price_above_50000"].enabled is False

    def test_get_conditions(self, alert_manager, sample_price_condition, sample_trend_condition):
        """测试获取所有条件."""
        alert_manager.add_condition(sample_price_condition)
        alert_manager.add_condition(sample_trend_condition)

        conditions = alert_manager.get_conditions()

        assert len(conditions) == 2
        assert all(isinstance(c, dict) for c in conditions)


class TestEventDrivenAlertManagerPriceAlerts:
    """测试价格告警."""

    def test_on_price_update_triggers_alert(self, alert_manager, sample_price_condition, sample_price_data):
        """测试价格更新触发告警."""
        alert_manager.add_condition(sample_price_condition)

        # 触发价格更新事件
        alert_manager._on_price_update(sample_price_data)

        # 验证告警历史被记录
        assert len(alert_manager.alert_history) == 1

        alert = alert_manager.alert_history[0]
        assert alert.symbol == "BTC-USDT-SWAP"
        assert alert.level in [ALERT_LEVEL_INFO, ALERT_LEVEL_WARNING, ALERT_LEVEL_CRITICAL]

    def test_on_price_update_no_match_symbol(self, alert_manager, sample_price_condition):
        """测试符号不匹配时不触发."""
        alert_manager.add_condition(sample_price_condition)

        # 不同符号的价格数据
        price_data = {
            "symbol": "ETH-USDT-SWAP",
            "price": 51000.0,
        }

        alert_manager._on_price_update(price_data)

        # 不应该触发告警
        assert len(alert_manager.alert_history) == 0

    def test_on_price_update_disabled_condition(self, alert_manager, sample_price_condition, sample_price_data):
        """测试禁用的条件不触发."""
        sample_price_condition.enabled = False
        alert_manager.add_condition(sample_price_condition)

        alert_manager._on_price_update(sample_price_data)

        # 不应该触发告警
        assert len(alert_manager.alert_history) == 0

    def test_on_price_update_sends_notification(self, alert_manager, sample_price_condition, sample_price_data):
        """测试发送通知."""
        alert_manager.add_condition(sample_price_condition)

        alert_manager._on_price_update(sample_price_data)

        # 验证通知被发送
        alert_manager.notification_manager.send.assert_called_once()

    def test_on_price_update_publishes_event(self, alert_manager, sample_price_condition, sample_price_data):
        """测试发布告警事件."""
        alert_manager.add_condition(sample_price_condition)

        # Mock emit 方法来捕获调用
        from unittest.mock import MagicMock

        original_emit = alert_manager.event_bus.emit
        mock_emit = MagicMock(side_effect=original_emit)

        # 临时替换
        alert_manager.event_bus.emit = mock_emit
        try:
            alert_manager._on_price_update(sample_price_data)
        finally:
            # 恢复原始方法
            alert_manager.event_bus.emit = original_emit

        # 验证事件被发布
        assert mock_emit.called
        # 检查调用参数
        call_args_list = [call[0][0] for call in mock_emit.call_args_list]
        assert any("alert" in str(arg) for arg in call_args_list)


class TestEventDrivenAlertManagerTrendAlerts:
    """测试趋势告警."""

    def test_on_trend_update_triggers_alert(self, alert_manager, sample_trend_condition, sample_trend_data):
        """测试趋势更新触发告警."""
        alert_manager.add_condition(sample_trend_condition)

        alert_manager._on_trend_update(sample_trend_data)

        # 验证告警被触发
        assert len(alert_manager.alert_history) == 1

        alert = alert_manager.alert_history[0]
        assert alert.symbol == "BTC-USDT-SWAP"
        assert alert.condition_type == "trend_change"

    def test_on_trend_update_no_match_condition_type(self, alert_manager, sample_price_condition, sample_trend_data):
        """测试条件类型不匹配时不触发."""
        alert_manager.add_condition(sample_price_condition)

        alert_manager._on_trend_update(sample_trend_data)

        # price_above 条件不应该被趋势更新触发
        assert len(alert_manager.alert_history) == 0


class TestEventDrivenAlertManagerHistoryAndStats:
    """测试告警历史和统计."""

    def test_get_alert_history(self, alert_manager, sample_price_condition, sample_price_data):
        """测试获取告警历史."""
        alert_manager.add_condition(sample_price_condition)

        # 触发两次告警(使用不同的条件以避免冷却时间)
        condition2 = EventAlertCondition(
            id="price_above_52000",
            name="BTC 价格超过 52000",
            symbol="BTC-USDT-SWAP",
            condition_type="price_above",
            threshold=52000.0,
        )
        alert_manager.add_condition(condition2)

        alert_manager._on_price_update(sample_price_data)
        sample_price_data["price"] = 53000.0
        alert_manager._on_price_update(sample_price_data)

        history = alert_manager.get_alert_history()

        assert len(history) == 2
        assert all(isinstance(alert, dict) for alert in history)

    def test_get_alert_history_with_limit(self, alert_manager, sample_price_condition, sample_price_data):
        """测试限制历史记录数量."""
        # 添加多个不同的条件以避免冷却时间
        for i in range(5):
            condition = EventAlertCondition(
                id=f"price_above_{50000 + i * 1000}",
                name=f"BTC 价格超过 {50000 + i * 1000}",
                symbol="BTC-USDT-SWAP",
                condition_type="price_above",
                threshold=float(50000 + i * 1000),
            )
            alert_manager.add_condition(condition)

        # 触发多次告警
        for i in range(5):
            sample_price_data["price"] = float(50000 + i * 1000 + 500)
            alert_manager._on_price_update(sample_price_data)

        history = alert_manager.get_alert_history(limit=3)

        assert len(history) == 3

    def test_get_stats(self, alert_manager, sample_price_condition, sample_price_data):
        """测试获取统计信息."""
        alert_manager.add_condition(sample_price_condition)

        alert_manager._on_price_update(sample_price_data)

        stats = alert_manager.get_stats()

        assert stats["total_alerts"] == 1
        assert stats["alerts_by_symbol"]["BTC-USDT-SWAP"] == 1
        assert stats["last_alert_time"] is not None

    def test_clear_history(self, alert_manager, sample_price_condition, sample_price_data):
        """测试清空历史."""
        alert_manager.add_condition(sample_price_condition)

        alert_manager._on_price_update(sample_price_data)
        assert len(alert_manager.alert_history) > 0

        alert_manager.clear_history()

        assert len(alert_manager.alert_history) == 0


class TestEventDrivenAlertManagerLifecycle:
    """测试生命周期管理."""

    def test_start(self, alert_manager):
        """测试启动."""
        alert_manager.start()

        assert alert_manager.is_running is True

    def test_stop(self, alert_manager):
        """测试停止."""
        alert_manager.start()
        alert_manager.stop()

        assert alert_manager.is_running is False

    def test_cleanup_removes_listeners(self, alert_manager):
        """测试清理移除事件监听器."""
        alert_manager.cleanup()

        # 验证 is_running 为 False
        assert alert_manager.is_running is False


class TestEventDrivenAlertManagerAlertLevel:
    """测试告警级别确定."""

    def test_determine_alert_level_high_price(self, alert_manager, sample_price_condition):
        """测试高价格触发关键告警."""
        data = {"price": 120000.0}

        level = alert_manager._determine_alert_level(sample_price_condition, data)

        assert level == ALERT_LEVEL_CRITICAL

    def test_determine_alert_level_medium_price(self, alert_manager, sample_price_condition):
        """测试中等价格触发警告告警."""
        data = {"price": 60000.0}

        level = alert_manager._determine_alert_level(sample_price_condition, data)

        assert level == ALERT_LEVEL_WARNING

    def test_determine_alert_level_low_price(self, alert_manager, sample_price_condition):
        """测试低价格触发信息告警."""
        data = {"price": 30000.0}

        level = alert_manager._determine_alert_level(sample_price_condition, data)

        assert level == ALERT_LEVEL_INFO

    def test_determine_alert_level_change_percent_critical(self, alert_manager):
        """测试大幅涨跌幅触发关键告警."""
        condition = EventAlertCondition(
            id="change_1",
            name="涨跌幅",
            symbol="BTC-USDT-SWAP",
            condition_type="change_percent_above",
            threshold=5.0,
        )

        data = {"change_percent": 12.0}

        level = alert_manager._determine_alert_level(condition, data)

        assert level == ALERT_LEVEL_CRITICAL

    def test_determine_alert_level_trend_change(self, alert_manager, sample_trend_condition):
        """测试趋势变化触发警告."""
        data = {"trend_info": {"direction": "up"}}

        level = alert_manager._determine_alert_level(sample_trend_condition, data)

        assert level == ALERT_LEVEL_WARNING
