"""RealtimeService - 实时监控应用服务"""

from typing import Optional
from app.domain.repositories import DataProvider, ConfigProvider
from app.domain.events import EventPublisher


class RealtimeService:
    """
    实时监控应用服务

    编排实时监控业务流程，处理价格更新和信号检测。
    """

    def __init__(
        self,
        data_provider: DataProvider,
        event_publisher: EventPublisher,
        config: ConfigProvider,
    ):
        """
        初始化实时监控服务

        Args:
            data_provider: 数据提供者接口
            event_publisher: 事件发布者接口
            config: 配置提供者接口
        """
        self.data_provider = data_provider
        self.event_publisher = event_publisher
        self.config = config
        self.is_running = False

    def start(self):
        """启动实时监控服务"""
        if self.is_running:
            return

        self.is_running = True

        # TODO: 启动定时检查任务
        # symbols = self.config.get_symbols()
        # for symbol in symbols:
        #     self._schedule_price_check(symbol)

    def stop(self):
        """停止实时监控服务"""
        self.is_running = False

    def check_price(self, symbol: str) -> Optional[float]:
        """
        检查当前价格

        Args:
            symbol: 交易对符号

        Returns:
            当前价格
        """
        return self.data_provider.get_current_price(symbol)

    def check_signals(self, symbol: str):
        """
        检查交易信号

        Args:
            symbol: 交易对符号

        Returns:
            信号列表
        """
        # TODO: 实现信号检测逻辑
        # 获取价格
        price = self.check_price(symbol)

        # TODO: 分析信号
        return {
            "symbol": symbol,
            "price": price,
            "signals": [],
        }
