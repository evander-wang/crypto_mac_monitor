"""
TrendAnalyzer 单元测试.

测试趋势分析器的核心功能,包括:
- 初始化
- 趋势分析
- 数据准备检查
- 冲击检测
- 突破检测
- 实时波动监控
"""

from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

from app.models.dto import ReturnBreakoutDTO, ReturnImpulseDTO, ReturnRealtimeRangeDTO
from app.trend_analysis.trend_analyzer import TrendAnalyzer


class TestTrendAnalyzerInit:
    """测试 TrendAnalyzer 初始化."""

    def test_init_with_data_manager(self, mock_data_manager):
        """测试使用数据管理器初始化."""
        analyzer = TrendAnalyzer(mock_data_manager)

        assert analyzer.data_manager == mock_data_manager
        assert analyzer.fetch_periods == 30
        assert analyzer.realtime_enabled is False
        assert "breakout" in analyzer.models
        assert "channel" in analyzer.models
        assert "consolidation" in analyzer.models
        assert analyzer.analysis_history == {}

    def test_init_with_custom_fetch_periods(self, mock_data_manager):
        """测试自定义 fetch_periods."""
        # 修改配置
        mock_data_manager.data_config.trend_analyzer_fetch_periods = 50

        analyzer = TrendAnalyzer(mock_data_manager)

        assert analyzer.fetch_periods == 50

    def test_init_with_invalid_fetch_periods(self, mock_data_manager):
        """测试无效的 fetch_periods 被限制在合理范围."""
        # 测试超出范围的情况
        mock_data_manager.data_config.trend_analyzer_fetch_periods = 1000

        analyzer = TrendAnalyzer(mock_data_manager)

        # 应该被限制在 500 以内
        assert analyzer.fetch_periods == 500

    def test_init_models_configuration(self, mock_data_manager):
        """测试模型配置初始化."""
        analyzer = TrendAnalyzer(mock_data_manager)

        # 验证所有模型都被初始化
        assert hasattr(analyzer.models["breakout"], "analyze")
        assert hasattr(analyzer.models["channel"], "analyze")
        assert hasattr(analyzer.models["consolidation"], "analyze")


class TestTrendAnalyzerDataReadiness:
    """测试数据准备检查."""

    def test_symbol_data_is_ready_true(self, mock_data_manager):
        """测试数据准备就绪."""
        mock_data_manager.is_kline_data_ready = Mock(return_value=True)

        analyzer = TrendAnalyzer(mock_data_manager)

        result = analyzer.symbol_data_is_ready("BTC-USDT-SWAP", "5m")

        assert result is True

    def test_symbol_data_is_ready_false(self, mock_data_manager):
        """测试数据未准备就绪."""
        mock_data_manager.is_kline_data_ready = Mock(return_value=False)

        analyzer = TrendAnalyzer(mock_data_manager)

        result = analyzer.symbol_data_is_ready("BTC-USDT-SWAP", "5m")

        assert result is False

    def test_symbol_data_is_ready_with_exception(self, mock_data_manager):
        """测试配置异常时的默认行为."""
        # 删除 data_config
        delattr(mock_data_manager, "data_config")

        analyzer = TrendAnalyzer(mock_data_manager)

        # 应该使用默认值 50
        analyzer.symbol_data_is_ready("BTC-USDT-SWAP", "5m")

        # 验证使用了默认的 min_periods
        mock_data_manager.is_kline_data_ready.assert_called()

    def test_is_ready(self, mock_data_manager):
        """测试 is_ready 便捷方法."""
        analyzer = TrendAnalyzer(mock_data_manager)

        result = analyzer.is_ready("BTC-USDT-SWAP", "5m")

        assert result is True
        mock_data_manager.is_kline_data_ready.assert_called_with("BTC-USDT-SWAP", "5m", min_periods=20)


