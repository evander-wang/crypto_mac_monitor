"""
核心接口定义模块
定义各模块间的标准接口
"""

from .dto import (
    AlertDTO,
    AnalysisTrendDTO,
    PriceDTO,
    RealtimeExtrasDTO,
    Return5mExtrasDTO,
    Return5mIndicatorsDTO,
    ReturnBreakoutDTO,
    ReturnCryptoSymbolDisplayDTO,
    ReturnCryptoSymbolUiInfoDto,
    ReturnDataReadyDTO,
    ReturnImpulseDTO,
    ReturnKlineUpdateDTO,
    ReturnRealtimeRangeDTO,
    ReturnTickerDTO,
    TrendDTO,
)
from .trend_analysis_model import BaseTrendModel, TrendResult


__all__ = [
    "BaseTrendModel",
    "TrendResult",
    "PriceDTO",
    "TrendDTO",
    "AnalysisTrendDTO",
    "RealtimeExtrasDTO",
    "AlertDTO",
    "ReturnTickerDTO",
    "ReturnDataReadyDTO",
    "ReturnKlineUpdateDTO",
    "ReturnImpulseDTO",
    "ReturnBreakoutDTO",
    "ReturnRealtimeRangeDTO",
    "Return5mIndicatorsDTO",
    "Return5mExtrasDTO",
    "ReturnCryptoSymbolUiInfoDto",
    "ReturnCryptoSymbolDisplayDTO",
]
