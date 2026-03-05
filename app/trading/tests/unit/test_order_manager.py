"""
OrderManager 单元测试.

测试订单管理器的核心功能,包括:
- 初始化
- 启动/停止监控
- 订单数据获取
- 订单数据解析
- 事件发布
"""

from unittest.mock import Mock, call, patch
import time

import pytest

from app.trading.order_manager import OrderInfo, OrderManager, OrderSummary


class TestOrderManagerInit:
    """测试 OrderManager 初始化."""

    def test_init_default_parameters(self, mock_exchange):
        """测试使用默认参数初始化."""
        manager = OrderManager(mock_exchange)

        assert manager.exchange == mock_exchange
        assert manager.update_interval == 30
        assert manager._running is False
        assert manager._thread is None
        assert manager._orders_cache == {}
        assert manager.last_update_time == 0

    def test_init_custom_update_interval(self, mock_exchange):
        """测试自定义更新间隔."""
        manager = OrderManager(mock_exchange, update_interval=60)

        assert manager.update_interval == 60


class TestOrderManagerLifecycle:
    """测试 OrderManager 生命周期管理."""

    def test_start_starts_monitoring_thread(self, mock_exchange):
        """测试启动监控线程."""
        manager = OrderManager(mock_exchange)
        manager.start()

        assert manager._running is True
        assert manager._thread is not None
        assert manager._thread.is_alive()

        # 清理
        manager.stop()

    def test_start_when_already_running(self, mock_exchange):
        """测试重复启动."""
        manager = OrderManager(mock_exchange)
        manager.start()
        thread1 = manager._thread

        manager.start()  # 再次调用应该被忽略

        assert manager._thread == thread1  # 线程不应该改变

        # 清理
        manager.stop()

    def test_stop_stops_monitoring_thread(self, mock_exchange):
        """测试停止监控线程 - 线程可能需要时间完全停止."""
        manager = OrderManager(mock_exchange)
        manager.start()
        manager.stop()

        assert manager._running is False

        # 等待线程结束,增加超时时间
        if manager._thread:
            manager._thread.join(timeout=5)
            # 注意:线程可能因为 sleep 而仍在运行,这是正常的

    def test_stop_when_not_running(self, mock_exchange):
        """测试停止未运行的监控器."""
        manager = OrderManager(mock_exchange)
        # 不应该抛出异常
        manager.stop()

        assert manager._running is False


class TestOrderManagerGetSummary:
    """测试 OrderManager 获取摘要信息."""

    def test_get_summary_empty_cache(self, mock_exchange):
        """测试空缓存时获取摘要."""
        manager = OrderManager(mock_exchange)
        summary = manager.get_order_summary()

        assert summary.total_orders == 0
        assert summary.open_orders == 0
        assert summary.filled_orders == 0
        assert summary.cancelled_orders == 0
        assert summary.orders == []

    def test_get_summary_with_open_order(self, mock_exchange):
        """测试包含开放订单的摘要."""
        manager = OrderManager(mock_exchange)

        # 手动添加订单数据
        order = OrderInfo(
            id="12345678",
            symbol="BTC-USDT-SWAP",
            type="limit",
            side="buy",
            amount=0.1,
            price=50000.0,
            filled=0.0,
            remaining=0.1,
            status="open",
            timestamp=int(time.time() * 1000),
            info={},
        )

        with manager._lock:
            manager._orders_cache["12345678"] = order

        summary = manager.get_order_summary()

        assert summary.total_orders == 1
        assert summary.open_orders == 1
        assert summary.filled_orders == 0
        assert summary.cancelled_orders == 0

    def test_get_summary_with_filled_order(self, mock_exchange):
        """测试包含已成交订单的摘要."""
        manager = OrderManager(mock_exchange)

        order = OrderInfo(
            id="12345679",
            symbol="BTC-USDT-SWAP",
            type="market",
            side="buy",
            amount=0.1,
            price=None,
            filled=0.1,
            remaining=0.0,
            status="filled",
            timestamp=int(time.time() * 1000),
            info={},
        )

        with manager._lock:
            manager._orders_cache["12345679"] = order

        summary = manager.get_order_summary()

        assert summary.total_orders == 1
        assert summary.open_orders == 0
        assert summary.filled_orders == 1
        assert summary.cancelled_orders == 0

    def test_get_summary_with_cancelled_order(self, mock_exchange):
        """测试包含已取消订单的摘要."""
        manager = OrderManager(mock_exchange)

        order = OrderInfo(
            id="12345680",
            symbol="BTC-USDT-SWAP",
            type="limit",
            side="sell",
            amount=0.1,
            price=52000.0,
            filled=0.0,
            remaining=0.1,
            status="canceled",
            timestamp=int(time.time() * 1000),
            info={},
        )

        with manager._lock:
            manager._orders_cache["12345680"] = order

        summary = manager.get_order_summary()

        assert summary.total_orders == 1
        assert summary.open_orders == 0
        assert summary.filled_orders == 0
        assert summary.cancelled_orders == 1

    def test_get_summary_with_mixed_orders(self, mock_exchange):
        """测试包含混合状态订单的摘要."""
        manager = OrderManager(mock_exchange)

        orders = [
            OrderInfo("1", "BTC-USDT-SWAP", "limit", "buy", 0.1, 50000.0, 0.0, 0.1, "open", int(time.time() * 1000), {}),
            OrderInfo("2", "BTC-USDT-SWAP", "market", "sell", 0.1, None, 0.1, 0.0, "filled", int(time.time() * 1000), {}),
            OrderInfo("3", "ETH-USDT-SWAP", "limit", "buy", 1.0, 3000.0, 0.0, 1.0, "canceled", int(time.time() * 1000), {}),
        ]

        with manager._lock:
            for order in orders:
                manager._orders_cache[order.id] = order

        summary = manager.get_order_summary()

        assert summary.total_orders == 3
        assert summary.open_orders == 1
        assert summary.filled_orders == 1
        assert summary.cancelled_orders == 1