class TestTrendAnalyzerAnalyzeTrend:
    """测试趋势分析."""

    def test_analyze_trend_success(self, mock_data_manager, sample_kline_data):
        """测试成功的趋势分析."""
        analyzer = TrendAnalyzer(mock_data_manager)

        result = analyzer.analyze_trend("BTC-USDT-SWAP", min_confidence=0.6, bar="5m")

        # 验证返回了结果(可能为 None,因为模型可能不识别)
        # 主要验证没有异常抛出
        assert result is None or hasattr(result, "trend_type")

    def test_analyze_trend_insufficient_data(self, mock_data_manager):
        """测试数据不足时的处理."""
        # Mock 返回空数据
        mock_data_manager.get_kline_data = Mock(return_value=None)
        mock_data_manager.is_kline_data_ready = Mock(return_value=False)

        analyzer = TrendAnalyzer(mock_data_manager)

        result = analyzer.analyze_trend("BTC-USDT-SWAP", min_confidence=0.6, bar="5m")

        assert result is None

    def test_analyze_trend_saves_history(self, mock_data_manager, sample_kline_data):
        """测试分析结果保存到历史."""
        analyzer = TrendAnalyzer(mock_data_manager)

        # 执行分析
        analyzer.analyze_trend("BTC-USDT-SWAP", min_confidence=0.6, bar="5m")

        # 验证历史记录被创建
        key = ("BTC-USDT-SWAP", "5m")
        assert key in analyzer.analysis_history

    def test_analyze_trend_history_limit(self, mock_data_manager, sample_kline_data):
        """测试历史记录数量限制."""
        analyzer = TrendAnalyzer(mock_data_manager)
        analyzer.fetch_periods = 20  # 减少数据量以加快测试

        # 降低置信度阈值以确保有分析结果
        min_conf = 0.0

        # 执行多次分析
        for i in range(60):
            analyzer.analyze_trend("BTC-USDT-SWAP", min_confidence=min_conf, bar="5m")

        # 验证历史记录不超过 50(如果有结果的话)
        key = ("BTC-USDT-SWAP", "5m")
        if key in analyzer.analysis_history:
            assert len(analyzer.analysis_history[key]) <= 50

    def test_analyze_trend_with_model_error(self, mock_data_manager, sample_kline_data):
        """测试模型分析异常处理."""
        analyzer = TrendAnalyzer(mock_data_manager)

        # Mock 一个模型抛出异常
        analyzer.models["breakout"].analyze = Mock(side_effect=Exception("Model error"))

        # 不应该抛出异常
        result = analyzer.analyze_trend("BTC-USDT-SWAP", min_confidence=0.6, bar="5m")

        # 其他模型应该继续执行
        assert result is None or hasattr(result, "trend_type")


class TestTrendAnalyzerImpulseDetection:
    """测试冲击检测."""

    def test_detect_5m_impulse_upward(self, mock_data_manager):
        """测试检测到向上冲击."""
        # 创建有明显上涨的数据
        pd.Timestamp.now()
        df = pd.DataFrame(
            {
                "close": [50000, 50200, 50500]  # 1% 上涨
            }
        )

        mock_data_manager.get_kline_data = Mock(return_value=df)

        analyzer = TrendAnalyzer(mock_data_manager)
        analyzer.impulse_threshold = 0.5  # 设置阈值为 0.5%

        result = analyzer.detect_5m_impulse("BTC-USDT-SWAP")

        assert result is not None
        assert isinstance(result, ReturnImpulseDTO)
        assert result.direction == "↑"
        assert result.pct3 >= 0.5

    def test_detect_5m_impulse_downward(self, mock_data_manager):
        """测试检测到向下冲击."""
        # 创建有明显下跌的数据
        df = pd.DataFrame(
            {
                "close": [50500, 50200, 50000]  # 1% 下跌
            }
        )

        mock_data_manager.get_kline_data = Mock(return_value=df)

        analyzer = TrendAnalyzer(mock_data_manager)
        analyzer.impulse_threshold = 0.5

        result = analyzer.detect_5m_impulse("BTC-USDT-SWAP")

        assert result is not None
        assert result.direction == "↓"
        assert result.pct3 >= 0.5

    def test_detect_5m_impulse_no_impulse(self, mock_data_manager):
        """测试未检测到冲击."""
        # 创建小幅波动数据
        df = pd.DataFrame(
            {
                "close": [50000, 50010, 50020]  # 0.04% 变化
            }
        )

        mock_data_manager.get_kline_data = Mock(return_value=df)

        analyzer = TrendAnalyzer(mock_data_manager)
        analyzer.impulse_threshold = 0.5

        result = analyzer.detect_5m_impulse("BTC-USDT-SWAP")

        assert result is None

    def test_detect_5m_impulse_insufficient_data(self, mock_data_manager):
        """测试数据不足."""
        mock_data_manager.get_kline_data = Mock(return_value=None)

        analyzer = TrendAnalyzer(mock_data_manager)

        result = analyzer.detect_5m_impulse("BTC-USDT-SWAP")

        assert result is None


