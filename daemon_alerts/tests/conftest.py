"""
共享 fixtures 和测试工具.
"""

import pytest
from unittest.mock import Mock
from daemon_alerts.event_alert_manager import EventAlertCondition, EventDrivenAlertManager
from app.notifications_v2 import NotificationManager
from datetime import datetime


@pytest.fixture
def mock_notification_manager():
    """提供模拟的通知管理器."""
    manager = Mock(spec=NotificationManager)
    manager.send = Mock(return_value=True)
    return manager


@pytest.fixture
def alert_manager(mock_notification_manager):
    """提供 EventDrivenAlertManager 实例."""
    manager = EventDrivenAlertManager(mock_notification_manager)
    yield manager
    # 清理
    manager.cleanup()


@pytest.fixture
def sample_price_condition():
    """提供示例价格告警条件."""
    return EventAlertCondition(
        id="price_above_50000",
        name="BTC 价格超过 50000",
        symbol="BTC-USDT-SWAP",
        condition_type="price_above",
        threshold=50000.0,
        enabled=True,
    )


@pytest.fixture
def sample_trend_condition():
    """提供示例趋势告警条件."""
    return EventAlertCondition(
        id="trend_change_btc",
        name="BTC 趋势变化",
        symbol="BTC-USDT-SWAP",
        condition_type="trend_change",
        threshold=0.0,
        enabled=True,
    )


@pytest.fixture
def sample_price_data():
    """提供示例价格数据."""
    return {"symbol": "BTC-USDT-SWAP", "price": 51000.0, "change_percent": 2.0, "timestamp": datetime.now()}


@pytest.fixture
def sample_trend_data():
    """提供示例趋势数据."""
    return {
        "symbol": "BTC-USDT-SWAP",
        "trend_info": {"direction": "up", "trend_type": "突破", "confidence": 0.85},
        "timestamp": datetime.now(),
    }
