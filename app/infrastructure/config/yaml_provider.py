"""YamlConfigProvider - YAML 配置提供者实现"""

from typing import Any, Dict, List

from app.config.config_manager import ConfigManager
from app.domain.repositories.config_provider import ConfigProvider


class YamlConfigProvider(ConfigProvider):
    """
    YAML 配置提供者实现

    基础设施层实现 ConfigProvider 接口。
    包装现有的 ConfigManager，提供适配器模式转换。
    """

    def __init__(self, config_file: str = None):
        """
        初始化配置提供者

        Args:
            config_file: 配置文件路径，默认使用 ConfigManager 的默认路径
        """
        self._config_manager = ConfigManager(config_file)

    def get_symbols(self) -> List[str]:
        """获取配置的交易对列表"""
        data_config = self._config_manager.get_data_config()
        return data_config.symbols

    def get_timeframes(self) -> Dict[str, Any]:
        """获取配置的时间周期"""
        data_config = self._config_manager.get_data_config()
        return data_config.timeframes

    def get_trend_min_confidence(self, timeframe: str) -> float:
        """获取指定时间周期的最小置信度阈值"""
        data_config = self._config_manager.get_data_config()
        return data_config.trend_min_confidence.get(timeframe, 0.5)