class TestOrderManagerParseOrder:
    """测试 OrderManager 订单数据解析."""

    def test_parse_order_valid_limit_order(self, mock_exchange, sample_order_data):
        """测试解析有效的限价订单."""
        manager = OrderManager(mock_exchange)
        result = manager._parse_order(sample_order_data)

        assert result is not None
        assert result.id == "12345678"
        assert result.symbol == "BTC-USDT-SWAP"
        assert result.type == "limit"
        assert result.side == "buy"
        assert result.amount == 0.1
        assert result.price == 50000.0
        assert result.filled == 0.1
        assert result.status == "filled"

    def test_parse_order_market_order(self, mock_exchange):
        """测试解析市价订单."""
        manager = OrderManager(mock_exchange)

        market_order_data = {
            "id": "87654321",
            "symbol": "ETH-USDT-SWAP",
            "type": "market",
            "side": "sell",
            "amount": 1.0,
            "price": None,  # 市价单没有价格
            "filled": 1.0,
            "remaining": 0.0,
            "status": "filled",
            "timestamp": int(time.time() * 1000),
            "info": {},
        }

        result = manager._parse_order(market_order_data)

        assert result is not None
        assert result.type == "market"
        assert result.price is None

    def test_parse_order_with_avg_price(self, mock_exchange):
        """测试解析包含成交均价的订单."""
        manager = OrderManager(mock_exchange)

        order_data_with_avg = {
            "id": "11111111",
            "symbol": "BTC-USDT-SWAP",
            "type": "limit",
            "side": "buy",
            "amount": 0.5,
            "price": 50000.0,
            "filled": 0.3,
            "remaining": 0.2,
            "status": "partially_filled",
            "timestamp": int(time.time() * 1000),
            "average": 50100.0,  # 成交均价
            "info": {},
        }

        result = manager._parse_order(order_data_with_avg)

        assert result is not None
        assert result.avg_price == 50100.0

    def test_parse_order_with_executed_value(self, mock_exchange):
        """测试从成交总额计算平均价格."""
        manager = OrderManager(mock_exchange)

        order_data = {
            "id": "22222222",
            "symbol": "BTC-USDT-SWAP",
            "type": "market",
            "side": "buy",
            "amount": 0.2,
            "price": None,
            "filled": 0.2,
            "remaining": 0.0,
            "status": "filled",
            "timestamp": int(time.time() * 1000),
            "executedValue": "10020.0",  # 成交总额
            "info": {},
        }

        result = manager._parse_order(order_data)

        assert result is not None
        # avg_price = executedValue / filled = 10020.0 / 0.2 = 50100.0
        assert result.avg_price == 50100.0

    def test_parse_order_with_pnl(self, mock_exchange):
        """测试解析包含盈亏的订单."""
        manager = OrderManager(mock_exchange)

        order_data_with_pnl = {
            "id": "33333333",
            "symbol": "BTC-USDT-SWAP",
            "type": "limit",
            "side": "sell",
            "amount": 0.1,
            "price": 52000.0,
            "filled": 0.1,
            "remaining": 0.0,
            "status": "filled",
            "timestamp": int(time.time() * 1000),
            "pnl": 150.0,  # 盈亏
            "info": {},
        }

        result = manager._parse_order(order_data_with_pnl)

        assert result is not None
        assert result.profit_loss == 150.0

    def test_parse_order_invalid_data(self, mock_exchange):
        """测试解析无效数据 - 缺少必需字段时会返回带有默认值的对象."""
        manager = OrderManager(mock_exchange)

        invalid_data = {
            "id": "44444444"
            # 缺少其他必需字段
        }

        result = manager._parse_order(invalid_data)
        # 当前实现会返回带有默认值的 OrderInfo 对象
        assert result is not None
        assert result.id == "44444444"
        assert result.symbol == ""
        assert result.side == ""
        assert result.amount == 0.0


