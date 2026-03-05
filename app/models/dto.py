from dataclasses import field


"""
核心数据传输对象(DTO)定义
用于在不同组件间传递结构化数据
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class PriceDTO:
    """价格数据传输对象"""

    symbol: str
    price: Decimal
    timestamp: datetime
    volume: Optional[Decimal] = None
    high_24h: Optional[Decimal] = None
    low_24h: Optional[Decimal] = None
    change_24h: Optional[Decimal] = None
    change_percent_24h: Optional[Decimal] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        change_percent_value = float(self.change_percent_24h) if self.change_percent_24h else None
        return {
            "symbol": self.symbol,
            "price": float(self.price),
            "timestamp": (self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp),
            "volume": float(self.volume) if self.volume else None,
            "high_24h": float(self.high_24h) if self.high_24h else None,
            "low_24h": float(self.low_24h) if self.low_24h else None,
            "change_24h": float(self.change_24h) if self.change_24h else None,
            "change_percent_24h": change_percent_value,
            "change_percent": change_percent_value,  # 向后兼容性
        }


@dataclass
class ReturnTickerDTO:
    """Ticker 数据传输对象

    统一 ticker 数据结构，便于在调度器、缓存与数据管理器之间传递。
    保留 to_dict 与 from_dict 以兼容旧字典结构。
    """

    symbol: str
    last: float
    open24h: Optional[float] = None
    high24h: Optional[float] = None
    low24h: Optional[float] = None
    vol_base_24h: Optional[float] = None
    vol_quote_24h: Optional[float] = None
    timestamp_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为旧字典格式（兼容原有使用习惯）"""
        return {
            "instId": self.symbol,
            "last": str(self.last) if self.last is not None else "0",
            "open24h": (str(self.open24h) if self.open24h is not None else None),
            "high24h": (str(self.high24h) if self.high24h is not None else None),
            "low24h": (str(self.low24h) if self.low24h is not None else None),
            "volCcy24h": (str(self.vol_base_24h) if self.vol_base_24h is not None else None),
            "vol24h": (str(self.vol_quote_24h) if self.vol_quote_24h is not None else None),
            "ts": (str(self.timestamp_ms) if self.timestamp_ms is not None else None),
            "sodUtc0": (str(self.open24h) if self.open24h is not None else None),
            "sodUtc8": (str(self.open24h) if self.open24h is not None else None),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReturnTickerDTO":
        """从旧字典结构创建 ReturnTickerDTO（确保类型安全）"""

        def _to_float(val: Any) -> Optional[float]:
            if val is None or val == "" or val == "None":
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        def _to_int(val: Any) -> Optional[int]:
            if val is None or val == "" or val == "None":
                return None
            try:
                return int(val)
            except (ValueError, TypeError):
                try:
                    return int(float(val))
                except (ValueError, TypeError):
                    return None

        return cls(
            symbol=str(data.get("instId") or data.get("symbol") or ""),
            last=float(data.get("last") or 0.0),
            open24h=_to_float(data.get("open24h")),
            high24h=_to_float(data.get("high24h")),
            low24h=_to_float(data.get("low24h")),
            vol_base_24h=_to_float(data.get("volCcy24h")),
            vol_quote_24h=_to_float(data.get("vol24h")),
            timestamp_ms=_to_int(data.get("ts")),
        )


@dataclass
class TrendDTO:
    """趋势分析数据传输对象"""

    symbol: str
    timeframe: str
    direction: str  # 'up', 'down', 'sideways'
    strength: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    timestamp: datetime
    indicators: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "direction": self.direction,
            "strength": self.strength,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "indicators": self.indicators,
        }


@dataclass
class AnalysisTrendDTO:
    """分析结果数据传输对象"""

    symbol: str
    data: Dict[str, Any] = field(default_factory=dict)
    timeframe: Optional[str] = None  # 触发此次更新的时间框架（用于UI只闪烁该TF）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "symbol": self.symbol,
            "data": self.data,
            "timeframe": self.timeframe,
        }


@dataclass
class RealtimeExtrasDTO:
    """实时额外数据传输对象"""

    symbol: str
    timestamp: datetime
    funding_rate: Optional[Decimal] = None
    open_interest: Optional[Decimal] = None
    long_short_ratio: Optional[float] = None
    fear_greed_index: Optional[int] = None
    news_sentiment: Optional[float] = None
    social_sentiment: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "funding_rate": float(self.funding_rate) if self.funding_rate else None,
            "open_interest": float(self.open_interest) if self.open_interest else None,
            "long_short_ratio": self.long_short_ratio,
            "fear_greed_index": self.fear_greed_index,
            "news_sentiment": self.news_sentiment,
            "social_sentiment": self.social_sentiment,
        }


@dataclass
class AlertDTO:
    """告警数据传输对象"""

    title: str
    alert_id: str
    symbol: str
    condition_type: str
    message: str
    level: str
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "title": self.title,
            "alert_id": self.alert_id,
            "symbol": self.symbol,
            "condition_type": self.condition_type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ReturnImpulseDTO:
    """3x5m冲击检测返回数据传输对象"""

    direction: str  # '↑' or '↓'
    pct3: float  # 3根K线的变化百分比
    is_approximated: bool = False  # 是否为近似计算

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "direction": self.direction,
            "pct3": self.pct3,
            "is_approximated": self.is_approximated,
        }


