"""
from utils.logger import log_error

趋势分析模块
支持四种市场趋势识别：突破、宽通道、窄通道、震荡
"""

from .trend_analyzer import TrendAnalyzer


__version__ = "1.0.0"
__all__ = ["TrendAnalyzer"]
