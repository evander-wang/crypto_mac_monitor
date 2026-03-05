"""Application - 应用层门面

应用层的统一入口，提供简洁的业务接口。
"""

from app.domain.repositories import DataProvider, ConfigProvider
from app.domain.events import EventPublisher


class Application:
    """
    应用层门面

    提供统一的业务入口，编排业务流程。
    通过构造函数注入接口依赖，实现依赖倒置。
    """

    def __init__(
        self,
        data_provider: DataProvider,
        event_publisher: EventPublisher,
        config: ConfigProvider,
    ):
        """
        初始化应用

        Args:
            data_provider: 数据提供者接口
            event_publisher: 事件发布者接口
            config: 配置提供者接口
        """
        # 构造函数注入 - 所有依赖都是接口
        self.data_provider = data_provider
        self.event_publisher = event_publisher
        self.config = config

        # 创建应用服务
        # TODO: Task 2.5 创建具体的服务类
        self.analysis = None  # type: ignore
        self.realtime = None  # type: ignore

    def start(self):
        """启动应用"""
        if self.analysis:
            self.analysis.start()
        if self.realtime:
            self.realtime.start()

    def stop(self):
        """停止应用"""
        if self.analysis:
            self.analysis.stop()
        if self.realtime:
            self.realtime.stop()

    def get_trend(self, symbol: str, timeframe: str):
        """
        获取趋势分析结果 - 门面方法

        Args:
            symbol: 交易对符号
            timeframe: 时间周期

        Returns:
            趋势分析结果
        """
        if self.analysis:
            return self.analysis.analyze_trend(symbol, timeframe)
        return None