class TestTrendAnalyzerBreakoutDetection:
    """测试突破检测."""

    def test_detect_5m_breakout_consecutive_up(self, mock_data_manager):
        """测试检测到连续上涨突破."""
        # 创建连续上涨的数据
        close_prices = [50000, 50100, 50200, 50300, 50400, 50500, 50600, 50700, 50800, 50900]
        df = pd.DataFrame({"close": close_prices})

        mock_data_manager.get_kline_data = Mock(return_value=df)

        analyzer = TrendAnalyzer(mock_data_manager)

        result = analyzer.detect_5m_breakout("BTC-USDT-SWAP")

        assert result is not None
        assert isinstance(result, ReturnBreakoutDTO)
        assert result.breakout_type == "连续上涨突破"
        assert result.direction == "↑"
        assert result.consecutive_count > 0

    def test_detect_5m_breakout_consecutive_down(self, mock_data_manager):
        """测试检测到连续下跌突破."""
        # 创建连续下跌的数据
        close_prices = [50900, 50800, 50700, 50600, 50500, 50400, 50300, 50200, 50100, 50000]
        df = pd.DataFrame({"close": close_prices})

        mock_data_manager.get_kline_data = Mock(return_value=df)

        analyzer = TrendAnalyzer(mock_data_manager)

        result = analyzer.detect_5m_breakout("BTC-USDT-SWAP")

        assert result is not None
        assert result.breakout_type == "连续下跌突破"
        assert result.direction == "↓"
        assert result.consecutive_count > 0

    def test_detect_5m_breakout_no_consecutive(self, mock_data_manager):
        """测试未检测到连续趋势."""
        # 创建震荡数据
        close_prices = [50000, 50100, 50000, 50100, 50000, 50100, 50000, 50100, 50000, 50100]
        df = pd.DataFrame({"close": close_prices})

        mock_data_manager.get_kline_data = Mock(return_value=df)

        analyzer = TrendAnalyzer(mock_data_manager)

        result = analyzer.detect_5m_breakout("BTC-USDT-SWAP")

        assert result is None

    def test_detect_5m_breakout_insufficient_data(self, mock_data_manager):
        """测试数据不足."""
        mock_data_manager.get_kline_data = Mock(return_value=None)

        analyzer = TrendAnalyzer(mock_data_manager)

        result = analyzer.detect_5m_breakout("BTC-USDT-SWAP")

        assert result is None


class TestTrendAnalyzerRealtimeRange:
    """测试实时波动监控."""

    def test_get_1m_realtime_range_success(self, mock_data_manager):
        """测试成功获取实时波动."""
        df = pd.DataFrame({"high": [50100, 50200, 50300, 50400, 50500], "low": [49900, 50000, 50100, 50200, 50300]})

        mock_data_manager.get_kline_data = Mock(return_value=df)

        analyzer = TrendAnalyzer(mock_data_manager)

        result = analyzer.get_1m_realtime_range("BTC-USDT-SWAP", limit=5)

        assert result is not None
        assert isinstance(result, ReturnRealtimeRangeDTO)
        assert result.high > 0
        assert result.low > 0
        assert result.range_percent > 0

    def test_get_1m_realtime_range_custom_limit(self, mock_data_manager):
        """测试自定义限制数量."""
        df = pd.DataFrame({"high": [50100, 50200, 50300], "low": [49900, 50000, 50100]})

        mock_data_manager.get_kline_data = Mock(return_value=df)

        analyzer = TrendAnalyzer(mock_data_manager)

        result = analyzer.get_1m_realtime_range("BTC-USDT-SWAP", limit=3)

        assert result is not None

    def test_get_1m_realtime_range_empty_data(self, mock_data_manager):
        """测试空数据."""
        mock_data_manager.get_kline_data = Mock(return_value=None)

        analyzer = TrendAnalyzer(mock_data_manager)

        result = analyzer.get_1m_realtime_range("BTC-USDT-SWAP")

        assert result is None


