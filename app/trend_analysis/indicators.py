"""
from utils.logger import log_error

技术指标计算模块
使用TA-Lib计算各种技术指标
"""

from typing import Dict

import pandas as pd
import talib

from app.utils import log_error


class TechnicalIndicators:
    """技术指标计算器"""

    @staticmethod
    def sma(data: pd.Series, period: int = 20) -> pd.Series:
        """简单移动平均线"""
        return pd.Series(talib.SMA(data.values, timeperiod=period), index=data.index)

    @staticmethod
    def ema(data: pd.Series, period: int = 20) -> pd.Series:
        """指数移动平均线"""
        return pd.Series(talib.EMA(data.values, timeperiod=period), index=data.index)

    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """布林带"""
        upper, middle, lower = talib.BBANDS(data.values, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
        return {
            "upper": pd.Series(upper, index=data.index),
            "middle": pd.Series(middle, index=data.index),
            "lower": pd.Series(lower, index=data.index),
        }

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """平均真实波幅"""
        return pd.Series(
            talib.ATR(high.values, low.values, close.values, timeperiod=period),
            index=close.index,
        )

    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """平均方向性指数 - 衡量趋势强度"""
        return pd.Series(
            talib.ADX(high.values, low.values, close.values, timeperiod=period),
            index=close.index,
        )

    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """相对强弱指数"""
        return pd.Series(talib.RSI(data.values, timeperiod=period), index=data.index)

    @staticmethod
    def macd(
        data: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Dict[str, pd.Series]:
        """MACD指标"""
        macd_line, signal_line, histogram = talib.MACD(
            data.values,
            fastperiod=fast_period,
            slowperiod=slow_period,
            signalperiod=signal_period,
        )
        return {
            "macd": pd.Series(macd_line, index=data.index),
            "signal": pd.Series(signal_line, index=data.index),
            "histogram": pd.Series(histogram, index=data.index),
        }

    @staticmethod
    def detect_macd_crossovers(macd: pd.Series, signal: pd.Series) -> Dict[str, pd.Series]:
        """
        检测MACD金叉死叉

        Args:
            macd: MACD线
            signal: 信号线

        Returns:
            包含金叉和死叉信号的字典
        """
        # 金叉：MACD线从下向上穿越信号线
        golden_cross = (macd > signal) & (macd.shift(1) <= signal.shift(1))

        # 死叉：MACD线从上向下穿越信号线
        death_cross = (macd < signal) & (macd.shift(1) >= signal.shift(1))

        return {
            "golden_cross": golden_cross,  # 金叉
            "death_cross": death_cross,  # 死叉
        }

    @staticmethod
    def detect_rsi_extremes(rsi: pd.Series, oversold: float = 20, overbought: float = 80) -> Dict[str, pd.Series]:
        """
        检测RSI超买超卖

        Args:
            rsi: RSI值
            oversold: 超卖阈值（默认20）
            overbought: 超买阈值（默认80）

        Returns:
            包含超买超卖信号的字典
        """
        # 超卖：RSI < 20
        oversold_signal = rsi < oversold

        # 超买：RSI > 80
        overbought_signal = rsi > overbought

        return {
            "oversold": oversold_signal,  # 超卖信号
            "overbought": overbought_signal,  # 超买信号
        }

    @staticmethod
    def linear_regression(data: pd.Series, period: int = 20) -> Dict[str, pd.Series]:
        """线性回归指标"""
        # 线性回归线
        linreg = pd.Series(talib.LINEARREG(data.values, timeperiod=period), index=data.index)

        # 线性回归斜率
        slope = pd.Series(talib.LINEARREG_SLOPE(data.values, timeperiod=period), index=data.index)

        # 线性回归角度
        angle = pd.Series(talib.LINEARREG_ANGLE(data.values, timeperiod=period), index=data.index)

        return {"linreg": linreg, "slope": slope, "angle": angle}

    @staticmethod
    def standard_deviation(data: pd.Series, period: int = 20) -> pd.Series:
        """标准差"""
        return pd.Series(talib.STDDEV(data.values, timeperiod=period), index=data.index)

    @staticmethod
    def volume_sma(volume: pd.Series, period: int = 20) -> pd.Series:
        """成交量简单移动平均"""
        return pd.Series(talib.SMA(volume.values, timeperiod=period), index=volume.index)

    @staticmethod
    def volume_rate_of_change(volume: pd.Series, period: int = 10) -> pd.Series:
        """成交量变化率"""
        return pd.Series(talib.ROC(volume.values, timeperiod=period), index=volume.index)


class ChannelCalculator:
    """通道计算器"""

    @staticmethod
    def linear_regression_channel(data: pd.Series, period: int = 20, std_multiplier: float = 2.0) -> Dict[str, pd.Series]:
        """
        线性回归通道

        Args:
            data: 价格数据
            period: 计算周期
            std_multiplier: 标准差倍数

        Returns:
            包含上轨、中轨、下轨的字典
        """
        # 线性回归线
        linreg = pd.Series(talib.LINEARREG(data.values, timeperiod=period), index=data.index)

        # 标准差
        std = TechnicalIndicators.standard_deviation(data, period)

        # 计算通道
        upper_channel = linreg + (std * std_multiplier)
        lower_channel = linreg - (std * std_multiplier)

        return {
            "upper": upper_channel,
            "middle": linreg,
            "lower": lower_channel,
            "std": std,
        }

    @staticmethod
    def calculate_channel_width(upper: pd.Series, lower: pd.Series, middle: pd.Series) -> pd.Series:
        """计算通道宽度百分比"""
        width = (upper - lower) / middle * 100
        return width

    @staticmethod
    def detect_breakout(
        price: pd.Series,
        upper: pd.Series,
        lower: pd.Series,
        volume: pd.Series,
        vol_threshold: float = 1.5,
    ) -> Dict[str, pd.Series]:
        """
        检测突破

        Args:
            price: 收盘价
            upper: 上轨
            lower: 下轨
            volume: 成交量
            vol_threshold: 成交量倍数阈值

        Returns:
            突破信号字典
        """
        # 计算成交量均线
        vol_ma = TechnicalIndicators.volume_sma(volume, 20)

        # 上突破：价格突破上轨 + 成交量放大
        upper_breakout = (price > upper) & (volume > vol_ma * vol_threshold)

        # 下突破：价格跌破下轨 + 成交量放大
        lower_breakout = (price < lower) & (volume > vol_ma * vol_threshold)

        return {
            "upper_breakout": upper_breakout,
            "lower_breakout": lower_breakout,
            "volume_surge": volume > vol_ma * vol_threshold,
        }


class TrendAnalysisCalculator:
    """趋势分析计算器"""

    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> Dict:
        """
        计算所有需要的技术指标

        Args:
            df: 包含OHLCV数据的DataFrame

        Returns:
            包含所有指标的字典
        """
        # 支持更短窗口（20~30根K线），不足时直接返回空指标
        if len(df) < 20:
            return {}

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        indicators = {}

        try:
            # 移动平均线
            indicators["sma_20"] = TechnicalIndicators.sma(close, 20)
            indicators["sma_30"] = TechnicalIndicators.sma(close, 30)
            indicators["sma_50"] = TechnicalIndicators.sma(close, 50)
            indicators["ema_20"] = TechnicalIndicators.ema(close, 20)

            # 布林带
            bb = TechnicalIndicators.bollinger_bands(close, 20, 2.0)
            indicators["bb_upper"] = bb["upper"]
            indicators["bb_middle"] = bb["middle"]
            indicators["bb_lower"] = bb["lower"]

            # 线性回归通道
            lr_channel = ChannelCalculator.linear_regression_channel(close, 20, 2.0)
            indicators["lr_upper"] = lr_channel["upper"]
            indicators["lr_middle"] = lr_channel["middle"]
            indicators["lr_lower"] = lr_channel["lower"]
            indicators["lr_std"] = lr_channel["std"]

            # 通道宽度
            indicators["bb_width"] = ChannelCalculator.calculate_channel_width(bb["upper"], bb["lower"], bb["middle"])
            indicators["lr_width"] = ChannelCalculator.calculate_channel_width(
                lr_channel["upper"], lr_channel["lower"], lr_channel["middle"]
            )

            # 趋势指标
            indicators["adx"] = TechnicalIndicators.adx(high, low, close, 14)
            lr_indicators = TechnicalIndicators.linear_regression(close, 20)
            indicators["lr_slope"] = lr_indicators["slope"]
            indicators["lr_angle"] = lr_indicators["angle"]

            # 波动率指标
            indicators["atr"] = TechnicalIndicators.atr(high, low, close, 14)
            indicators["std"] = TechnicalIndicators.standard_deviation(close, 20)

            # RSI
            indicators["rsi"] = TechnicalIndicators.rsi(close, 14)

            # RSI超买超卖检测
            rsi_extremes = TechnicalIndicators.detect_rsi_extremes(indicators["rsi"])
            indicators["rsi_oversold"] = rsi_extremes["oversold"]  # RSI < 20
            indicators["rsi_overbought"] = rsi_extremes["overbought"]  # RSI > 80

            # MACD指标
            macd_data = TechnicalIndicators.macd(close)
            indicators["macd"] = macd_data["macd"]
            indicators["macd_signal"] = macd_data["signal"]
            indicators["macd_histogram"] = macd_data["histogram"]

            # MACD金叉死叉检测
            macd_crossovers = TechnicalIndicators.detect_macd_crossovers(indicators["macd"], indicators["macd_signal"])
            indicators["macd_golden_cross"] = macd_crossovers["golden_cross"]  # 金叉
            indicators["macd_death_cross"] = macd_crossovers["death_cross"]  # 死叉

            # 成交量指标
            indicators["volume_sma"] = TechnicalIndicators.volume_sma(volume, 20)
            indicators["volume_roc"] = TechnicalIndicators.volume_rate_of_change(volume, 10)

            # 突破检测
            breakout = ChannelCalculator.detect_breakout(close, indicators["bb_upper"], indicators["bb_lower"], volume, 1.5)
            indicators["upper_breakout"] = breakout["upper_breakout"]
            indicators["lower_breakout"] = breakout["lower_breakout"]
            indicators["volume_surge"] = breakout["volume_surge"]

        except Exception as e:
            log_error(f"计算指标时出错: {e}", "TREND")
            return {}

        return indicators
