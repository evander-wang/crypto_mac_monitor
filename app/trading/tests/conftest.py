"""
Trading module test configuration and shared fixtures.
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock
import time

import pytest


@pytest.fixture
def mock_exchange():
    """提供模拟的交易所实例."""
    exchange = Mock()
    exchange.apiKey = "test_api_key"
    exchange.fetch_positions = Mock(return_value=[])
    exchange.fetch_open_orders = Mock(return_value=[])
    exchange.load_markets = Mock(return_value={})
    return exchange


@pytest.fixture
def sample_position_data():
    """提供示例仓位数据."""
    return {
        "symbol": "BTC-USDT-SWAP",
        "side": "long",
        "size": 0.5,
        "contracts": 0.5,
        "contractSize": 0.01,
        "entryPrice": 50000.0,
        "markPrice": 51000.0,
        "unrealizedPnl": 50.0,
        "percentage": 1.0,
        "maintenanceMargin": 10.0,
        "initialMargin": 100.0,
        "timestamp": int(time.time() * 1000),
        "info": {},
    }


@pytest.fixture
def sample_order_data():
    """提供示例订单数据."""
    return {
        "id": "12345678",
        "symbol": "BTC-USDT-SWAP",
        "type": "limit",
        "side": "buy",
        "amount": 0.1,
        "price": 50000.0,
        "filled": 0.1,
        "remaining": 0.0,
        "status": "filled",
        "timestamp": int(time.time() * 1000),
        "average": 50000.0,
        "info": {},
    }
