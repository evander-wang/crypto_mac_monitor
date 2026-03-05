"""YamlConfigProvider - YAML 配置提供者（骨架）"""

from app.domain.repositories.config_provider import ConfigProvider


class YamlConfigProvider(ConfigProvider):
    """
    YAML 配置提供者实现

    基础设施层实现 ConfigProvider 接口。
    TODO: 在阶段 2 实现完整功能，包装现有 ConfigManager。
    """

    def get_symbols(self):
        """获取配置的交易对列表"""
        raise NotImplementedError("将在阶段 2 实现")

    def get_timeframes(self):
        """获取配置的时间周期"""
        raise NotImplementedError("将在阶段 2 实现")

    def get_trend_min_confidence(self, timeframe: str) -> float:
        """获取指定时间周期的最小置信度阈值"""
        raise NotImplementedError("将在阶段 2 实现")
