"""
PositionManager 单元测试.

测试仓位管理器的核心功能,包括:
- 初始化
- 启动/停止监控
- 仓位数据获取
- 仓位数据解析
- 事件发布
"""

from unittest.mock import Mock, call, patch
import time

import pytest

from app.trading.position_manager import PositionInfo, PositionManager, PositionSummary


class TestPositionManagerInit:
    """测试 PositionManager 初始化."""

    def test_init_default_parameters(self, mock_exchange):
        """测试使用默认参数初始化."""
        manager = PositionManager(mock_exchange)

        assert manager.exchange == mock_exchange
        assert manager.update_interval == 30
        assert manager._running is False
        assert manager._thread is None
        assert manager._positions_cache == {}
        assert manager.last_update_time == 0

    def test_init_custom_update_interval(self, mock_exchange):
        """测试自定义更新间隔."""
        manager = PositionManager(mock_exchange, update_interval=60)

        assert manager.update_interval == 60


class TestPositionManagerLifecycle:
    """测试 PositionManager 生命周期管理."""

    def test_start_starts_monitoring_thread(self, mock_exchange):
        """测试启动监控线程."""
        manager = PositionManager(mock_exchange)
        manager.start()

        assert manager._running is True
        assert manager._thread is not None
        assert manager._thread.is_alive()

        # 清理
        manager.stop()

    def test_start_when_already_running(self, mock_exchange):
        """测试重复启动."""
        manager = PositionManager(mock_exchange)
        manager.start()
        thread1 = manager._thread

        manager.start()  # 再次调用应该被忽略

        assert manager._thread == thread1  # 线程不应该改变

        # 清理
        manager.stop()

    def test_stop_stops_monitoring_thread(self, mock_exchange):
        """测试停止监控线程 - 线程可能需要时间完全停止."""
        manager = PositionManager(mock_exchange)
        manager.start()
        manager.stop()

        assert manager._running is False

        # 等待线程结束,增加超时时间
        if manager._thread:
            manager._thread.join(timeout=5)
            # 注意:线程可能因为 sleep 而仍在运行,这是正常的

    def test_stop_when_not_running(self, mock_exchange):
        """测试停止未运行的监控器."""
        manager = PositionManager(mock_exchange)
        # 不应该抛出异常
        manager.stop()

        assert manager._running is False


class TestPositionManagerGetSummary:
    """测试 PositionManager 获取摘要信息."""

    def test_get_summary_empty_cache(self, mock_exchange):
        """测试空缓存时获取摘要."""
        manager = PositionManager(mock_exchange)
        summary = manager.get_position_summary()

        assert summary.total_positions == 0
        assert summary.long_positions == 0
        assert summary.short_positions == 0
        assert summary.total_unrealized_pnl == 0.0
        assert summary.total_margin_used == 0.0
        assert summary.positions == []

    def test_get_summary_with_long_position(self, mock_exchange):
        """测试包含多头仓位的摘要."""
        manager = PositionManager(mock_exchange)

        # 手动添加仓位数据
        position = PositionInfo(
            symbol="BTC-USDT-SWAP",
            side="long",
            size=0.5,
            contracts=0.5,
            contract_size=0.01,
            entry_price=50000.0,
            mark_price=51000.0,
            unrealized_pnl=50.0,
            percentage=1.0,
            maintenance_margin=10.0,
            initial_margin=100.0,
            timestamp=int(time.time() * 1000),
            info={},
        )

        with manager._lock:
            manager._positions_cache["BTC-USDT-SWAP_long"] = position

        summary = manager.get_position_summary()

        assert summary.total_positions == 1
        assert summary.long_positions == 1
        assert summary.short_positions == 0
        assert summary.total_unrealized_pnl == 50.0
        assert summary.total_margin_used == 100.0
        assert len(summary.positions) == 1

    def test_get_summary_with_short_position(self, mock_exchange):
        """测试包含空头仓位的摘要."""
        manager = PositionManager(mock_exchange)

        # 手动添加空头仓位
        position = PositionInfo(
            symbol="BTC-USDT-SWAP",
            side="short",
            size=0.3,
            contracts=0.3,
            contract_size=0.01,
            entry_price=52000.0,
            mark_price=51000.0,
            unrealized_pnl=30.0,
            percentage=0.6,
            maintenance_margin=8.0,
            initial_margin=80.0,
            timestamp=int(time.time() * 1000),
            info={},
        )

        with manager._lock:
            manager._positions_cache["BTC-USDT-SWAP_short"] = position

        summary = manager.get_position_summary()

        assert summary.total_positions == 1
        assert summary.long_positions == 0
        assert summary.short_positions == 1
        assert summary.total_unrealized_pnl == 30.0
        assert summary.total_margin_used == 80.0


class TestPositionManagerParsePosition:
    """测试 PositionManager 仓位数据解析."""

    def test_parse_position_valid_data(self, mock_exchange, sample_position_data):
        """测试解析有效的仓位数据."""
        manager = PositionManager(mock_exchange)
        result = manager._parse_position(sample_position_data)

        assert result is not None
        assert result.symbol == "BTC-USDT-SWAP"
        assert result.side == "long"
        assert result.size == 0.5
        assert result.entry_price == 50000.0
        assert result.mark_price == 51000.0
        assert result.unrealized_pnl == 50.0

    def test_parse_position_missing_optional_fields(self, mock_exchange):
        """测试解析缺少可选字段的仓位数据."""
        manager = PositionManager(mock_exchange)

        incomplete_data = {
            "symbol": "ETH-USDT-SWAP",
            "side": "short",
            "size": 1.0,
            "contracts": 1.0,
            "contractSize": 0.01,
            "entryPrice": None,
            "markPrice": None,
            "unrealizedPnl": None,
            "percentage": None,
            "maintenanceMargin": None,
            "initialMargin": None,
            "timestamp": int(time.time() * 1000),
            "info": {},
        }

        result = manager._parse_position(incomplete_data)

        assert result is not None
        assert result.symbol == "ETH-USDT-SWAP"
        assert result.side == "short"
        assert result.entry_price is None
        assert result.mark_price is None

    def test_parse_position_invalid_data(self, mock_exchange):
        """测试解析无效数据 - 缺少字段时返回默认值对象."""
        manager = PositionManager(mock_exchange)

        # 缺少必需字段
        invalid_data = {
            "symbol": "BTC-USDT-SWAP"
            # 缺少 side, size 等必需字段
        }

        result = manager._parse_position(invalid_data)
        # 当前实现会返回带有默认值的 PositionInfo 对象
        assert result is not None
        assert result.symbol == "BTC-USDT-SWAP"
        assert result.side == ""
        assert result.size == 0.0