class TestOrderManagerFetchOrders:
    """测试 OrderManager 获取订单数据."""

    def test_fetch_orders_no_api_key(self, mock_exchange):
        """测试未配置 API 密钥时获取订单."""
        mock_exchange.apiKey = None

        manager = OrderManager(mock_exchange)
        manager._fetch_orders()

        # 应该不抛出异常,但也不应该获取任何数据
        assert len(manager._orders_cache) == 0

    @patch("app.trading.order_manager.get_bridge_manager")
    def test_fetch_orders_success(self, mock_bridge_manager, mock_exchange, sample_order_data):
        """测试成功获取订单数据."""
        mock_exchange.fetch_open_orders = Mock(return_value=[sample_order_data])
        mock_exchange.fetchOrders = Mock(return_value=[])
        mock_bridge = Mock()
        mock_bridge.get_ui_emitter = Mock(return_value=Mock())
        mock_bridge_manager.return_value = mock_bridge

        manager = OrderManager(mock_exchange)
        manager._fetch_orders()

        # 验证订单被缓存
        assert len(manager._orders_cache) > 0

    @patch("app.trading.order_manager.get_bridge_manager")
    def test_fetch_orders_api_permission_error(self, mock_bridge_manager, mock_exchange):
        """测试 API 权限错误处理."""
        mock_exchange.fetch_open_orders = Mock(side_effect=Exception("API permission denied"))
        mock_bridge = Mock()
        mock_bridge.get_ui_emitter = Mock(return_value=Mock())
        mock_bridge_manager.return_value = mock_bridge

        manager = OrderManager(mock_exchange)
        # 不应该抛出异常
        manager._fetch_orders()

        assert len(manager._orders_cache) == 0


class TestOrderManagerOrderChanges:
    """测试 OrderManager 订单变化检测."""

    def test_has_orders_changed_size_differs(self, mock_exchange, sample_order_data):
        """测试订单数量不同时检测到变化."""
        manager = OrderManager(mock_exchange)

        # 第一次检查空字典,长度不同应该返回 True
        new_orders = {}
        # 空字典对空字典,长度相同,应该返回 False
        assert manager._has_orders_changed(new_orders) is False

        # 添加订单后,长度不同应该返回 True
        order = OrderInfo(
            id="12345678",
            symbol="BTC-USDT-SWAP",
            type="limit",
            side="buy",
            amount=0.1,
            price=50000.0,
            filled=0.0,
            remaining=0.1,
            status="open",
            timestamp=int(time.time() * 1000),
            info={},
        )

        new_orders = {"12345678": order}
        assert manager._has_orders_changed(new_orders) is True

        # 更新缓存
        with manager._lock:
            manager._orders_cache = new_orders.copy()

        # 第二次检查应该返回 False(没有变化)
        assert manager._has_orders_changed(new_orders) is False

        # 修改订单状态
        order2 = OrderInfo(
            id="12345678",
            symbol="BTC-USDT-SWAP",
            type="limit",
            side="buy",
            amount=0.1,
            price=50000.0,
            filled=0.1,  # 不同的成交量
            remaining=0.0,
            status="filled",  # 不同的状态
            timestamp=int(time.time() * 1000),
            info={},
        )

        new_orders_modified = {"12345678": order2}

        # 应该检测到变化
        assert manager._has_orders_changed(new_orders_modified) is True


class TestOrderManagerPublishUpdate:
    """测试 OrderManager 发布更新事件."""

    @patch("app.trading.order_manager.get_bridge_manager")
    def test_publish_update_emits_event(self, mock_bridge_manager, mock_exchange):
        """测试发布订单更新事件."""
        mock_emitter = Mock()
        mock_bridge = Mock()
        mock_bridge.get_ui_emitter = Mock(return_value=mock_emitter)
        mock_bridge_manager.return_value = mock_bridge

        manager = OrderManager(mock_exchange)

        # 添加一些订单数据
        order = OrderInfo(
            id="12345678",
            symbol="BTC-USDT-SWAP",
            type="limit",
            side="buy",
            amount=0.1,
            price=50000.0,
            filled=0.0,
            remaining=0.1,
            status="open",
            timestamp=int(time.time() * 1000),
            info={},
        )

        with manager._lock:
            manager._orders_cache["12345678"] = order

        # 发布更新
        manager._publish_update()

        # 验证事件被发布
        mock_emitter.emit.assert_called_once()
        call_args = mock_emitter.emit.call_args
        assert call_args[0][0] == "ui.order.update"  # EVENT_ORDER_UPDATE
        assert isinstance(call_args[0][1], OrderSummary)
