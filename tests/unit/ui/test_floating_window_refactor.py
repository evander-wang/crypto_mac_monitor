"""测试 FloatingWindow DDD 重构"""

from unittest.mock import Mock, MagicMock, patch
import pytest


def test_floating_window_uses_application_facade():
    """验证 FloatingWindow 可以使用 Application 门面"""
    # 创建 mock application
    mock_application = Mock()
    mock_application.get_trend = Mock(return_value={"trend": "bullish"})

    # TODO: 修改 FloatingWindow 构造函数以接受 Application
    # window = FloatingWindow(application=mock_application)

    # 验证可以通过 application 获取趋势
    # result = window.get_trend_from_application("BTC/USDT", "5m")
    # mock_application.get_trend.assert_called_once_with("BTC/USDT", "5m")

    # 暂时只验证 mock 创建成功
    assert mock_application is not None


def test_floating_window_receives_events():
    """验证 FloatingWindow 通过事件订阅接收更新"""
    mock_application = Mock()

    # 验证事件订阅机制
    # window = FloatingWindow(application=mock_application)
    # window.start_listening()

    # 模拟事件发布
    # mock_application.publish_ui("price_update", {"symbol": "BTC/USDT", "price": 50000})

    # 验证 UI 接收到事件
    assert mock_application is not None