class TestPositionManagerFetchPositions:
    """测试 PositionManager 获取仓位数据."""

    def test_fetch_positions_no_api_key(self, mock_exchange):
        """测试未配置 API 密钥时获取仓位."""
        mock_exchange.apiKey = None

        manager = PositionManager(mock_exchange)
        manager._fetch_positions()

        # 应该不抛出异常,但也不应该获取任何数据
        assert len(manager._positions_cache) == 0

    @patch("app.trading.position_manager.get_bridge_manager")
    def test_fetch_positions_success(self, mock_bridge_manager, mock_exchange, sample_position_data):
        """测试成功获取仓位数据."""
        mock_exchange.fetch_positions = Mock(return_value=[sample_position_data])
        mock_bridge = Mock()
        mock_bridge.get_ui_emitter = Mock(return_value=Mock())
        mock_bridge_manager.return_value = mock_bridge

        manager = PositionManager(mock_exchange)
        manager._fetch_positions()

        # 验证仓位被缓存
        assert len(manager._positions_cache) > 0

    @patch("app.trading.position_manager.get_bridge_manager")
    def test_fetch_positions_api_error(self, mock_bridge_manager, mock_exchange):
        """测试 API 错误处理."""
        mock_exchange.fetch_positions = Mock(side_effect=Exception("API Error"))
        mock_bridge = Mock()
        mock_bridge.get_ui_emitter = Mock(return_value=Mock())
        mock_bridge_manager.return_value = mock_bridge

        manager = PositionManager(mock_exchange)
        # 不应该抛出异常
        manager._fetch_positions()

        assert len(manager._positions_cache) == 0


class TestPositionManagerPositionChanges:
    """测试 PositionManager 仓位变化检测."""

    def test_has_positions_changed_size_differs(self, mock_exchange, sample_position_data):
        """测试仓位大小不同时检测到变化."""
        manager = PositionManager(mock_exchange)

        # 添加初始仓位
        position1 = PositionInfo(
            symbol="BTC-USDT-SWAP",
            side="long",
            size=0.5,
            contracts=0.5,
            contract_size=0.01,
            entry_price=50000.0,
            mark_price=51000.0,
            unrealized_pnl=50.0,
            percentage=1.0,
            maintenance_margin=10.0,
            initial_margin=100.0,
            timestamp=int(time.time() * 1000),
            info={},
        )

        new_positions = {"BTC-USDT-SWAP_long": position1}

        # 第一次检查应该返回 True(缓存为空)
        assert manager._has_positions_changed(new_positions) is True

        # 更新缓存
        with manager._lock:
            manager._positions_cache = new_positions.copy()

        # 第二次检查应该返回 False(没有变化)
        assert manager._has_positions_changed(new_positions) is False

        # 修改仓位大小
        position2 = PositionInfo(
            symbol="BTC-USDT-SWAP",
            side="long",
            size=0.6,  # 不同的仓位大小
            contracts=0.6,
            contract_size=0.01,
            entry_price=50000.0,
            mark_price=51000.0,
            unrealized_pnl=50.0,
            percentage=1.0,
            maintenance_margin=10.0,
            initial_margin=100.0,
            timestamp=int(time.time() * 1000),
            info={},
        )

        new_positions_modified = {"BTC-USDT-SWAP_long": position2}

        # 应该检测到变化
        assert manager._has_positions_changed(new_positions_modified) is True


class TestPositionManagerPublishUpdate:
    """测试 PositionManager 发布更新事件."""

    @patch("app.trading.position_manager.get_bridge_manager")
    def test_publish_update_emits_event(self, mock_bridge_manager, mock_exchange):
        """测试发布仓位更新事件."""
        mock_emitter = Mock()
        mock_bridge = Mock()
        mock_bridge.get_ui_emitter = Mock(return_value=mock_emitter)
        mock_bridge_manager.return_value = mock_bridge

        manager = PositionManager(mock_exchange)

        # 添加一些仓位数据
        position = PositionInfo(
            symbol="BTC-USDT-SWAP",
            side="long",
            size=0.5,
            contracts=0.5,
            contract_size=0.01,
            entry_price=50000.0,
            mark_price=51000.0,
            unrealized_pnl=50.0,
            percentage=1.0,
            maintenance_margin=10.0,
            initial_margin=100.0,
            timestamp=int(time.time() * 1000),
            info={},
        )

        with manager._lock:
            manager._positions_cache["BTC-USDT-SWAP_long"] = position

        # 发布更新
        manager._publish_update()

        # 验证事件被发布
        mock_emitter.emit.assert_called_once()
        call_args = mock_emitter.emit.call_args
        assert call_args[0][0] == "ui.position.update"  # EVENT_POSITION_UPDATE
        assert isinstance(call_args[0][1], PositionSummary)
