"""
from utils.logger import log_error

趋势分析器主类
整合四种趋势检测模型，提供统一的分析接口
"""

from typing import Dict, List, Optional

from app.domain.repositories import DataProvider
from app.models import ReturnBreakoutDTO, ReturnImpulseDTO, ReturnRealtimeRangeDTO, TrendResult
from app.utils import log_error, log_warn

from .indicators import TrendAnalysisCalculator
from .models import (
    BreakoutModel,
    ChannelModel,
    ConsolidationModel,
)


class TrendAnalyzer:
    """趋势分析器主类"""

    impulse_threshold = 0.0

    def __init__(
        self,
        data_provider: DataProvider,
    ):
        """
        初始化趋势分析器

        Args:
            data_provider: 数据提供者接口
        """
        self.data_provider: DataProvider = data_provider
        # TODO: 从 ConfigProvider 获取 fetch_periods，暂时使用默认值
        self.fetch_periods: int = 30
        # 实时波动监控配置
        self.realtime_enabled: bool = False
        self.realtime_interval_sec: int = 3
        self.realtime_range_threshold: float = 0.6  # %

        # TODO: 从 ConfigProvider 获取模型配置，暂时使用 None
        tm_cfg = None

        self.models = {
            "breakout": BreakoutModel(config=(tm_cfg.get("breakout") if tm_cfg else None)),
            "channel": ChannelModel(config=(tm_cfg.get("channel") if tm_cfg else None)),
            "consolidation": ConsolidationModel(config=(tm_cfg.get("consolidation") if tm_cfg else None)),
        }

        # 分析历史记录，按(symbol, bar)维度保存
        self.analysis_history: Dict[tuple, List[TrendResult]] = {}

    def symbol_data_is_ready(self, symbol: str, bar: str = "5m") -> bool:
        """
        检查指定交易对的数据是否准备就绪

        Args:
            symbol: 交易对符号，如'BTC-USDT'
            bar: 时间周期

        Returns:
            数据是否准备就绪
        """
        # 使用 DataProvider 接口的 is_data_ready 方法
        return self.data_provider.is_data_ready(symbol, bar)

    def analyze_trend(self, symbol: str, min_confidence: float = 0.6, bar: str = "5m") -> Optional[TrendResult]:
        """
        分析指定交易对的趋势

        Args:
            symbol: 交易对符号
            min_confidence: 最小置信度阈值

        Returns:
            最佳匹配的趋势结果，如果没有找到返回None
        """
        if not self.symbol_data_is_ready(symbol, bar=bar):
            return None

        # TODO: 从 ConfigProvider 获取模型配置覆盖
        # try:
        #     if hasattr(self.data_provider, "data_config") and hasattr(self.data_provider.data_config, "get_trend_model_config"):
        #         for name in ["breakout", "channel", "consolidation"]:
        #             cfg = self.data_provider.data_config.get_trend_model_config(name, timeframe=bar)  # type: ignore
        #             if cfg and name in self.models:
        #                 # 合并覆盖到模型现有配置
        #                 self.models[name].config.update(cfg)  # type: ignore
        # except (AttributeError, TypeError, ValueError):
        #     # 配置更新失败，使用默认配置
        #     pass

        # 获取K线数据
        df = self.data_provider.get_kline_data(symbol, bar, limit=self.fetch_periods)
        if df is None or len(df) < 20:
            log_error(f"{symbol} {bar} 数据不足, 无法分析趋势", "TREND")
            return None

        # 计算技术指标
        indicators = TrendAnalysisCalculator.calculate_all_indicators(df)
        if not indicators:
            return None

        # 运行所有模型分析
        results = []

        for model_name, model in self.models.items():
            try:
                result = model.analyze(df, indicators)
                if result and result.confidence >= min_confidence:
                    results.append(result)
            except Exception as e:
                log_error(f"{model_name} 模型分析出错: {e}", "TREND")
                continue

        # 如果没有任何模型识别出趋势，返回None
        if not results:
            return None

        # 选择置信度最高的结果
        best_result = max(results, key=lambda x: x.confidence)

        # 保存到历史记录
        key = (symbol, bar)
        if key not in self.analysis_history:
            self.analysis_history[key] = []
        self.analysis_history[key].append(best_result)

        # 只保留最近的50次分析结果
        if len(self.analysis_history[key]) > 50:
            self.analysis_history[key] = self.analysis_history[key][-50:]

        return best_result

    # 运行时配置更新API
    def set_fetch_periods(self, periods: int):
        self.fetch_periods = max(20, min(500, int(periods)))

    def update_channel_config(self, **kwargs):
        channel: ChannelModel = self.models.get("channel")  # type: ignore
        if channel:
            channel.config.update({k: v for k, v in kwargs.items() if v is not None})

    # 3x5m 冲击检测（基于现有5m数据）
    def detect_5m_impulse(self, symbol: str) -> Optional[ReturnImpulseDTO]:
        df = self.data_provider.get_kline_data(symbol, "5m", 3)
        if df is None or len(df) < 3:
            log_warn(f"{symbol} 3x5m 冲击 失败, 数据不足", "EXTRAS")
            return None
        close = df["close"]
        pct3 = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100

        # 只有变化幅度超过阈值才认为是冲击
        if abs(pct3) >= self.impulse_threshold:
            direction = "↑" if pct3 > 0 else "↓"
            return ReturnImpulseDTO(direction=direction, pct3=abs(pct3), is_approximated=False)
        return None

    # 实现 5m 蜡烛线连续突破检测
    def detect_5m_breakout(self, symbol: str) -> Optional[ReturnBreakoutDTO]:
        df = self.data_provider.get_kline_data(symbol, "5m", 10)
        if df is None or len(df) < 10:
            log_warn(f"{symbol} 5m 连续突破检测失败, 数据不足", "EXTRAS")
            return None

        close = df["close"]

        # 从最新开始往前检查连续K线
        consecutive_count = 0
        direction = None

        # 从最新开始往前检查连续K线
        for i in range(len(close) - 1, 0, -1):  # 从最后一根往前
            if close.iloc[i] > close.iloc[i - 1]:
                if direction is None:
                    direction = "up"
                elif direction == "up":
                    consecutive_count += 1
                else:
                    # 方向改变，停止计数
                    break
            elif close.iloc[i] < close.iloc[i - 1]:
                if direction is None:
                    direction = "down"
                elif direction == "down":
                    consecutive_count += 1
                else:
                    # 方向改变，停止计数
                    break
            else:
                # 平盘，停止计数
                break

        # 如果没有检测到连续趋势，返回None
        if direction is None or consecutive_count == 0:
            return None

        # 计算连续期间的涨跌幅
        start_idx = len(close) - 1 - consecutive_count
        end_idx = len(close) - 1
        change_pct = round((close.iloc[end_idx] - close.iloc[start_idx]) / close.iloc[start_idx] * 100, 2)

        if direction == "up":
            return ReturnBreakoutDTO(
                breakout_type="连续上涨突破",
                direction="↑",
                consecutive_count=consecutive_count,
                change_pct=change_pct,
                breakout_strength=min(change_pct / 2.0, 1.0),
                start_price=float(close.iloc[start_idx]),
                end_price=float(close.iloc[end_idx]),
                total_periods=len(close),
            )
        else:  # direction == 'down'
            return ReturnBreakoutDTO(
                breakout_type="连续下跌突破",
                direction="↓",
                consecutive_count=consecutive_count,
                change_pct=change_pct,
                breakout_strength=min(abs(change_pct) / 2.0, 1.0),
                start_price=float(close.iloc[start_idx]),
                end_price=float(close.iloc[end_idx]),
                total_periods=len(close),
            )

    # 实时波动（最近5根1m）
    def get_1m_realtime_range(self, symbol: str, limit: int = 5) -> Optional[ReturnRealtimeRangeDTO]:
        df = self.data_provider.get_kline_data(symbol, "1m", limit=limit)
        if df is None or df.empty:
            log_warn(f"{symbol} 1m 实时波动 失败, 数据不足", "EXTRAS")
            return None
        high_price = df["high"].max()
        low_price = df["low"].min()
        mid = (high_price + low_price) / 2
        if mid <= 0:
            return None
        r = (high_price - low_price) / mid * 100
        return ReturnRealtimeRangeDTO(high=float(high_price), low=float(low_price), range_percent=round(r, 2))

    def _extract_key_details(self, result: TrendResult) -> Dict:
        """提取关键详细信息用于显示"""
        key_details = {}

        if result.trend_type == "突破":
            details = result.details
            key_details = {
                "breakout_type": details.get("breakout_type"),
                "volume_ratio": round(details.get("volume_ratio", 1), 2),
                "breakout_strength": round(details.get("breakout_strength", 0), 2),
            }
        elif result.trend_type in ["宽通道", "窄通道"]:
            details = result.details
            key_details = {
                "channel_width": round(details.get("avg_width_percent", 0), 2),
                "price_position": round(details.get("price_position_in_channel", 0.5), 2),
                "stability": round(details.get("width_stability", 0), 2),
            }
        elif result.trend_type == "震荡":
            details = result.details
            key_details = {
                "adx": round(details.get("adx_value", 0), 1),
                "price_range": round(details.get("price_range_percent", 0), 2),
                "rsi": round(details.get("rsi_analysis", {}).get("current_rsi", 50), 1),
            }

        return key_details

    def get_analysis_history(self, symbol: str, bar: str = "5m", limit: int = 10) -> List[TrendResult]:
        """
        获取分析历史记录

        Args:
            symbol: 交易对符号
            limit: 返回记录数量限制

        Returns:
            最近的分析历史记录
        """
        key = (symbol, bar)
        if key not in self.analysis_history:
            return []
        history = self.analysis_history[key]
        return history[-limit:] if len(history) > limit else history

    def is_ready(self, symbol: str, bar: str = "5m") -> bool:
        """检查是否准备好进行分析"""
        return self.data_provider.is_data_ready(symbol, bar)

    def get_supported_symbols(self) -> List[str]:
        """获取支持的交易对列表"""
        return self.data_provider.get_supported_symbols()
