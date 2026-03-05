"""
数据配置类

管理数据获取、缓存、调度等相关配置
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base_config import BaseConfig


@dataclass
class TimeframeConfig:
    """时间周期配置"""

    min_periods: int = 50
    buffer_periods: int = 50
    update_interval: int = 20
    cache_size: int = 400
    show_on_ui: bool = True  # 是否在UI上显示

    @property
    def limit(self) -> int:
        """获取数据获取限制"""
        return self.min_periods + self.buffer_periods

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        from dataclasses import asdict

        return asdict(self)


@dataclass
class SchedulerConfig:
    """调度器配置"""

    ticker_update_interval: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        from dataclasses import asdict

        return asdict(self)


@dataclass
class CacheConfig:
    """缓存配置"""

    cleanup_interval: int = 600
    data_expiry: int = 3600
    max_size: int = 1000

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        from dataclasses import asdict

        return asdict(self)


@dataclass
class DataConfig(BaseConfig):
    """数据配置"""

    # 时间周期配置
    timeframes: Dict[str, TimeframeConfig] = field(
        default_factory=lambda: {
            "5m": TimeframeConfig(min_periods=50, buffer_periods=50, update_interval=21, cache_size=400),
            "1h": TimeframeConfig(min_periods=50, buffer_periods=50, update_interval=22, cache_size=400),
            "4h": TimeframeConfig(min_periods=50, buffer_periods=50, update_interval=23, cache_size=400),
        }
    )

    # 调度器配置
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)

    # 缓存配置
    cache: CacheConfig = field(default_factory=CacheConfig)

    # 趋势分析器配置
    trend_analyzer_fetch_periods: int = 100

    # 分析配置
    trend_min_confidence: Dict[str, float] = field(default_factory=lambda: {"5m": 0.5, "1h": 0.6, "4h": 0.65})
    analysis_interval_sec: int = 10

    # 支持的交易对
    symbols: List[str] = field(default_factory=lambda: ["BTC-USDT-SWAP", "ETH-USDT-SWAP"])

    # 趋势模型配置（支持 Breakout/Channel/Consolidation 参数化）
    trend_models: Dict[str, Dict[str, Any]] = field(
        default_factory=lambda: {
            "breakout": {
                "volume_multiplier": 1.5,
                "breakout_threshold": 0.5,
                "confirmation_periods": 2,
                "min_periods": 20,
                "per_timeframe": {},
            },
            "channel": {
                "wide_channel_threshold": 4.0,
                "narrow_channel_threshold": 1.5,
                "channel_consistency": 0.7,
                "slope_up_threshold": 0.1,
                "slope_down_threshold": -0.1,
                "min_periods": 20,
                "per_timeframe": {},
            },
            "consolidation": {
                "adx_threshold": 25,
                "price_range_threshold": 3.0,
                "ma_convergence_threshold": 2.0,
                "rsi_range": [30, 70],
                "min_periods": 20,
                "per_timeframe": {},
            },
        }
    )

    def get_section_name(self) -> str:
        return "data"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataConfig":
        """从字典创建数据配置实例"""
        # 创建默认实例
        instance = cls()

        # 更新简单字段
        for key, value in data.items():
            if key == "timeframes" and isinstance(value, dict):
                # 处理时间周期配置
                timeframes = {}
                for tf, tf_data in value.items():
                    if isinstance(tf_data, dict):
                        timeframes[tf] = TimeframeConfig(**tf_data)
                    else:
                        timeframes[tf] = tf_data
                instance.timeframes = timeframes
            elif key == "scheduler" and isinstance(value, dict):
                # 处理调度器配置
                instance.scheduler = SchedulerConfig(**value)
            elif key == "cache" and isinstance(value, dict):
                # 处理缓存配置
                instance.cache = CacheConfig(**value)
            elif key == "trend_models" and isinstance(value, dict):
                # 处理趋势模型配置
                tm: Dict[str, Dict[str, Any]] = {}
                for model_name, model_cfg in value.items():
                    if isinstance(model_cfg, dict):
                        # 保留默认项，并合并自定义
                        base_default = instance.trend_models.get(model_name, {})
                        merged = {**base_default, **model_cfg}
                        # 确保 per_timeframe 存在并为字典
                        if "per_timeframe" not in merged or not isinstance(merged.get("per_timeframe"), dict):
                            merged["per_timeframe"] = {}
                        tm[model_name] = merged
                # 合并默认与自定义，保留未提供的默认项
                instance.trend_models = {**instance.trend_models, **tm}
            elif hasattr(instance, key):
                setattr(instance, key, value)

        return instance

    def get_timeframe_config(self, timeframe: str) -> TimeframeConfig:
        """获取指定时间周期的配置"""
        return self.timeframes.get(timeframe, TimeframeConfig())

    def get_supported_timeframes(self) -> List[str]:
        """获取支持的时间周期列表"""
        return list(self.timeframes.keys())

    def get_symbols(self) -> List[str]:
        """获取支持的交易对列表"""
        return self.symbols

    def get_trend_model_config(self, name: str, timeframe: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取指定趋势模型配置，支持按时间周期覆盖"""
        base = self.trend_models.get(name)
        if base is None:
            return None
        # 分离 per_timeframe 与基础配置
        per_tf = base.get("per_timeframe") if isinstance(base, dict) else None
        # 构建实际用于模型的配置（不包含 per_timeframe 键）
        cfg = {k: v for k, v in base.items() if k != "per_timeframe"}
        if timeframe and isinstance(per_tf, dict):
            override = per_tf.get(timeframe)
            if isinstance(override, dict):
                cfg.update(override)
        return cfg

    def validate(self) -> bool:
        """验证数据配置"""
        # 验证时间周期配置
        for tf, config in self.timeframes.items():
            if config.min_periods <= 0:
                return False
            if config.buffer_periods < 0:
                return False
            if config.update_interval <= 0:
                return False

        # 验证调度器配置
        if self.scheduler.ticker_update_interval <= 0:
            return False

        return True