@dataclass
class ReturnBreakoutDTO:
    """5m连续突破检测返回数据传输对象"""

    breakout_type: str  # '连续上涨突破' or '连续下跌突破'
    direction: str  # '↑' or '↓'
    consecutive_count: int  # 连续K线数量
    change_pct: float  # 连续期间的涨跌幅
    breakout_strength: float  # 突破强度 (0.0-1.0)
    start_price: float  # 起始价格
    end_price: float  # 结束价格
    total_periods: int  # 总K线数量

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "breakout_type": self.breakout_type,
            "direction": self.direction,
            "consecutive_count": self.consecutive_count,
            "change_pct": self.change_pct,
            "breakout_strength": self.breakout_strength,
            "start_price": self.start_price,
            "end_price": self.end_price,
            "total_periods": self.total_periods,
        }


@dataclass
class ReturnRealtimeRangeDTO:
    """1m实时区间返回数据传输对象"""

    high: float  # 最高价
    low: float  # 最低价
    range_percent: float  # 区间百分比

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "high": self.high,
            "low": self.low,
            "range_percent": self.range_percent,
        }


@dataclass
class Return5mIndicatorsDTO:
    """5分钟指标的结构化数据传输对象

    - impulse: 3x5m 冲击检测结果（结构化）
    - breakout: 5m 连续突破检测结果（结构化）
    - realtime_range: 1m 实时区间（结构化）
    """

    impulse: Optional["ReturnImpulseDTO"] = None
    breakout: Optional["ReturnBreakoutDTO"] = None
    realtime_range: Optional["ReturnRealtimeRangeDTO"] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "impulse": (self.impulse.to_dict() if self.impulse else None),
            "breakout": (self.breakout.to_dict() if self.breakout else None),
            "realtime_range": (self.realtime_range.to_dict() if self.realtime_range else None),
        }


@dataclass
class Return5mExtrasDTO:
    """5分钟额外数据传输对象"""

    impulse: str = ""  # 3x5m冲击检测结果
    range: str = ""  # 1m实时区间检测结果
    breakout: str = ""  # 5m连续突破检测结果

    def to_dict(self) -> Dict[str, Any]:
        """转换为完整字典格式，包含所有字段"""
        return {"impulse": self.impulse, "range": self.range, "breakout": self.breakout}

    def to_5m_dict(self) -> Dict[str, Any]:
        """转换为5m格式的字典，只包含非空字段，用于向后兼容"""
        result = {
            "impulse": "",
            "range": "",
            "breakout": "",
        }
        if self.impulse or self.range or self.breakout:
            result = {
                "impulse": self.impulse,
                "range": self.range,
                "breakout": self.breakout,
            }
        return result


@dataclass
class ReturnDataReadyDTO:
    """数据就绪事件数据传输对象

    用于在事件系统中发布数据就绪通知，包含当前管理器类型、时间戳、
    支持的交易对和时间周期列表。
    """

    manager_type: str
    timestamp: str
    supported_symbols: List[str]
    supported_timeframes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（供需要字典的消费者使用）"""
        return {
            "manager_type": self.manager_type,
            "timestamp": self.timestamp,
            "supported_symbols": list(self.supported_symbols),
            "supported_timeframes": list(self.supported_timeframes),
        }


@dataclass
class ReturnKlineUpdateDTO:
    """K线更新事件数据传输对象

    用于在K线数据写入缓存后发布事件，提示订阅者可进行针对性分析或刷新。
    """

    symbol: str
    timeframe: str
    is_initial: bool = False
    data_count: Optional[int] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "is_initial": self.is_initial,
            "data_count": self.data_count,
            "timestamp": self.timestamp,
        }


@dataclass
class ReturnCryptoDisplayColorDTO:
    """加密货币显示颜色DTO"""

    red: float  # 红色分量 (0.0-1.0)
    green: float  # 绿色分量 (0.0-1.0)
    blue: float  # 蓝色分量 (0.0-1.0)

    def to_tuple(self) -> tuple:
        """转换为RGB元组"""
        return (self.red, self.green, self.blue)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {"red": self.red, "green": self.green, "blue": self.blue, "rgb_tuple": self.to_tuple()}


class ReturnCryptoSymbolUiInfoDto:
    """保留原类以兼容旧用法（最小实现）"""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.price: Any = "加载中..."
        self.change_percent: float = 0.0
        self.color: tuple[float, float, float] = (0, 0, 0)
        self.initial_price: Optional[float] = None
        self.ui_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "change_percent": self.change_percent,
            "color": self.color,
            "initial_price": self.initial_price,
            "ui_text": self.ui_text,
        }


@dataclass
class ReturnCryptoSymbolDisplayDTO:
    """加密货币符号显示数据DTO

    用于UI显示的加密货币数据结构，包含价格、颜色、趋势等信息
    """

    time_texts = {}
    symbol_info: Optional[ReturnCryptoSymbolUiInfoDto] = None
    trend_by_tf: Optional[AnalysisTrendDTO] = None  # 按时间框架的趋势数据 trend_analysis.get_trend_indicators()
    extras_by_tf: Return5mExtrasDTO | None = None  # 按时间框架的额外数据

    def __post_init__(self):
        """初始化后处理"""
        if self.trend_by_tf is None:
            self.trend_by_tf = AnalysisTrendDTO(symbol=self.symbol_info.symbol) if self.symbol_info else None
        if self.extras_by_tf is None:
            self.extras_by_tf = Return5mExtrasDTO()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（兼容原有格式）"""
        return {
            "symbol": self.symbol_info.to_dict() if self.symbol_info else None,
            "trend_by_tf": self.trend_by_tf or {},
            "extras_by_tf": self.extras_by_tf.to_dict() if self.extras_by_tf else {},
        }