class TestTrendAnalyzerConfiguration:
    """测试运行时配置."""

    def test_set_fetch_periods(self, mock_data_manager):
        """测试设置 fetch_periods."""
        analyzer = TrendAnalyzer(mock_data_manager)

        analyzer.set_fetch_periods(100)

        assert analyzer.fetch_periods == 100

    def test_set_fetch_periods_clamps_values(self, mock_data_manager):
        """测试 fetch_periods 被限制在合理范围."""
        analyzer = TrendAnalyzer(mock_data_manager)

        # 测试下限
        analyzer.set_fetch_periods(10)
        assert analyzer.fetch_periods == 20

        # 测试上限
        analyzer.set_fetch_periods(1000)
        assert analyzer.fetch_periods == 500

    def test_update_channel_config(self, mock_data_manager):
        """测试更新通道模型配置."""
        analyzer = TrendAnalyzer(mock_data_manager)

        analyzer.update_channel_config(period=20, deviation=2.5)

        # 验证配置被更新
        channel_model = analyzer.models["channel"]
        assert channel_model.config is not None


class TestTrendAnalyzerUtilityMethods:
    """测试工具方法."""

    def test_get_supported_symbols(self, mock_data_manager):
        """测试获取支持的交易对."""
        analyzer = TrendAnalyzer(mock_data_manager)

        symbols = analyzer.get_supported_symbols()

        assert symbols == ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]
        mock_data_manager.get_supported_symbols.assert_called_once()

    def test_get_analysis_history_empty(self, mock_data_manager):
        """测试获取空历史记录."""
        analyzer = TrendAnalyzer(mock_data_manager)

        history = analyzer.get_analysis_history("BTC-USDT-SWAP", "5m")

        assert history == []

    def test_get_analysis_history_with_limit(self, mock_data_manager, sample_kline_data):
        """测试限制历史记录数量."""
        analyzer = TrendAnalyzer(mock_data_manager)

        # 执行多次分析
        for _ in range(20):
            analyzer.analyze_trend("BTC-USDT-SWAP", min_confidence=0.6, bar="5m")

        # 获取限制数量的历史
        history = analyzer.get_analysis_history("BTC-USDT-SWAP", "5m", limit=10)

        assert len(history) <= 10

    def test_extract_key_details_breakout(self, mock_data_manager):
        """测试提取突破趋势的关键详情."""
        from app.models import TrendResult

        analyzer = TrendAnalyzer(mock_data_manager)

        # 创建模拟的 TrendResult
        result = TrendResult(
            trend_type="突破",
            confidence=0.8,
            direction="up",
            strength=2.0,
            details={"breakout_type": "price_breakout", "volume_ratio": 1.5, "breakout_strength": 0.9},
        )

        key_details = analyzer._extract_key_details(result)

        assert "breakout_type" in key_details
        assert "volume_ratio" in key_details
        assert "breakout_strength" in key_details

    def test_extract_key_details_channel(self, mock_data_manager):
        """测试提取通道趋势的关键详情."""
        from app.models import TrendResult

        analyzer = TrendAnalyzer(mock_data_manager)

        result = TrendResult(
            trend_type="宽通道",
            confidence=0.7,
            direction="neutral",
            strength=1.5,
            details={"avg_width_percent": 2.5, "price_position_in_channel": 0.6, "width_stability": 0.8},
        )

        key_details = analyzer._extract_key_details(result)

        assert "channel_width" in key_details
        assert "price_position" in key_details
        assert "stability" in key_details

    def test_extract_key_details_consolidation(self, mock_data_manager):
        """测试提取震荡趋势的关键详情."""
        from app.models import TrendResult

        analyzer = TrendAnalyzer(mock_data_manager)

        result = TrendResult(
            trend_type="震荡",
            confidence=0.6,
            direction="neutral",
            strength=1.0,
            details={"adx_value": 20.5, "price_range_percent": 1.2, "rsi_analysis": {"current_rsi": 55.0}},
        )

        key_details = analyzer._extract_key_details(result)

        assert "adx" in key_details
        assert "price_range" in key_details
        assert "rsi" in key_details
